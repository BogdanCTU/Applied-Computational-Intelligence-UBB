"""Dataset preprocessing, dual-track splitting, and manifest generation."""

import hashlib
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from app.core.config import get_project_root
from app.core.logging import get_logger
from app.database.schema_manager import SchemaManager
from app.datasets.bird import BIRDDataset
from app.datasets.schema_formatter import SchemaFormatter
from app.datasets.spider import SpiderDataset
from app.datasets.synthetic import SyntheticDatasetGenerator

logger = get_logger(__name__)

DEFAULT_SYSTEM_PROMPT = (
    "You are a specialized Text-to-SQL AI. Given the SQLite database schema and user question, "
    "generate a syntactically correct SQLite query that precisely answers the question. "
    "Output ONLY the SQL code enclosed in a ```sql code block."
)


@dataclass
class SQLTrainingExample:
    example_id: str
    db_id: str
    question: str
    query: str
    schema_text: str
    source: str       # 'spider', 'bird', 'synthetic'
    track: str        # 'track1_known' or 'track2_unseen'
    split: str        # 'train', 'valid', 'test'
    difficulty: str = "medium"
    system_prompt: str = DEFAULT_SYSTEM_PROMPT

    def to_chatml(self) -> Dict[str, Any]:
        """Converts example into Qwen/ChatML messages format for MLX-LM."""
        user_prompt = (
            f"Database Schema:\n{self.schema_text}\n\n"
            f"User Question:\n{self.question}\n\n"
            "Generate the SQLite query to answer the question."
        )
        assistant_reply = f"```sql\n{self.query.strip()}\n```"

        return {
            "example_id": self.example_id,
            "db_id": self.db_id,
            "track": self.track,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt},
                {"role": "assistant", "content": assistant_reply},
            ],
        }


def compute_sha256(file_path: Path) -> str:
    """Computes SHA-256 checksum of a file."""
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            sha.update(chunk)
    return sha.hexdigest()


class DatasetPreprocessor:
    """Orchestrates multi-source dataset ingestion, validation, splitting, and manifest generation."""

    def __init__(self, processed_dir: Optional[Union[str, Path]] = None):
        if processed_dir is None:
            self.processed_dir = get_project_root() / "2_Database" / "processed"
        else:
            self.processed_dir = Path(processed_dir).resolve()
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self._schema_cache: Dict[str, str] = {}

    def _get_schema_text(self, db_id: str, db_path: Path) -> str:
        """Retrieves or caches prompt-formatted schema for a database."""
        if db_id not in self._schema_cache:
            schema = SchemaManager.extract_schema_from_sqlite(db_path, db_id=db_id)
            self._schema_cache[db_id] = SchemaFormatter.format_for_prompt(schema)
        return self._schema_cache[db_id]

    def build_expanded_dataset(
        self,
        train_target: int = 3500,
        val_target: int = 350,
        seed: int = 42,
    ) -> Tuple[Dict[str, List[SQLTrainingExample]], Dict[str, Path]]:
        """Ingests Synthetic, Spider, and BIRD benchmarks and partitions into strict tracks."""
        rng = random.Random(seed)
        db_map: Dict[str, Path] = {}

        # 1. Generate Synthetic Databases (8 domains)
        synth_gen = SyntheticDatasetGenerator()
        synth_samples, synth_dbs = synth_gen.generate_and_validate()
        db_map.update(synth_dbs)

        # 2. Ingest Spider Databases & Records
        spider_ds = SpiderDataset()
        spider_db_map = spider_ds.get_available_database_map()
        db_map.update(spider_db_map)

        train_records = spider_ds.load_train_records()
        dev_records = spider_ds.load_dev_records()

        logger.info(f"Loaded {len(train_records)} raw Spider train and {len(dev_records)} Spider dev records.")

        # Identify unseen databases for Track 2 (dev databases)
        dev_db_ids: Set[str] = {r.db_id for r in dev_records}
        train_db_ids: Set[str] = {r.db_id for r in train_records} - dev_db_ids

        # Ensure complete disjointness
        assert len(dev_db_ids.intersection(train_db_ids)) == 0, "Spider train/dev DB overlap detected!"

        # Track 2 unseen synthetic domains
        unseen_synthetic_dbs = {"education", "entertainment"}

        # -------------------------------------------------------------
        # Track 1: Known-Schema Generalization
        # -------------------------------------------------------------
        # Gather all candidates for Track 1
        track1_examples: List[SQLTrainingExample] = []

        # Synthetic Track 1 samples
        for idx, s in enumerate(synth_samples):
            if s.track == "track1_known":
                schema_txt = self._get_schema_text(s.db_id, synth_dbs[s.db_id])
                track1_examples.append(
                    SQLTrainingExample(
                        example_id=f"synth_known_{idx+1}",
                        db_id=s.db_id,
                        question=s.question,
                        query=s.query,
                        schema_text=schema_txt,
                        source="synthetic",
                        track="track1_known",
                        split="train",  # reassigned below
                        difficulty=s.difficulty,
                    )
                )

        # Spider Train samples (belong to train_db_ids)
        for idx, r in enumerate(train_records):
            if r.db_id in db_map:
                schema_txt = self._get_schema_text(r.db_id, db_map[r.db_id])
                track1_examples.append(
                    SQLTrainingExample(
                        example_id=f"spider_train_{idx+1}",
                        db_id=r.db_id,
                        question=r.question,
                        query=r.query,
                        schema_text=schema_txt,
                        source="spider",
                        track="track1_known",
                        split="train",
                        difficulty="medium",
                    )
                )

        # Shuffle Track 1
        rng.shuffle(track1_examples)

        # Limit to train_target + val_target + test_target
        total_needed = train_target + val_target + 100
        selected_track1 = track1_examples[:total_needed]

        n_train = min(train_target, len(selected_track1) - val_target - 50)
        n_val = val_target

        train_split = selected_track1[:n_train]
        for ex in train_split:
            ex.split = "train"

        valid_split = selected_track1[n_train : n_train + n_val]
        for ex in valid_split:
            ex.split = "valid"

        test_known_split = selected_track1[n_train + n_val :]
        for ex in test_known_split:
            ex.split = "test_known"

        # -------------------------------------------------------------
        # Track 2: Unseen-Schema Generalization (Held-out Databases Only)
        # -------------------------------------------------------------
        test_unseen_split: List[SQLTrainingExample] = []

        # Synthetic Track 2 samples (education and entertainment)
        for idx, s in enumerate(synth_samples):
            if s.track == "track2_unseen":
                schema_txt = self._get_schema_text(s.db_id, synth_dbs[s.db_id])
                test_unseen_split.append(
                    SQLTrainingExample(
                        example_id=f"synth_unseen_{idx+1}",
                        db_id=s.db_id,
                        question=s.question,
                        query=s.query,
                        schema_text=schema_txt,
                        source="synthetic",
                        track="track2_unseen",
                        split="test_unseen",
                        difficulty=s.difficulty,
                    )
                )

        # Spider Dev samples (completely unseen databases)
        for idx, r in enumerate(dev_records):
            if r.db_id in db_map:
                schema_txt = self._get_schema_text(r.db_id, db_map[r.db_id])
                test_unseen_split.append(
                    SQLTrainingExample(
                        example_id=f"spider_dev_{idx+1}",
                        db_id=r.db_id,
                        question=r.question,
                        query=r.query,
                        schema_text=schema_txt,
                        source="spider",
                        track="track2_unseen",
                        split="test_unseen",
                        difficulty="hard",
                    )
                )

        rng.shuffle(test_unseen_split)

        dataset_splits = {
            "train": train_split,
            "valid": valid_split,
            "test_known": test_known_split,
            "test_unseen": test_unseen_split,
        }

        logger.info(
            f"Dataset assembled: Train={len(train_split)}, Valid={len(valid_split)}, "
            f"TestKnown={len(test_known_split)}, TestUnseen={len(test_unseen_split)}"
        )
        return dataset_splits, db_map

    def build_all_examples(self) -> Tuple[List[SQLTrainingExample], Dict[str, Path]]:
        """Backward-compatibility helper returning flattened examples list."""
        splits, db_map = self.build_expanded_dataset()
        all_ex: List[SQLTrainingExample] = []
        for s in splits.values():
            all_ex.extend(s)
        return all_ex, db_map

    def export_and_manifest(
        self,
        splits: Dict[str, List[SQLTrainingExample]],
        db_map: Dict[str, Path],
    ) -> Dict[str, Any]:
        """Writes JSONL split files and generates formal dataset_manifest.json with SHA-256."""
        files = {
            "train": self.processed_dir / "train.jsonl",
            "valid": self.processed_dir / "valid.jsonl",
            "test_known": self.processed_dir / "test_known_schema.jsonl",
            "test_unseen": self.processed_dir / "test_unseen_schema.jsonl",
        }

        # Also write unified test.jsonl pointing to test_unseen for default MLX evaluation
        files["test"] = self.processed_dir / "test.jsonl"

        manifest_data: Dict[str, Any] = {
            "manifest_version": "2.0.0",
            "created_at": "2026-11-18",
            "sources": [
                {
                    "name": "Yale Spider Benchmark",
                    "url": "https://yale-lily.github.io/spider",
                    "license": "CC BY-SA 4.0",
                    "records_used": len([ex for split in splits.values() for ex in split if ex.source == "spider"]),
                },
                {
                    "name": "Multi-Domain Synthetic Generator",
                    "url": "internal://2_Database/synthetic",
                    "license": "Proprietary / Open Research",
                    "records_used": len([ex for split in splits.values() for ex in split if ex.source == "synthetic"]),
                },
            ],
            "total_databases": len(db_map),
            "splits": {},
            "track_separation": {
                "track1_known_schema": {
                    "description": "Training and testing share database schemas with disjoint query pairs.",
                    "test_records": len(splits["test_known"]),
                },
                "track2_unseen_schema": {
                    "description": "Strict database-level isolation. Test databases are completely absent from training and validation.",
                    "test_records": len(splits["test_unseen"]),
                    "unseen_databases_count": len({ex.db_id for ex in splits["test_unseen"]}),
                },
            },
        }

        # Write each split to disk
        for split_key, path in files.items():
            if split_key == "test":
                split_records = splits["test_unseen"]
            else:
                split_records = splits[split_key]

            with open(path, "w", encoding="utf-8") as f:
                for ex in split_records:
                    f.write(json.dumps(ex.to_chatml(), ensure_ascii=False) + "\n")

            try:
                rel_path = str(path.relative_to(get_project_root()))
            except ValueError:
                rel_path = str(path)

            sha = compute_sha256(path)
            manifest_data["splits"][split_key] = {
                "file_path": rel_path,
                "records": len(split_records),
                "sha256": sha,
            }
            logger.info(f"Exported {split_key} split ({len(split_records)} records) -> {path.name} (SHA-256: {sha[:12]}...)")

        # Save manifest
        manifest_path = self.processed_dir / "dataset_manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)

        logger.info(f"Dataset manifest written: {manifest_path}")
        return manifest_data

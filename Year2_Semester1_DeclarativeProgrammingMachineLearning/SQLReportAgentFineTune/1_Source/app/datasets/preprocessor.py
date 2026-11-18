"""Dataset preprocessing and JSONL formatting for MLX-LM ChatML training."""

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
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
    db_id: str
    question: str
    query: str
    schema_text: str
    system_prompt: str = DEFAULT_SYSTEM_PROMPT

    def to_chatml(self) -> Dict[str, List[Dict[str, str]]]:
        """Converts example into Qwen/ChatML messages format for MLX-LM."""
        user_prompt = (
            f"Database Schema:\n{self.schema_text}\n\n"
            f"User Question:\n{self.question}\n\n"
            "Generate the SQLite query to answer the question."
        )
        assistant_reply = f"```sql\n{self.query.strip()}\n```"

        return {
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt},
                {"role": "assistant", "content": assistant_reply},
            ]
        }


class DatasetPreprocessor:
    """Consolidates benchmark and synthetic datasets, applies schema context, and builds splits."""

    def __init__(self, processed_dir: Optional[Union[str, Path]] = None):
        if processed_dir is None:
            self.processed_dir = get_project_root() / "2_Database" / "processed"
        else:
            self.processed_dir = Path(processed_dir).resolve()
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    def build_all_examples(self) -> Tuple[List[SQLTrainingExample], Dict[str, Path]]:
        """Collects all synthetic, Spider, and BIRD samples and couples with SQLite schemas."""
        db_map: Dict[str, Path] = {}
        examples: List[SQLTrainingExample] = []

        # 1. Synthetic samples
        synth_gen = SyntheticDatasetGenerator()
        synth_samples, synth_dbs = synth_gen.generate_all()
        db_map.update(synth_dbs)

        for s in synth_samples:
            schema = SchemaManager.extract_schema_from_sqlite(synth_dbs[s.db_id])
            schema_txt = SchemaFormatter.format_for_prompt(schema)
            examples.append(
                SQLTrainingExample(
                    db_id=s.db_id,
                    question=s.question,
                    query=s.query,
                    schema_text=schema_txt,
                )
            )

        # 2. Spider bundled samples
        spider_ds = SpiderDataset()
        spider_dbs = spider_ds.setup_bundled_databases()
        db_map.update(spider_dbs)

        for sp in spider_ds.get_bundled_spider_examples():
            schema = SchemaManager.extract_schema_from_sqlite(spider_dbs[sp.db_id])
            schema_txt = SchemaFormatter.format_for_prompt(schema)
            examples.append(
                SQLTrainingExample(
                    db_id=sp.db_id,
                    question=sp.question,
                    query=sp.query,
                    schema_text=schema_txt,
                )
            )

        # 3. BIRD bundled samples
        bird_ds = BIRDDataset()
        bird_db = bird_ds.setup_bundled_database()
        db_map["financial"] = bird_db

        for bi in bird_ds.get_bundled_bird_examples():
            schema = SchemaManager.extract_schema_from_sqlite(bird_db)
            schema_txt = SchemaFormatter.format_for_prompt(schema)
            examples.append(
                SQLTrainingExample(
                    db_id=bi.db_id,
                    question=bi.question,
                    query=bi.query,
                    schema_text=schema_txt,
                )
            )

        logger.info(f"Loaded {len(examples)} verified Text-to-SQL training examples across {len(db_map)} databases.")
        return examples, db_map

    def split_and_export(
        self,
        examples: List[SQLTrainingExample],
        train_ratio: float = 0.85,
        val_ratio: float = 0.10,
        seed: int = 42,
    ) -> Dict[str, Path]:
        """Partitions examples and writes train.jsonl, valid.jsonl, and test.jsonl."""
        rng = random.Random(seed)
        shuffled = list(examples)
        rng.shuffle(shuffled)

        n = len(shuffled)
        n_train = max(1, int(n * train_ratio))
        n_val = max(1, int(n * val_ratio))

        train_set = shuffled[:n_train]
        valid_set = shuffled[n_train : n_train + n_val]
        test_set = shuffled[n_train + n_val :]
        if not test_set:
            test_set = valid_set[:1]

        files = {
            "train": self.processed_dir / "train.jsonl",
            "valid": self.processed_dir / "valid.jsonl",
            "test": self.processed_dir / "test.jsonl",
        }

        for split_name, dataset in [("train", train_set), ("valid", valid_set), ("test", test_set)]:
            path = files[split_name]
            with open(path, "w", encoding="utf-8") as f:
                for ex in dataset:
                    f.write(json.dumps(ex.to_chatml(), ensure_ascii=False) + "\n")
            logger.info(f"Exported {split_name} split with {len(dataset)} records -> {path}")

        return files

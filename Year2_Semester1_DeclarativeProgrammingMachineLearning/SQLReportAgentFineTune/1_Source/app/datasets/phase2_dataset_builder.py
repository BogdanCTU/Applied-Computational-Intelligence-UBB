"""Builder for Phase II controlled experimental datasets (A: Direct, B: Grounded, C: Grounded + Distractors)."""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from app.core.config import get_project_root
from app.core.logging import get_logger
from app.database.schema_manager import DatabaseSchema, SchemaManager
from app.datasets.ast_annotator import ASTSchemaAnnotator
from app.datasets.preprocessor import DatasetPreprocessor, SQLTrainingExample
from app.datasets.schema_formatter import SchemaFormatter
from app.datasets.synthetic_grounded import ErrorDrivenSyntheticGenerator

logger = get_logger(__name__)

SYSTEM_PROMPT_DIRECT = (
    "You are a specialized Text-to-SQL AI. Given the SQLite database schema and user question, "
    "generate a syntactically correct SQLite query that precisely answers the question. "
    "Output ONLY the SQL code enclosed in a ```sql code block."
)

SYSTEM_PROMPT_GROUNDED = (
    "You are a specialized Text-to-SQL AI. Given the SQLite database schema and user question, "
    "first identify the relevant schema elements under <SCHEMA_SELECTION> (TABLES, COLUMNS, and RELATIONSHIPS), "
    "then generate the precise SQLite query enclosed under <SQL>."
)


def compute_file_sha256(path: Path) -> str:
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            sha.update(chunk)
    return sha.hexdigest()


class Phase2DatasetBuilder:
    """Creates the three controlled experimental dataset variants for Phase II."""

    def __init__(self, output_dir: Optional[Path] = None):
        self.root = get_project_root()
        self.output_dir = output_dir or (self.root / "2_Database" / "processed")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.annotator = ASTSchemaAnnotator()
        self._schema_cache: Dict[str, DatabaseSchema] = {}

    def _get_schema(self, db_id: str, db_path: Path) -> DatabaseSchema:
        if db_id not in self._schema_cache:
            self._schema_cache[db_id] = SchemaManager.extract_schema_from_sqlite(db_path, db_id=db_id)
        return self._schema_cache[db_id]

    def _format_pruned_schema(self, full_schema: DatabaseSchema, relevant_tables: List[str]) -> str:
        """Formats a schema subset containing only the relevant tables and their mutual foreign keys."""
        rel_set = {t.lower() for t in relevant_tables}
        lines = [f"Database Schema [{full_schema.db_id}]:"]
        for t_name, table in full_schema.tables.items():
            if t_name.lower() in rel_set:
                col_strs = [f"{col.name} ({col.data_type}{' [PK]' if col.is_pk else ''})" for col in table.columns]
                lines.append(f"- Table `{t_name}`: " + ", ".join(col_strs))
                for fk in table.foreign_keys:
                    if fk.ref_table.lower() in rel_set:
                        lines.append(f"  * FK: {t_name}.{fk.column} -> {fk.ref_table}.{fk.ref_column}")
        return "\n".join(lines)

    def build_all(self) -> Dict[str, Any]:
        """Builds Dataset A, B, and C for train and validation splits."""
        preprocessor = DatasetPreprocessor()
        splits, db_map = preprocessor.build_expanded_dataset(seed=42)

        raw_train = splits["train"]
        raw_valid = splits["valid"]

        # Ingest Error-Driven Synthetic Examples into Train
        synth_db_dir = self.root / "2_Database" / "synthetic" / "databases"
        if not synth_db_dir.exists():
            synth_db_dir = self.root / "2_Database" / "synthetic"
        synth_gen = ErrorDrivenSyntheticGenerator(synth_db_dir)
        synth_examples = synth_gen.generate_and_validate()

        for s in synth_examples:
            schema_txt = SchemaFormatter.format_for_prompt(self._get_schema(s.db_id, db_map[s.db_id]))
            raw_train.append(
                SQLTrainingExample(
                    example_id=s.example_id,
                    db_id=s.db_id,
                    question=s.question,
                    query=s.query,
                    schema_text=schema_txt,
                    source=s.source,
                    track=s.track,
                    split="train",
                    difficulty=s.difficulty,
                )
            )

        logger.info(f"Augmented train split with {len(synth_examples)} error-driven synthetic examples (total: {len(raw_train)}).")

        # Process Train and Valid
        train_a, train_b, train_c = self._process_split(raw_train, db_map, split_name="train")
        valid_a, valid_b, valid_c = self._process_split(raw_valid, db_map, split_name="valid")

        # Write files
        files = {
            "train_a": self.output_dir / "phase2_train_a.jsonl",
            "valid_a": self.output_dir / "phase2_valid_a.jsonl",
            "train_b": self.output_dir / "phase2_train_b.jsonl",
            "valid_b": self.output_dir / "phase2_valid_b.jsonl",
            "train_c": self.output_dir / "phase2_train_c.jsonl",
            "valid_c": self.output_dir / "phase2_valid_c.jsonl",
        }

        self._write_jsonl(files["train_a"], train_a)
        self._write_jsonl(files["valid_a"], valid_a)
        self._write_jsonl(files["train_b"], train_b)
        self._write_jsonl(files["valid_b"], valid_b)
        self._write_jsonl(files["train_c"], train_c)
        self._write_jsonl(files["valid_c"], valid_c)

        # Generate Manifest
        manifest = {
            "metadata": {
                "phase": 2,
                "strategy": "Schema-Grounded Controlled LoRA Fine-Tuning",
                "train_records_per_variant": len(train_a),
                "valid_records_per_variant": len(valid_a),
            },
            "datasets": {
                name: {
                    "path": str(path),
                    "records": len(train_a) if "train" in name else len(valid_a),
                    "sha256": compute_file_sha256(path),
                }
                for name, path in files.items()
            },
        }

        manifest_path = self.output_dir / "phase2_manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        logger.info(f"Phase II datasets and manifest exported successfully: {manifest_path}")
        return manifest

    def _process_split(
        self,
        examples: List[SQLTrainingExample],
        db_map: Dict[str, Path],
        split_name: str,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        ds_a: List[Dict[str, Any]] = []
        ds_b: List[Dict[str, Any]] = []
        ds_c: List[Dict[str, Any]] = []

        for ex in examples:
            db_path = db_map.get(ex.db_id)
            if not db_path:
                continue

            schema = self._get_schema(ex.db_id, db_path)
            full_schema_txt = SchemaFormatter.format_for_prompt(schema)
            res = self.annotator.annotate(ex.query, schema, example_id=ex.example_id)

            # Skip rejected queries if any
            if res.status == "rejected":
                continue

            # Variant A: Direct SQL (Full Schema Prompt -> Direct SQL Target)
            user_msg_a = (
                f"Database Schema:\n{full_schema_txt}\n\n"
                f"User Question:\n{ex.question}\n\n"
                "Generate the SQLite query to answer the question."
            )
            asst_msg_a = f"```sql\n{ex.query.strip()}\n```"
            ds_a.append({
                "example_id": ex.example_id,
                "db_id": ex.db_id,
                "variant": "dataset_a_direct",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT_DIRECT},
                    {"role": "user", "content": user_msg_a},
                    {"role": "assistant", "content": asst_msg_a},
                ],
            })

            # Variant B: Schema-Grounded (Pruned Relevant Schema Prompt -> Structured Target)
            pruned_schema_txt = self._format_pruned_schema(schema, res.tables)
            user_msg_b = (
                f"Database Schema:\n{pruned_schema_txt}\n\n"
                f"User Question:\n{ex.question}\n\n"
                "First identify the relevant schema elements under <SCHEMA_SELECTION>, then output the SQLite query under <SQL>."
            )
            asst_msg_b = res.structured_target
            ds_b.append({
                "example_id": ex.example_id,
                "db_id": ex.db_id,
                "variant": "dataset_b_grounded",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT_GROUNDED},
                    {"role": "user", "content": user_msg_b},
                    {"role": "assistant", "content": asst_msg_b},
                ],
            })

            # Variant C: Schema-Grounded with Distractors (Full Schema Prompt -> Structured Target)
            user_msg_c = (
                f"Database Schema:\n{full_schema_txt}\n\n"
                f"User Question:\n{ex.question}\n\n"
                "First identify the relevant schema elements under <SCHEMA_SELECTION>, then output the SQLite query under <SQL>."
            )
            asst_msg_c = res.structured_target
            ds_c.append({
                "example_id": ex.example_id,
                "db_id": ex.db_id,
                "variant": "dataset_c_distractors",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT_GROUNDED},
                    {"role": "user", "content": user_msg_c},
                    {"role": "assistant", "content": asst_msg_c},
                ],
            })

        logger.info(f"Processed split '{split_name}': {len(ds_a)} records per variant.")
        return ds_a, ds_b, ds_c

    def _write_jsonl(self, path: Path, records: List[Dict[str, Any]]) -> None:
        with open(path, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")

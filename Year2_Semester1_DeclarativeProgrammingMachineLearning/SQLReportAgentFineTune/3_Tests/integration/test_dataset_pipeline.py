"""Integration tests for dataset building, splitting, and SQLite validation."""

import json
from pathlib import Path
from app.datasets.preprocessor import DatasetPreprocessor
from app.database.sqlite_executor import SQLiteExecutor


def test_dataset_pipeline_end_to_end(tmp_path: Path):
    preprocessor = DatasetPreprocessor(processed_dir=tmp_path / "processed")
    examples, db_map = preprocessor.build_all_examples()

    assert len(examples) > 0
    assert len(db_map) >= 3

    # Ensure every database exists and is queryable
    for db_id, db_path in db_map.items():
        assert db_path.exists()
        executor = SQLiteExecutor(db_path)
        tables_res = executor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        assert tables_res.success is True
        assert tables_res.row_count > 0

    # Ensure ChatML structure in exported splits
    splits = preprocessor.split_and_export(examples, train_ratio=0.8, val_ratio=0.1)
    assert splits["train"].exists()
    assert splits["valid"].exists()
    assert splits["test"].exists()

    with open(splits["train"], "r", encoding="utf-8") as f:
        first_line = json.loads(f.readline())
        assert "messages" in first_line
        assert len(first_line["messages"]) == 3
        assert first_line["messages"][0]["role"] == "system"
        assert first_line["messages"][1]["role"] == "user"
        assert first_line["messages"][2]["role"] == "assistant"
        assert "```sql" in first_line["messages"][2]["content"]

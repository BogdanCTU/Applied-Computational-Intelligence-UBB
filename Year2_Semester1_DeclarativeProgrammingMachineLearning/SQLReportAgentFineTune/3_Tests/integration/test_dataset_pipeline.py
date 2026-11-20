"""Integration tests for dataset building, splitting, and SQLite validation."""

import json
from pathlib import Path
from app.datasets.preprocessor import DatasetPreprocessor
from app.database.sqlite_executor import SQLiteExecutor


def test_dataset_pipeline_end_to_end(tmp_path: Path):
    preprocessor = DatasetPreprocessor(processed_dir=tmp_path / "processed")
    splits, db_map = preprocessor.build_expanded_dataset(train_target=10, val_target=5)

    assert "train" in splits
    assert "valid" in splits
    assert "test_known" in splits
    assert "test_unseen" in splits
    assert len(db_map) >= 8

    # Ensure every database exists and is queryable
    for db_id, db_path in list(db_map.items())[:10]:
        assert db_path.exists()
        executor = SQLiteExecutor(db_path)
        tables_res = executor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        assert tables_res.success is True
        assert tables_res.row_count > 0

    # Ensure export and manifest work
    manifest = preprocessor.export_and_manifest(splits, db_map)
    assert (tmp_path / "processed" / "train.jsonl").exists()
    assert (tmp_path / "processed" / "valid.jsonl").exists()
    assert (tmp_path / "processed" / "test_known_schema.jsonl").exists()
    assert (tmp_path / "processed" / "test_unseen_schema.jsonl").exists()
    assert (tmp_path / "processed" / "dataset_manifest.json").exists()

    with open(tmp_path / "processed" / "train.jsonl", "r", encoding="utf-8") as f:
        first_line = json.loads(f.readline())
        assert "messages" in first_line
        assert len(first_line["messages"]) == 3
        assert first_line["messages"][0]["role"] == "system"
        assert first_line["messages"][1]["role"] == "user"
        assert first_line["messages"][2]["role"] == "assistant"
        assert "```sql" in first_line["messages"][2]["content"]

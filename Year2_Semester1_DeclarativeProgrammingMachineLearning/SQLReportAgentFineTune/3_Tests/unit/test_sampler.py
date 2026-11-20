"""Unit tests for stratified sampling and SQL complexity classification."""

import tempfile
from pathlib import Path
from app.datasets.preprocessor import SQLTrainingExample
from app.evaluation.sampler import StratifiedSampler, classify_sql_complexity


def test_classify_sql_complexity():
    easy_sql = "SELECT name, age FROM users WHERE age > 21;"
    medium_sql = "SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id;"
    hard_sql = "SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id WHERE u.age IN (SELECT age FROM vip_users);"
    extra_hard_sql = """
    WITH cte AS (SELECT user_id, sum(total) as s FROM orders GROUP BY user_id)
    SELECT u.name, c.s FROM users u
    JOIN cte c ON u.id = c.user_id
    JOIN profiles p ON u.id = p.user_id
    JOIN logs l ON u.id = l.user_id;
    """

    assert classify_sql_complexity(easy_sql) == "easy"
    assert classify_sql_complexity(medium_sql) == "medium"
    assert classify_sql_complexity(hard_sql) in ["hard", "extra_hard"]
    assert classify_sql_complexity(extra_hard_sql) == "extra_hard"


def test_stratified_sampler_distribution():
    # Construct synthetic example pool across 3 DBs and multiple complexities
    examples = []
    for db in ["db1", "db2", "db3"]:
        for i in range(20):
            sql = "SELECT a FROM t;" if i % 2 == 0 else "SELECT a, b FROM t1 JOIN t2 ON t1.id = t2.id;"
            examples.append(
                SQLTrainingExample(
                    example_id=f"{db}_sample_{i}",
                    db_id=db,
                    question=f"Question {i}",
                    query=sql,
                    schema_text="CREATE TABLE t (a INT);",
                    source="spider",
                    track="track2_unseen",
                    split="test_unseen",
                )
            )

    sampler = StratifiedSampler(seed=42)
    sample = sampler.sample_unseen(examples, target_size=15)
    assert len(sample) == 15

    # Check all DBs represented
    dbs = {s.db_id for s in sample}
    assert dbs == {"db1", "db2", "db3"}

    with tempfile.TemporaryDirectory() as tmp:
        manifest_file = Path(tmp) / "manifest.json"
        sampler.export_sample_manifest(sample, population_size=60, output_file=manifest_file)
        assert manifest_file.exists()

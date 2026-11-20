"""Runner script for Phase I benchmark evaluation across all 4 model configurations."""

import json
import time
from pathlib import Path
from typing import Dict, List

from app.core.config import get_project_root
from app.core.logging import get_logger
from app.datasets.preprocessor import DatasetPreprocessor, SQLTrainingExample
from app.evaluation.comparator import ModelComparator
from app.evaluation.execution_eval import ExecutionEvaluator
from app.inference.engine import InferenceEngine

logger = get_logger(__name__)


def run_benchmark():
    root = get_project_root()
    base_model_path = str(root / "6_Models" / "base" / "Qwen2.5-Coder-3B-Instruct-4bit")
    adapters_dir = root / "6_Models" / "adapters"

    adapter_a = str(adapters_dir / "exp_a_lora_r8")
    adapter_b = str(adapters_dir / "exp_b_lora_r16")
    adapter_c = str(adapters_dir / "exp_c_lora_r32")

    # 1. Load Preprocessor and DB map
    preprocessor = DatasetPreprocessor()
    splits, db_map = preprocessor.build_expanded_dataset(seed=42)

    # 2. Load 200 Stratified Unseen Samples from Manifest
    manifest_path = root / "2_Database" / "processed" / "evaluation_sample_unseen_200.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    manifest_ids = set(manifest["sample_ids"])
    unseen_200 = [ex for ex in splits["test_unseen"] if ex.example_id in manifest_ids]
    # Keep exact manifest order
    id_to_ex = {ex.example_id: ex for ex in unseen_200}
    unseen_200 = [id_to_ex[mid] for mid in manifest["sample_ids"]]

    # 3. Load 100 Known Schema Samples
    known_100 = splits["test_known"]

    logger.info(f"Loaded {len(unseen_200)} stratified unseen samples and {len(known_100)} known samples.")

    runs = [
        # Track 2: 200 Stratified Unseen
        {
            "name": "phase1_baseline_unseen200",
            "model": base_model_path,
            "adapter": None,
            "examples": unseen_200,
            "track": "unseen",
        },
        {
            "name": "phase1_exp_a_lora_r8_unseen200",
            "model": base_model_path,
            "adapter": adapter_a,
            "examples": unseen_200,
            "track": "unseen",
        },
        {
            "name": "phase1_exp_b_lora_r16_unseen200",
            "model": base_model_path,
            "adapter": adapter_b,
            "examples": unseen_200,
            "track": "unseen",
        },
        {
            "name": "phase1_exp_c_lora_r32_unseen200",
            "model": base_model_path,
            "adapter": adapter_c,
            "examples": unseen_200,
            "track": "unseen",
        },
        # Track 1: 100 Known
        {
            "name": "phase1_baseline_known100",
            "model": base_model_path,
            "adapter": None,
            "examples": known_100,
            "track": "known",
        },
        {
            "name": "phase1_exp_b_lora_r16_known100",
            "model": base_model_path,
            "adapter": adapter_b,
            "examples": known_100,
            "track": "known",
        },
    ]

    results_summary = {}

    for run_cfg in runs:
        run_name = run_cfg["name"]
        logger.info("=" * 60)
        logger.info(f"Starting run: {run_name} (Adapter: {run_cfg['adapter']})")
        logger.info("=" * 60)

        engine = InferenceEngine(
            model_path_or_id=run_cfg["model"],
            adapter_path=run_cfg["adapter"],
            lazy_load=False,
        )
        evaluator = ExecutionEvaluator(engine=engine, db_map=db_map)
        metrics, _ = evaluator.evaluate(run_cfg["examples"], run_name=run_name)
        results_summary[run_name] = metrics.to_dict()

        logger.info(
            f"Finished {run_name}: EX={metrics.execution_accuracy}% | EM={metrics.exact_match_rate}% | "
            f"VSR={metrics.valid_sql_rate}% | Latency(avg/med/p90)={metrics.average_latency_ms}/{metrics.median_latency_ms}/{metrics.p90_latency_ms}ms"
        )

    # 4. Generate Paired Comparisons
    comparator = ModelComparator()

    comparisons_to_run = [
        ("phase1_baseline_unseen200", "phase1_exp_a_lora_r8_unseen200"),
        ("phase1_baseline_unseen200", "phase1_exp_b_lora_r16_unseen200"),
        ("phase1_baseline_unseen200", "phase1_exp_c_lora_r32_unseen200"),
        ("phase1_baseline_known100", "phase1_exp_b_lora_r16_known100"),
    ]

    for base_n, tuned_n in comparisons_to_run:
        logger.info(f"Comparing {base_n} vs {tuned_n}...")
        comparator.compare(base_n, tuned_n)

    logger.info("Phase I full benchmark evaluation and comparisons completed successfully!")


if __name__ == "__main__":
    run_benchmark()

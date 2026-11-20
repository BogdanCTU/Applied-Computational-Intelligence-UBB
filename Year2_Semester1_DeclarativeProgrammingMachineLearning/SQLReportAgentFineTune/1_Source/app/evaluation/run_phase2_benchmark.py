"""Runner script for Phase II evaluation across Dev-200 and Confirmation-200 benchmarks."""

import json
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List

from app.core.config import get_project_root
from app.core.logging import get_logger
from app.datasets.preprocessor import DatasetPreprocessor
from app.evaluation.comparator import ModelComparator
from app.evaluation.execution_eval import ExecutionEvaluator
from app.inference.engine import InferenceEngine

logger = get_logger(__name__)


def run_phase2_benchmark():
    root = get_project_root()
    base_model_path = str(root / "6_Models" / "base" / "Qwen2.5-Coder-3B-Instruct-4bit")
    adapters_dir = root / "6_Models" / "adapters"

    adapter_a = str(adapters_dir / "exp_phase2_a_direct_r8")
    adapter_b = str(adapters_dir / "exp_phase2_b_grounded_r8")
    adapter_c = str(adapters_dir / "exp_phase2_c_distractors_r8")

    # 1. Load Preprocessor and DB Map
    preprocessor = DatasetPreprocessor()
    splits, db_map = preprocessor.build_expanded_dataset(seed=42)

    # 2. Load Dev-200 Samples
    dev_manifest_path = root / "2_Database" / "processed" / "evaluation_sample_unseen_200.json"
    with open(dev_manifest_path, "r", encoding="utf-8") as f:
        dev_manifest = json.load(f)
    id_to_unseen = {ex.example_id: ex for ex in splits["test_unseen"]}
    dev_200 = [id_to_unseen[mid] for mid in dev_manifest["sample_ids"]]

    # 3. Load Confirmation-200 Samples
    conf_manifest_path = root / "2_Database" / "processed" / "confirmation_sample_unseen_200.json"
    with open(conf_manifest_path, "r", encoding="utf-8") as f:
        conf_manifest = json.load(f)
    conf_200 = [id_to_unseen[mid] for mid in conf_manifest["sample_ids"]]

    logger.info(f"Loaded {len(dev_200)} Dev-200 and {len(conf_200)} Confirmation-200 unseen samples.")

    # 4. Copy Phase I Baseline Dev-200 to Phase 2 for Exact Deterministic Parity
    phase1_base_dir = root / "7_Results" / "phase1_baseline_unseen200"
    phase2_base_dev_dir = root / "7_Results" / "phase2_base_dev200"
    if phase1_base_dir.exists() and not phase2_base_dev_dir.exists():
        shutil.copytree(phase1_base_dir, phase2_base_dev_dir)
        logger.info(f"Copied deterministic Phase I baseline results to {phase2_base_dev_dir}")

    # Define Evaluation Runs
    runs = [
        # --- Development Benchmark (Dev-200) ---
        {
            "name": "phase2_exp_a_direct_dev200",
            "model": base_model_path,
            "adapter": adapter_a,
            "examples": dev_200,
            "prompt_mode": "direct",
            "benchmark": "dev_200",
        },
        {
            "name": "phase2_exp_b_grounded_dev200",
            "model": base_model_path,
            "adapter": adapter_b,
            "examples": dev_200,
            "prompt_mode": "grounded",
            "benchmark": "dev_200",
        },
        {
            "name": "phase2_exp_c_distractors_dev200",
            "model": base_model_path,
            "adapter": adapter_c,
            "examples": dev_200,
            "prompt_mode": "grounded",
            "benchmark": "dev_200",
        },
        # --- Final Confirmation Benchmark (Confirmation-200) ---
        {
            "name": "phase2_base_conf200",
            "model": base_model_path,
            "adapter": None,
            "examples": conf_200,
            "prompt_mode": "direct",
            "benchmark": "conf_200",
        },
        {
            "name": "phase2_exp_a_direct_conf200",
            "model": base_model_path,
            "adapter": adapter_a,
            "examples": conf_200,
            "prompt_mode": "direct",
            "benchmark": "conf_200",
        },
        {
            "name": "phase2_exp_b_grounded_conf200",
            "model": base_model_path,
            "adapter": adapter_b,
            "examples": conf_200,
            "prompt_mode": "grounded",
            "benchmark": "conf_200",
        },
        {
            "name": "phase2_exp_c_distractors_conf200",
            "model": base_model_path,
            "adapter": adapter_c,
            "examples": conf_200,
            "prompt_mode": "grounded",
            "benchmark": "conf_200",
        },
    ]

    for run_cfg in runs:
        run_name = run_cfg["name"]
        logger.info("=" * 60)
        logger.info(f"Starting Phase II Run: {run_name} (Mode: {run_cfg['prompt_mode']}, Benchmark: {run_cfg['benchmark']})")
        logger.info("=" * 60)

        engine = InferenceEngine(
            model_path_or_id=run_cfg["model"],
            adapter_path=run_cfg["adapter"],
            lazy_load=False,
            prompt_mode=run_cfg["prompt_mode"],
        )
        evaluator = ExecutionEvaluator(engine=engine, db_map=db_map)
        metrics, _ = evaluator.evaluate(run_cfg["examples"], run_name=run_name)

        logger.info(
            f"Finished {run_name}: EX={metrics.execution_accuracy}% | EM={metrics.exact_match_rate}% | "
            f"FVR={metrics.valid_sql_rate}% | ESR={metrics.executable_sql_rate}% | "
            f"Table F1={metrics.schema_table_f1}% | Col F1={metrics.schema_col_f1}%"
        )

    # 5. Generate Paired Statistical Comparisons
    comparator = ModelComparator()

    comparisons_to_run = [
        # Dev-200 Comparisons
        ("phase2_base_dev200", "phase2_exp_a_direct_dev200"),
        ("phase2_base_dev200", "phase2_exp_b_grounded_dev200"),
        ("phase2_base_dev200", "phase2_exp_c_distractors_dev200"),
        ("phase2_exp_a_direct_dev200", "phase2_exp_b_grounded_dev200"),
        ("phase2_exp_a_direct_dev200", "phase2_exp_c_distractors_dev200"),
        # Confirmation-200 Comparisons
        ("phase2_base_conf200", "phase2_exp_a_direct_conf200"),
        ("phase2_base_conf200", "phase2_exp_b_grounded_conf200"),
        ("phase2_base_conf200", "phase2_exp_c_distractors_conf200"),
        ("phase2_exp_a_direct_conf200", "phase2_exp_b_grounded_conf200"),
        ("phase2_exp_a_direct_conf200", "phase2_exp_c_distractors_conf200"),
    ]

    for base_n, tuned_n in comparisons_to_run:
        logger.info(f"Comparing {base_n} vs {tuned_n}...")
        try:
            comparator.compare(base_n, tuned_n)
        except Exception as e:
            logger.error(f"Comparison failed for {base_n} vs {tuned_n}: {e}")

    logger.info("Phase II full benchmark evaluation and comparisons completed successfully!")


if __name__ == "__main__":
    run_phase2_benchmark()

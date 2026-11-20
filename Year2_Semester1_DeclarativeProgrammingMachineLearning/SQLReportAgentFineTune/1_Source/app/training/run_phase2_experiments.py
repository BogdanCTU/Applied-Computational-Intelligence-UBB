"""Runner script for Phase II controlled LoRA training experiments (A, B, C)."""

import json
import time
from pathlib import Path

from app.core.config import get_project_root
from app.core.logging import get_logger
from app.training.config import TrainingHyperparameters
from app.training.trainer import LoRATrainer

logger = get_logger(__name__)


def run_phase2_training(iters: int = 60):
    root = get_project_root()
    base_model = str(root / "6_Models" / "base" / "Qwen2.5-Coder-3B-Instruct-4bit")
    processed_dir = root / "2_Database" / "processed"

    experiments = [
        {
            "run_name": "exp_phase2_a_direct_r8",
            "data_dir": processed_dir / "variant_a",
            "variant": "Dataset A (Direct SQL)",
        },
        {
            "run_name": "exp_phase2_b_grounded_r8",
            "data_dir": processed_dir / "variant_b",
            "variant": "Dataset B (Schema-Grounded, Relevant Schema)",
        },
        {
            "run_name": "exp_phase2_c_distractors_r8",
            "data_dir": processed_dir / "variant_c",
            "variant": "Dataset C (Schema-Grounded with Distractors, Full Schema)",
        },
    ]

    hyperparams = TrainingHyperparameters(
        fine_tune_type="lora",
        iters=iters,
        batch_size=2,
        learning_rate=1e-4,
        steps_per_report=10,
        steps_per_eval=20,
        save_every=20,
        lora_rank=8,
        lora_alpha=16.0,
        val_batches=10,
        mask_prompt=True,
        grad_checkpoint=True,
        max_seq_length=2048,
    )

    summaries = {}

    for exp in experiments:
        run_name = exp["run_name"]
        logger.info("=" * 60)
        logger.info(f"Starting Phase II Training: {run_name} [{exp['variant']}]")
        logger.info(f"Data directory: {exp['data_dir']}")
        logger.info(f"Hyperparameters: rank={hyperparams.lora_rank}, alpha={hyperparams.lora_alpha}, iters={hyperparams.iters}")
        logger.info("=" * 60)

        trainer = LoRATrainer(
            base_model=base_model,
            data_dir=exp["data_dir"],
            hyperparameters=hyperparams,
        )

        t0 = time.perf_counter()
        summary = trainer.train(run_name=run_name)
        duration = round(time.perf_counter() - t0, 2)

        summaries[run_name] = {
            "success": summary.success,
            "duration_seconds": duration,
            "adapter_path": summary.adapter_path,
            "log_file": summary.log_file,
            "error": summary.error,
        }

        if summary.success:
            logger.info(f"Completed {run_name} successfully in {duration}s. Adapter at {summary.adapter_path}")
        else:
            logger.error(f"Failed {run_name}: {summary.error}")
            raise RuntimeError(f"Training failed for {run_name}: {summary.error}")

    out_file = root / "8_Logs" / "phase2_training_summaries.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summaries, f, indent=2)

    logger.info(f"Phase II all 3 experiments finished. Summary saved to {out_file}")


if __name__ == "__main__":
    run_phase2_training()

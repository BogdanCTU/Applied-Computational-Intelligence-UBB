"""Training runner for native Apple Silicon MLX-LM LoRA fine-tuning."""

import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from app.core.config import get_project_root
from app.core.logging import get_logger
from app.training.config import TrainingHyperparameters
from app.training.lora_manager import LoRAManager

logger = get_logger(__name__)


@dataclass
class TrainingSummary:
    run_name: str
    base_model: str
    adapter_path: str
    iterations: int
    duration_seconds: float
    success: bool
    log_file: str
    error: Optional[str] = None


class LoRATrainer:
    """Executes SFT fine-tuning via MLX-LM LoRA."""

    def __init__(
        self,
        base_model: str,
        data_dir: Optional[Union[str, Path]] = None,
        hyperparameters: Optional[TrainingHyperparameters] = None,
        logs_dir: Optional[Union[str, Path]] = None,
    ):
        self.base_model = str(base_model)
        if data_dir is None:
            self.data_dir = get_project_root() / "2_Database" / "processed"
        else:
            self.data_dir = Path(data_dir).resolve()
        self.hyperparameters = hyperparameters or TrainingHyperparameters()
        if logs_dir is None:
            self.logs_dir = get_project_root() / "8_Logs"
        else:
            self.logs_dir = Path(logs_dir).resolve()
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.lora_manager = LoRAManager()

    def train(self, run_name: str = "lora_run") -> TrainingSummary:
        """Executes fine-tuning using MLX-LM lora CLI."""
        adapter_dir = self.lora_manager.get_adapter_path(run_name)
        log_file = self.logs_dir / f"training_{run_name}.log"

        # Write YAML config for MLX-LM
        cfg_file = adapter_dir / "lora_config.yaml"
        self.hyperparameters.save_yaml(cfg_file)

        cmd = [
            sys.executable,
            "-m",
            "mlx_lm",
            "lora",
            "--model",
            self.base_model,
            "--data",
            str(self.data_dir),
            "--train",
            "--config",
            str(cfg_file),
            "--adapter-path",
            str(adapter_dir),
            "--iters",
            str(self.hyperparameters.iters),
            "--batch-size",
            str(self.hyperparameters.batch_size),
            "--learning-rate",
            str(self.hyperparameters.learning_rate),
            "--steps-per-report",
            str(self.hyperparameters.steps_per_report),
            "--steps-per-eval",
            str(self.hyperparameters.steps_per_eval),
            "--save-every",
            str(self.hyperparameters.save_every),
            "--max-seq-length",
            str(self.hyperparameters.max_seq_length),
        ]

        if self.hyperparameters.mask_prompt:
            cmd.append("--mask-prompt")
        if self.hyperparameters.grad_checkpoint:
            cmd.append("--grad-checkpoint")

        logger.info(f"Starting LoRA training run '{run_name}'...")
        logger.info(f"Command: {' '.join(cmd)}")

        start_time = time.perf_counter()
        success = False
        error_msg = None

        with open(log_file, "w", encoding="utf-8") as lf:
            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )
                if proc.stdout:
                    for line in proc.stdout:
                        lf.write(line)
                        lf.flush()
                        # Log report steps to console
                        if "Iter" in line or "Val" in line or "Loss" in line:
                            logger.info(f"[MLX Train] {line.strip()}")
                proc.wait()
                if proc.returncode == 0:
                    success = True
                    logger.info(f"Training run '{run_name}' completed successfully.")
                else:
                    error_msg = f"Process exited with error code {proc.returncode}"
                    logger.error(error_msg)
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Training failed with exception: {error_msg}")

        duration = round(time.perf_counter() - start_time, 2)
        return TrainingSummary(
            run_name=run_name,
            base_model=self.base_model,
            adapter_path=str(adapter_dir),
            iterations=self.hyperparameters.iters,
            duration_seconds=duration,
            success=success,
            log_file=str(log_file),
            error=error_msg,
        )

"""MLX-LM LoRA safety fine-tuning orchestrator, adapter fusion, and Ollama registration."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from source.config.settings import AppConfig, get_project_root
from source.fine_tuning.mlx_converter import OllamaMLXConverter
from source.inference.engine import verify_mlx_generation, verify_ollama_generation
from source.storage.database import DatabaseManager
from source.storage.models import TrainingRun
from source.utils.logging_utils import get_logger

logger = get_logger("trainer")

ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
VAL_LOSS_RE = re.compile(r"^\s*(\d+)\s+val\s+([0-9.]+)")
TRAIN_LOSS_RE = re.compile(r"^\s*(\d+)\s+([0-9.]+)\s+[▼▲]")


def parse_mlx_training_log(log_text: str) -> tuple[List[tuple[int, float]], List[tuple[int, float]]]:
    """Parse validation and training loss pairs from mlx_lm 0.32+ rich console output."""
    val_losses: List[tuple[int, float]] = []
    train_losses: List[tuple[int, float]] = []
    for raw_line in log_text.splitlines():
        clean = ANSI_ESCAPE_RE.sub("", raw_line)
        vm = VAL_LOSS_RE.match(clean)
        if vm:
            val_losses.append((int(vm.group(1)), float(vm.group(2))))
        tm = TRAIN_LOSS_RE.match(clean)
        if tm:
            train_losses.append((int(tm.group(1)), float(tm.group(2))))
    return val_losses, train_losses


class SafetyLoRATrainer:
    """Executes MLX-LM LoRA fine-tuning on Qwen3.5 4B, fuses adapters, and deploys to Ollama."""

    def __init__(self, config: AppConfig, db: DatabaseManager):
        self.config = config
        self.db = db
        self.converter = OllamaMLXConverter()

    def train_and_deploy(
        self,
        run_id: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        ft_cfg = self.config.fine_tuning
        root = get_project_root()
        ft_root = root / "2_FineTune"
        data_dir = ft_root / "03_Processed_Datasets"
        train_file = data_dir / "train.jsonl"
        valid_file = data_dir / "valid.jsonl"

        if not train_file.exists() or not valid_file.exists():
            raise FileNotFoundError(
                f"Training datasets not found in {data_dir}. Run generate-mitigation-data first."
            )

        train_count = sum(1 for _ in open(train_file, "r", encoding="utf-8"))
        val_count = sum(1 for _ in open(valid_file, "r", encoding="utf-8"))

        run_name = run_id or f"qwen35_4b_safety_lora_{uuid.uuid4().hex[:6]}"
        base_mlx_dir = ft_root / "07_Exported_Models" / "qwen3.5_4b_base_mlx"
        adapter_dir = ft_root / "06_Adapters" / run_name
        checkpoint_dir = ft_root / "05_Checkpoints" / run_name
        fused_dir = ft_root / "07_Exported_Models" / f"{run_name}_fused"
        ollama_staging = ft_root / "07_Exported_Models" / f"{run_name}_ollama"
        log_file = ft_root / "08_Training_Logs" / f"{run_name}.log"
        train_cfg_path = ft_root / "04_Training" / f"{run_name}_lora_config.yaml"

        for d in (adapter_dir, checkpoint_dir, fused_dir, ollama_staging, log_file.parent, train_cfg_path.parent):
            d.mkdir(parents=True, exist_ok=True)

        lora_yaml = {
            "fine_tune_type": ft_cfg.method,
            "optimizer": "adamw",
            "mask_prompt": ft_cfg.mask_prompt,
            "num_layers": ft_cfg.num_layers,
            "batch_size": ft_cfg.batch_size,
            "iters": ft_cfg.iters,
            "val_batches": ft_cfg.val_batches,
            "learning_rate": ft_cfg.learning_rate,
            "steps_per_report": ft_cfg.steps_per_report,
            "steps_per_eval": ft_cfg.steps_per_eval,
            "save_every": ft_cfg.save_every,
            "max_seq_length": ft_cfg.max_sequence_length,
            "grad_checkpoint": ft_cfg.grad_checkpoint,
            "seed": ft_cfg.seed,
            "lora_parameters": {
                "rank": ft_cfg.lora_rank,
                "alpha": ft_cfg.lora_alpha,
                "dropout": ft_cfg.lora_dropout,
                "scale": ft_cfg.lora_scale,
            },
        }
        train_cfg_path.write_text(yaml.safe_dump(lora_yaml, sort_keys=False), encoding="utf-8")

        if dry_run:
            return {
                "run_id": run_name,
                "dry_run": True,
                "base_model": self.config.model.baseline,
                "target_mitigated_model": self.config.model.mitigated,
                "train_examples": train_count,
                "val_examples": val_count,
                "hyperparameters": lora_yaml,
            }

        # 1. Reconstruct local MLX checkpoint from Ollama's qwen3.5:4b blobs
        if not (base_mlx_dir / "model.safetensors").exists():
            logger.info(f"Reconstructing local MLX base checkpoint from Ollama '{self.config.model.baseline}'...")
            export_info = self.converter.export_ollama_to_mlx(self.config.model.baseline, base_mlx_dir)
        else:
            export_info = {"reused_existing_mlx_base": True, "target_mlx_dir": str(base_mlx_dir)}

        # 2. Run MLX-LM LoRA training
        cmd = [
            sys.executable,
            "-m",
            "mlx_lm",
            "lora",
            "--model",
            str(base_mlx_dir),
            "--data",
            str(data_dir),
            "--train",
            "--config",
            str(train_cfg_path),
            "--adapter-path",
            str(adapter_dir),
            "--iters",
            str(ft_cfg.iters),
            "--batch-size",
            str(ft_cfg.batch_size),
            "--learning-rate",
            str(ft_cfg.learning_rate),
            "--steps-per-report",
            str(ft_cfg.steps_per_report),
            "--steps-per-eval",
            str(ft_cfg.steps_per_eval),
            "--save-every",
            str(ft_cfg.save_every),
            "--val-batches",
            str(ft_cfg.val_batches),
            "--max-seq-length",
            str(ft_cfg.max_sequence_length),
        ]
        if ft_cfg.mask_prompt:
            cmd.append("--mask-prompt")
        if ft_cfg.grad_checkpoint:
            cmd.append("--grad-checkpoint")

        logger.info(f"Launching MLX-LM LoRA fine-tuning: {' '.join(cmd)}")
        t0 = time.perf_counter()
        val_losses: List[tuple[int, float]] = []
        train_losses: List[tuple[int, float]] = []

        with open(log_file, "w", encoding="utf-8") as lf:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            assert proc.stdout is not None
            for line in proc.stdout:
                lf.write(line)
                lf.flush()
                clean = ANSI_ESCAPE_RE.sub("", line)
                vm = VAL_LOSS_RE.match(clean)
                if vm:
                    val_losses.append((int(vm.group(1)), float(vm.group(2))))
                    logger.info(f"[MLX-Val] {clean.strip()}")
                tm = TRAIN_LOSS_RE.match(clean)
                if tm:
                    train_losses.append((int(tm.group(1)), float(tm.group(2))))
                    logger.info(f"[MLX-Train] {clean.strip()}")
            proc.wait()
            if proc.returncode != 0:
                raise RuntimeError(f"MLX-LM LoRA training exited with code {proc.returncode}. See {log_file}")

        duration = round(time.perf_counter() - t0, 2)

        # Copy intermediate checkpoint files into 05_Checkpoints/
        for ckpt in adapter_dir.glob("*_adapters.safetensors"):
            dest = checkpoint_dir / ckpt.name
            dest.write_bytes(ckpt.read_bytes())

        # 3. Fuse trained LoRA adapter into base model weights (preserving nvfp4 quantization)
        fuse_cmd = [
            sys.executable,
            "-m",
            "mlx_lm",
            "fuse",
            "--model",
            str(base_mlx_dir),
            "--adapter-path",
            str(adapter_dir),
            "--save-path",
            str(fused_dir),
        ]
        logger.info(f"Fusing LoRA adapter: {' '.join(fuse_cmd)}")
        fuse_proc = subprocess.run(fuse_cmd, capture_output=True, text=True, check=False)
        if fuse_proc.returncode != 0:
            raise RuntimeError(f"MLX-LM fuse failed: {fuse_proc.stderr}")

        # Verify fused MLX checkpoint loads and generates
        mlx_verify = verify_mlx_generation(fused_dir)
        if not mlx_verify["success"]:
            raise RuntimeError(f"Fused MLX model generation check failed: {mlx_verify}")

        # 4. Export fused MLX model back to Ollama manifest/blobs as qwen3.5:4b-safety
        ollama_export = self.converter.export_fused_mlx_to_ollama(
            base_ollama_model=self.config.model.baseline,
            target_ollama_model=self.config.model.mitigated,
            fused_mlx_dir=fused_dir,
            staging_dir=ollama_staging,
        )

        # 5. Live inference verification through Ollama REST API
        ollama_verify = verify_ollama_generation(
            model_identifier=self.config.model.mitigated,
            host=self.config.ollama.host,
        )
        if not ollama_verify["success"]:
            raise RuntimeError(f"Live Ollama verification failed for {self.config.model.mitigated}: {ollama_verify}")

        initial_val = val_losses[0][1] if val_losses else None
        final_val = val_losses[-1][1] if val_losses else None
        final_train = train_losses[-1][1] if train_losses else None

        with self.db.session() as sess:
            sess.add(
                TrainingRun(
                    id=run_name,
                    base_model=self.config.model.baseline,
                    mlx_base_path=str(base_mlx_dir),
                    adapter_path=str(adapter_dir),
                    fused_model_path=str(fused_dir),
                    ollama_target_model=self.config.model.mitigated,
                    method=ft_cfg.method,
                    hyperparameters_json=json.dumps(lora_yaml),
                    train_examples_count=train_count,
                    val_examples_count=val_count,
                    initial_val_loss=initial_val,
                    final_val_loss=final_val,
                    final_train_loss=final_train,
                    duration_seconds=duration,
                    status="completed",
                    conversion_verified=True,
                    log_path=str(log_file),
                )
            )

        summary = {
            "run_id": run_name,
            "status": "completed",
            "duration_seconds": duration,
            "train_examples": train_count,
            "val_examples": val_count,
            "val_loss_history": val_losses,
            "train_loss_history": train_losses,
            "initial_val_loss": initial_val,
            "final_val_loss": final_val,
            "final_train_loss": final_train,
            "base_mlx_export": export_info,
            "adapter_path": str(adapter_dir),
            "fused_dir": str(fused_dir),
            "mlx_verification": mlx_verify,
            "ollama_export": ollama_export,
            "ollama_verification": ollama_verify,
            "log_file": str(log_file),
        }
        (ft_root / "09_Evaluation" / f"{run_name}_training_summary.json").write_text(
            json.dumps(summary, indent=2), encoding="utf-8"
        )
        return summary

"""Training hyperparameters and configuration generator for MLX-LM LoRA."""

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Union
import yaml


@dataclass
class TrainingHyperparameters:
    fine_tune_type: str = "lora"  # 'lora', 'dora', 'full'
    optimizer: str = "adamw"
    mask_prompt: bool = True
    num_layers: int = 16
    batch_size: int = 2
    iters: int = 600
    val_batches: int = 25
    learning_rate: float = 1e-4
    steps_per_report: int = 10
    steps_per_eval: int = 50
    grad_accumulation_steps: int = 2
    save_every: int = 100
    max_seq_length: int = 2048
    grad_checkpoint: bool = True
    seed: int = 42
    lora_rank: int = 8
    lora_alpha: float = 16.0
    lora_dropout: float = 0.05
    lora_scale: float = 2.0

    def to_yaml_dict(self) -> Dict[str, Any]:
        """Converts to dictionary structure expected by mlx_lm.lora YAML configs."""
        return {
            "fine_tune_type": self.fine_tune_type,
            "optimizer": self.optimizer,
            "mask_prompt": self.mask_prompt,
            "num_layers": self.num_layers,
            "batch_size": self.batch_size,
            "iters": self.iters,
            "val_batches": self.val_batches,
            "learning_rate": self.learning_rate,
            "steps_per_report": self.steps_per_report,
            "steps_per_eval": self.steps_per_eval,
            "grad_accumulation_steps": self.grad_accumulation_steps,
            "save_every": self.save_every,
            "max_seq_length": self.max_seq_length,
            "grad_checkpoint": self.grad_checkpoint,
            "seed": self.seed,
            "lora_parameters": {
                "rank": self.lora_rank,
                "alpha": self.lora_alpha,
                "dropout": self.lora_dropout,
                "scale": self.lora_scale,
            },
        }

    def save_yaml(self, path: Union[str, Path]) -> Path:
        """Writes configuration to YAML file."""
        target = Path(path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            yaml.safe_dump(self.to_yaml_dict(), f, sort_keys=False)
        return target

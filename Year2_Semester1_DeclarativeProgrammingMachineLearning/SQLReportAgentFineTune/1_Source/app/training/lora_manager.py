"""LoRA adapter management, checkpoint tracking, and model weight fusion."""

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, Union
from app.core.config import get_project_root
from app.core.logging import get_logger

logger = get_logger(__name__)


class LoRAManager:
    """Manages adapter directories, validates checkpoints, and fuses weights."""

    def __init__(self, adapters_dir: Optional[Union[str, Path]] = None):
        if adapters_dir is None:
            self.adapters_dir = get_project_root() / "6_Models" / "adapters"
        else:
            self.adapters_dir = Path(adapters_dir).resolve()
        self.adapters_dir.mkdir(parents=True, exist_ok=True)

    def get_adapter_path(self, run_name: str) -> Path:
        """Returns the target folder for a specific training run."""
        path = self.adapters_dir / run_name
        path.mkdir(parents=True, exist_ok=True)
        return path

    def is_adapter_valid(self, run_name: str) -> bool:
        """Checks if adapter weights file exists in the run directory."""
        folder = self.adapters_dir / run_name
        if not folder.exists():
            return False
        # MLX-LM saves adapter weights as adapters.safetensors or 0000xxx_adapters.safetensors
        safetensors = list(folder.glob("*.safetensors"))
        return len(safetensors) > 0

    def fuse_model(
        self,
        base_model_path_or_id: str,
        adapter_run_name: str,
        export_dir: Optional[Union[str, Path]] = None,
        export_gguf: bool = False,
    ) -> Path:
        """Fuses trained LoRA adapter back into base model weights."""
        adapter_path = self.get_adapter_path(adapter_run_name)
        if not self.is_adapter_valid(adapter_run_name):
            raise FileNotFoundError(f"No valid adapter weights found in {adapter_path}")

        if export_dir is None:
            export_dir = get_project_root() / "6_Models" / "exported" / f"{adapter_run_name}_fused"
        else:
            export_dir = Path(export_dir).resolve()
        export_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            sys.executable,
            "-m",
            "mlx_lm",
            "fuse",
            "--model",
            str(base_model_path_or_id),
            "--adapter-path",
            str(adapter_path),
            "--save-path",
            str(export_dir),
        ]
        if export_gguf:
            cmd.append("--export-gguf")

        logger.info(f"Running model fusion: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            logger.error(f"Fusion failed: {result.stderr}")
            raise RuntimeError(f"MLX model fusion failed with code {result.returncode}: {result.stderr}")

        logger.info(f"Model successfully fused and saved to: {export_dir}")
        return export_dir

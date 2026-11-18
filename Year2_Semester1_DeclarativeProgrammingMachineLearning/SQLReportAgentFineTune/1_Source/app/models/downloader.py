"""Pretrained model downloader using huggingface_hub."""

from pathlib import Path
from typing import Optional, Union
from huggingface_hub import snapshot_download
from app.core.config import get_project_root
from app.core.logging import get_logger
from app.models.registry import ModelRegistry, ModelSpec

logger = get_logger(__name__)


class ModelDownloader:
    """Handles independent download of base models into 6_Models/base/."""

    def __init__(self, target_dir: Optional[Union[str, Path]] = None):
        if target_dir is None:
            self.target_dir = get_project_root() / "6_Models" / "base"
        else:
            self.target_dir = Path(target_dir).resolve()
        self.target_dir.mkdir(parents=True, exist_ok=True)

    def download(self, model_id_or_repo: str) -> Path:
        """Downloads model repository to local base model directory."""
        spec = ModelRegistry.get_model(model_id_or_repo)
        repo_id = spec.hf_repo if spec else model_id_or_repo

        # Standard clean folder name (e.g. Qwen2.5-Coder-3B-Instruct-4bit)
        folder_name = repo_id.split("/")[-1]
        dest_path = self.target_dir / folder_name

        logger.info(f"Downloading model {repo_id} to {dest_path}...")
        snapshot_download(
            repo_id=repo_id,
            local_dir=str(dest_path),
            local_dir_use_symlinks=False,
        )
        logger.info(f"Model successfully downloaded: {dest_path}")
        return dest_path

    def is_downloaded(self, model_id_or_repo: str) -> bool:
        """Checks if required model files exist locally."""
        spec = ModelRegistry.get_model(model_id_or_repo)
        repo_id = spec.hf_repo if spec else model_id_or_repo
        folder_name = repo_id.split("/")[-1]
        dest_path = self.target_dir / folder_name

        if not dest_path.exists():
            return False

        # Must have config.json and tokenizer files
        required_files = ["config.json"]
        for req in required_files:
            if not (dest_path / req).exists():
                return False
        return True

    def get_local_path(self, model_id_or_repo: str) -> Optional[Path]:
        """Returns local path if downloaded, else None."""
        if self.is_downloaded(model_id_or_repo):
            spec = ModelRegistry.get_model(model_id_or_repo)
            repo_id = spec.hf_repo if spec else model_id_or_repo
            folder_name = repo_id.split("/")[-1]
            return self.target_dir / folder_name
        return None

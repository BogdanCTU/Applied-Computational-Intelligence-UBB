"""Inference engine using Apple MLX-LM with optional LoRA adapter loading."""

from pathlib import Path
from typing import Any, Optional, Tuple, Union
import mlx_lm
from mlx_lm.sample_utils import make_sampler
from app.core.logging import get_logger
from app.inference.prompt_template import PromptBuilder
from app.utils.sql_sanitizer import extract_sql_from_response

logger = get_logger(__name__)


class InferenceEngine:
    """Orchestrates local MLX inference for base or fine-tuned SQL models."""

    def __init__(
        self,
        model_path_or_id: str,
        adapter_path: Optional[Union[str, Path]] = None,
        lazy_load: bool = True,
    ):
        self.model_path_or_id = str(model_path_or_id)
        self.adapter_path = str(adapter_path) if adapter_path else None
        self.prompt_builder = PromptBuilder()
        self.model = None
        self.tokenizer = None

        if not lazy_load:
            self.load()

    def load(self) -> None:
        """Loads model weights and tokenizer into MLX unified memory."""
        if self.model is not None:
            return

        logger.info(f"Loading MLX model: {self.model_path_or_id} (adapter: {self.adapter_path})")
        if self.adapter_path:
            self.model, self.tokenizer = mlx_lm.load(
                self.model_path_or_id,
                adapter_path=self.adapter_path,
            )
        else:
            self.model, self.tokenizer = mlx_lm.load(self.model_path_or_id)
        logger.info("MLX model loaded successfully into unified memory.")

    def generate_sql(
        self,
        schema_text: str,
        question: str,
        max_tokens: int = 512,
        temperature: float = 0.0,
    ) -> Tuple[str, str]:
        """Generates SQL query given schema context and user question.
        
        Returns:
            Tuple of (extracted_clean_sql, raw_llm_response)
        """
        self.load()

        prompt = self.prompt_builder.build_prompt_with_tokenizer(
            self.tokenizer,
            schema_text=schema_text,
            question=question,
        )

        sampler = make_sampler(temp=temperature)

        raw_response = mlx_lm.generate(
            model=self.model,
            tokenizer=self.tokenizer,
            prompt=prompt,
            max_tokens=max_tokens,
            sampler=sampler,
            verbose=False,
        )

        extracted_sql = extract_sql_from_response(raw_response)
        return extracted_sql, raw_response

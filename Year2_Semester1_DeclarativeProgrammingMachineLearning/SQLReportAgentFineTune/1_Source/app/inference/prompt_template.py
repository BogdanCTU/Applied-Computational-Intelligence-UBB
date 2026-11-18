"""Prompt templating for ChatML / Qwen2.5 Text-to-SQL inference."""

from typing import Any, Dict, List, Optional
from app.datasets.preprocessor import DEFAULT_SYSTEM_PROMPT


class PromptBuilder:
    """Builds chat messages and formatted prompts for Text-to-SQL generation."""

    def __init__(self, system_prompt: str = DEFAULT_SYSTEM_PROMPT):
        self.system_prompt = system_prompt

    def build_messages(self, schema_text: str, question: str) -> List[Dict[str, str]]:
        """Constructs standardized role-based message dictionaries."""
        user_content = (
            f"Database Schema:\n{schema_text}\n\n"
            f"User Question:\n{question}\n\n"
            "Generate the SQLite query to answer the question."
        )
        return [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_content},
        ]

    def build_prompt_with_tokenizer(
        self,
        tokenizer: Any,
        schema_text: str,
        question: str,
    ) -> str:
        """Applies tokenizer's native chat template to messages."""
        messages = self.build_messages(schema_text, question)
        if hasattr(tokenizer, "apply_chat_template"):
            return tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
        # Fallback to standard ChatML string
        lines = [
            f"<|im_start|>system\n{self.system_prompt}<|im_end|>",
            f"<|im_start|>user\nDatabase Schema:\n{schema_text}\n\nUser Question:\n{question}\n\nGenerate the SQLite query to answer the question.<|im_end|>",
            "<|im_start|>assistant\n",
        ]
        return "\n".join(lines)

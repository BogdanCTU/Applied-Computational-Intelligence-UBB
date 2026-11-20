"""Prompt templating for ChatML / Qwen2.5 Text-to-SQL inference (Direct and Grounded modes)."""

from typing import Any, Dict, List, Optional
from app.datasets.preprocessor import DEFAULT_SYSTEM_PROMPT

SYSTEM_PROMPT_DIRECT = DEFAULT_SYSTEM_PROMPT

SYSTEM_PROMPT_GROUNDED = (
    "You are a specialized Text-to-SQL AI. Given the SQLite database schema and user question, "
    "first identify the relevant schema elements under <SCHEMA_SELECTION> (TABLES, COLUMNS, and RELATIONSHIPS), "
    "then generate the precise SQLite query enclosed under <SQL>."
)


class PromptBuilder:
    """Builds chat messages and formatted prompts for Text-to-SQL generation."""

    def __init__(self, mode: str = "direct"):
        self.mode = mode
        self.system_prompt = SYSTEM_PROMPT_GROUNDED if mode == "grounded" else SYSTEM_PROMPT_DIRECT

    def build_messages(self, schema_text: str, question: str) -> List[Dict[str, str]]:
        """Constructs standardized role-based message dictionaries."""
        if self.mode == "grounded":
            user_content = (
                f"Database Schema:\n{schema_text}\n\n"
                f"User Question:\n{question}\n\n"
                "First identify the relevant schema elements under <SCHEMA_SELECTION>, then output the SQLite query under <SQL>."
            )
        else:
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
        user_c = messages[1]["content"]
        lines = [
            f"<|im_start|>system\n{self.system_prompt}<|im_end|>",
            f"<|im_start|>user\n{user_c}<|im_end|>",
            "<|im_start|>assistant\n",
        ]
        return "\n".join(lines)

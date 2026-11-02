"""Matching validator module reproducing Agent-OM LLM validation prompt and bypass logic."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple, Union
from langchain_core.language_models import BaseChatModel
from langchain_ollama import ChatOllama

from ..config import config
from ..utils.text_processing import cleaning, uri_to_name


@dataclass
class ValidationRecord:
    """Detailed record of a candidate pair validation attempt."""
    source_uri: str
    target_uri: str
    source_name: str
    target_name: str
    cleaned_source_name: str
    cleaned_target_name: str
    bypassed: bool
    direction: Optional[str] = None
    prompt: Optional[str] = None
    raw_response: Optional[str] = None
    decision: str = "no"  # "yes", "no", or "error"
    duration_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    error_message: Optional[str] = None


class MatchingValidator:
    """
    Validates candidate correspondences using local LLM prompting
    with an exact-name bypass rule.
    
    Reproduces validate() and validation shortcut in om_database_matching.py.
    """

    PROMPT_TEMPLATE = (
        "Question: Is {a} equivalent to {b}?\n"
        "Context: {context}\n"
        "Answer the question within the context.\n"
        "Answer yes or no. Give a short explanation.\n"
    )

    def __init__(
        self,
        llm: Optional[BaseChatModel] = None,
        context: str = config.context,
    ):
        self.llm = llm
        self.context = context

    def _ensure_llm(self) -> BaseChatModel:
        """Instantiate default ChatOllama model if not injected."""
        if self.llm is None:
            self.llm = ChatOllama(
                model=config.default_llm,
                temperature=config.temperature,
                num_ctx=config.num_ctx,
                reasoning=False,
            )
        return self.llm

    @staticmethod
    def extract_yes_no(text: str) -> Optional[str]:
        """
        Extract 'yes' or 'no' word boundary from response.
        Reproduces util.extract_yes_no in original Agent-OM.
        """
        match = re.search(r"\b(?:yes|no)\b", str(text), flags=re.IGNORECASE)
        return match.group().lower() if match else None

    @staticmethod
    def check_name_bypass(name_a: str, name_b: str) -> Tuple[bool, str, str]:
        """
        Checks if cleaned entity names are case-insensitively identical.
        Reproduces lines 304-307 of om_database_matching.py:
        if entity_name_clean.casefold() == predict_entity_name_clean.casefold():
            # bypass validation, accept directly
        """
        clean_a = cleaning(name_a)
        clean_b = cleaning(name_b)
        is_bypass = clean_a.casefold() == clean_b.casefold()
        return is_bypass, clean_a, clean_b

    def validate_candidate_pair(
        self,
        source_uri: str,
        target_uri: str,
        source_name: Optional[str] = None,
        target_name: Optional[str] = None,
        context: Optional[str] = None,
        direction: Optional[str] = None,
    ) -> ValidationRecord:
        """
        Validates whether source_uri and target_uri are equivalent.
        
        1. Checks exact-name bypass rule first.
        2. If bypassed, records decision as 'yes' with zero LLM invocation.
        3. If not bypassed, prompts local Ollama LLM to answer yes/no.
        4. Parses decision and extracts token usage metadata.
        """
        s_name = source_name or uri_to_name(source_uri)
        t_name = target_name or uri_to_name(target_uri)
        ctx = context or self.context

        is_bypass, clean_s, clean_t = self.check_name_bypass(s_name, t_name)

        if is_bypass:
            return ValidationRecord(
                source_uri=source_uri,
                target_uri=target_uri,
                source_name=s_name,
                target_name=t_name,
                cleaned_source_name=clean_s,
                cleaned_target_name=clean_t,
                bypassed=True,
                direction=direction,
                prompt=None,
                raw_response="BYPASSED: Identical cleaned names",
                decision="yes",
                duration_ms=0.0,
            )

        prompt_text = self.PROMPT_TEMPLATE.format(a=clean_s, b=clean_t, context=ctx)
        llm = self._ensure_llm()

        t0 = time.perf_counter()
        try:
            response = llm.invoke(prompt_text)
            duration_ms = (time.perf_counter() - t0) * 1000.0
            raw_text = str(response.content).strip()
            parsed = self.extract_yes_no(raw_text)
            decision = parsed if parsed in ("yes", "no") else "no"

            # Extract token metadata if available from Ollama
            meta = getattr(response, "response_metadata", {})
            prompt_tokens = meta.get("prompt_eval_count", 0)
            completion_tokens = meta.get("eval_count", 0)
            total_tokens = prompt_tokens + completion_tokens

            return ValidationRecord(
                source_uri=source_uri,
                target_uri=target_uri,
                source_name=s_name,
                target_name=t_name,
                cleaned_source_name=clean_s,
                cleaned_target_name=clean_t,
                bypassed=False,
                direction=direction,
                prompt=prompt_text,
                raw_response=raw_text,
                decision=decision,
                duration_ms=duration_ms,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            )
        except Exception as e:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            return ValidationRecord(
                source_uri=source_uri,
                target_uri=target_uri,
                source_name=s_name,
                target_name=t_name,
                cleaned_source_name=clean_s,
                cleaned_target_name=clean_t,
                bypassed=False,
                direction=direction,
                prompt=prompt_text,
                raw_response=None,
                decision="error",
                duration_ms=duration_ms,
                error_message=str(e),
            )

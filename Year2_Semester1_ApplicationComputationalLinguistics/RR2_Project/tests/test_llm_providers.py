"""Unit and integration tests for Phase 3 Local <=4B LLM and Embedding Provider Architecture."""

from __future__ import annotations

from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

from src.config import STRICT_4B_PROFILES, VALID_PROFILES, AppConfig
from src.llm import (
    STRICT_4B_MAX_PARAMETERS,
    EmbeddingDimensionMismatchError,
    LocalChatProvider,
    LocalEmbeddingProvider,
    ModelNotAvailableError,
    ModelRegistry,
    ModelValidationError,
    ModelValidator,
    OllamaClient,
    OllamaClientError,
    ParameterLimitExceededError,
)


def _build_mock_ollama_client() -> OllamaClient:
    """Create a mocked OllamaClient returning realistic /api/tags, /api/show, /api/chat, and /api/embed payloads."""
    client = MagicMock(spec=OllamaClient)
    client.base_url = "http://127.0.0.1:11434"

    tags_payload = [
        {
            "name": "qwen2.5:3b",
            "digest": "sha256:qwen25_3b_digest",
            "size": 1929900000,
            "details": {
                "family": "qwen2",
                "format": "gguf",
                "parameter_size": "3.1B",
                "quantization_level": "Q4_K_M",
                "runner": "ggml",
            },
        },
        {
            "name": "deepseek-r1:1.5b",
            "digest": "sha256:deepseek_r1_15b_digest",
            "size": 1117320000,
            "details": {
                "family": "qwen2",
                "format": "gguf",
                "parameter_size": "1.8B",
                "quantization_level": "Q4_K_M",
                "runner": "ggml",
            },
        },
        {
            "name": "qwen3.5:4b",
            "digest": "7f3251fa6878a78a606bcb3c074283306e5ad2ea411a7774a9dd98a4bc7f2d13",
            "size": 3973305013,
            "details": {
                "family": "qwen3_5",
                "format": "safetensors",
                "parameter_size": "4.5B",
                "quantization_level": "nvfp4",
                "runner": "mlx",
            },
        },
        {
            "name": "llama3:8b",
            "digest": "365c0bd3c000a25d28ddbf732fe1c6add414de7275464c4e4d1c3b5fcb5d8ad1",
            "size": 4661224676,
            "details": {
                "family": "llama",
                "format": "gguf",
                "parameter_size": "8.0B",
                "quantization_level": "Q4_0",
                "runner": "ggml",
            },
        },
        {
            "name": "nomic-embed-text:latest",
            "digest": "sha256:nomic_digest",
            "size": 274302450,
            "details": {
                "family": "nomic-bert",
                "format": "gguf",
                "parameter_size": "137M",
                "quantization_level": "F16",
                "runner": "ggml",
            },
        },
        {
            "name": "mxbai-embed-large:latest",
            "digest": "sha256:mxbai_digest",
            "size": 669615493,
            "details": {
                "family": "bert",
                "format": "gguf",
                "parameter_size": "334M",
                "quantization_level": "F16",
                "runner": "ggml",
            },
        },
    ]
    client.list_tags.return_value = tags_payload

    show_map: Dict[str, Dict[str, Any]] = {
        "qwen2.5:3b": {
            "details": tags_payload[0]["details"],
            "capabilities": ["completion", "tools"],
            "model_info": {
                "general.architecture": "qwen2",
                "general.parameter_count": 3085938688,
                "qwen2.context_length": 32768,
                "qwen2.embedding_length": 2048,
            },
        },
        "deepseek-r1:1.5b": {
            "details": tags_payload[1]["details"],
            "capabilities": ["completion", "thinking"],
            "model_info": {
                "general.architecture": "qwen2",
                "general.parameter_count": 1777088000,
                "qwen2.context_length": 131072,
                "qwen2.embedding_length": 1536,
            },
        },
        "qwen3.5:4b": {
            "details": tags_payload[2]["details"],
            "capabilities": ["completion", "vision", "thinking", "tools"],
            "model_info": {
                "general.architecture": "qwen3_5",
                "general.parameter_count": 4538986496,
                "qwen3_5.context_length": 262144,
                "qwen3_5.embedding_length": 2560,
            },
        },
        "llama3:8b": {
            "details": tags_payload[3]["details"],
            "capabilities": ["completion"],
            "model_info": {
                "general.architecture": "llama",
                "general.parameter_count": 8030261248,
                "llama.context_length": 8192,
                "llama.embedding_length": 4096,
            },
        },
        "nomic-embed-text": {
            "details": tags_payload[4]["details"],
            "capabilities": ["embedding"],
            "model_info": {
                "general.architecture": "nomic-bert",
                "general.parameter_count": 136726528,
                "nomic-bert.context_length": 2048,
                "nomic-bert.embedding_length": 768,
            },
        },
        "nomic-embed-text:latest": {
            "details": tags_payload[4]["details"],
            "capabilities": ["embedding"],
            "model_info": {
                "general.architecture": "nomic-bert",
                "general.parameter_count": 136726528,
                "nomic-bert.context_length": 2048,
                "nomic-bert.embedding_length": 768,
            },
        },
        "mxbai-embed-large": {
            "details": tags_payload[5]["details"],
            "capabilities": ["embedding"],
            "model_info": {
                "general.architecture": "bert",
                "general.parameter_count": 334092288,
                "bert.context_length": 512,
                "bert.embedding_length": 1024,
            },
        },
        "mxbai-embed-large:latest": {
            "details": tags_payload[5]["details"],
            "capabilities": ["embedding"],
            "model_info": {
                "general.architecture": "bert",
                "general.parameter_count": 334092288,
                "bert.context_length": 512,
                "bert.embedding_length": 1024,
            },
        },
    }

    def _show_side_effect(model_name: str) -> Dict[str, Any]:
        if model_name not in show_map:
            raise OllamaClientError(f"Ollama HTTP 404 on POST /api/show: model '{model_name}' not found")
        return show_map[model_name]

    def _embed_side_effect(model_name: str, inputs: List[str] | str, timeout_s: Any = None) -> Dict[str, Any]:
        texts = [inputs] if isinstance(inputs, str) else list(inputs)
        if "nomic" in model_name:
            dim = 768
        elif "mxbai" in model_name:
            dim = 1024
        else:
            raise OllamaClientError("This model does not support embeddings")
        return {"model": model_name, "embeddings": [[0.1] * dim for _ in texts]}

    def _chat_side_effect(
        model_name: str, messages: List[Dict[str, str]], options: Any = None, think: Any = None, timeout_s: Any = None
    ) -> Dict[str, Any]:
        return {
            "model": model_name,
            "message": {"role": "assistant", "content": "yes"},
            "prompt_eval_count": 42,
            "eval_count": 1,
            "load_duration": 1000000,
            "total_duration": 15000000,
        }

    client.show_model.side_effect = _show_side_effect
    client.embed.side_effect = _embed_side_effect
    client.chat.side_effect = _chat_side_effect
    return client


class TestPhase3ModelRegistryAndValidator:
    """Verify runtime /api/show parameter enforcement, tag-trap protection, and embedding validation."""

    def test_strict_4b_parameter_limit_rejects_qwen35_4b_and_llama3_8b(self) -> None:
        client = _build_mock_ollama_client()
        reg = ModelRegistry(client)
        val = ModelValidator(reg)

        # qwen2.5:3b (3.085B) and deepseek-r1:1.5b (1.777B) MUST pass strict <=4.0B check
        m_qwen25 = val.validate_chat_model("qwen2.5:3b", enforce_4b_limit=True)
        assert m_qwen25.is_strict_4b_compliant is True
        assert m_qwen25.total_parameter_count == 3_085_938_688
        assert m_qwen25.total_parameter_count <= STRICT_4B_MAX_PARAMETERS

        m_ds = val.validate_chat_model("deepseek-r1:1.5b", enforce_4b_limit=True)
        assert m_ds.is_strict_4b_compliant is True
        assert m_ds.total_parameter_count == 1_777_088_000

        # qwen3.5:4b has 4,538,986,496 parameters (4.54B) despite its ':4b' tag -> MUST raise ParameterLimitExceededError!
        with pytest.raises(ParameterLimitExceededError, match="4,538,986,496"):
            val.validate_chat_model("qwen3.5:4b", enforce_4b_limit=True)

        # Without enforce_4b_limit, qwen3.5:4b is allowed as an out-of-limit reference model
        m_qwen35 = val.validate_chat_model("qwen3.5:4b", enforce_4b_limit=False)
        assert m_qwen35.is_strict_4b_compliant is False
        assert m_qwen35.total_parameter_count == 4_538_986_496

        # llama3:8b (8.03B) must also fail strict <=4B check
        with pytest.raises(ParameterLimitExceededError, match="8,030,261,248"):
            val.validate_chat_model("llama3:8b", enforce_4b_limit=True)

    def test_missing_model_and_cloud_model_prohibition(self) -> None:
        client = _build_mock_ollama_client()
        val = ModelValidator(ModelRegistry(client))

        with pytest.raises(PermissionError, match="Cloud model"):
            val.validate_chat_model("gpt-4o-2024-05-13")

        with pytest.raises(PermissionError, match="Cloud model"):
            val.validate_embedding_model("text-embedding-ada-002", expected_dimension=1536)

        with pytest.raises(ModelNotAvailableError, match="unavailable in local Ollama"):
            val.validate_chat_model("non-existent-local-model:3b")

    def test_chat_and_embedding_provider_role_separation(self) -> None:
        client = _build_mock_ollama_client()
        val = ModelValidator(ModelRegistry(client))

        # Cannot use a dedicated embedding model as a chat generator
        with pytest.raises(ModelValidationError, match="dedicated embedding model"):
            val.validate_chat_model("nomic-embed-text")

        # Cannot assume a causal chat model (qwen2.5:3b) is a suitable embedding model
        with pytest.raises(ModelValidationError, match="Never assume a chat model is a suitable embedding model"):
            val.validate_embedding_model("qwen2.5:3b", expected_dimension=2048)

    def test_embedding_dimension_verification_and_mismatch_rejection(self) -> None:
        client = _build_mock_ollama_client()
        reg = ModelRegistry(client)
        val = ModelValidator(reg)

        m_nomic = val.validate_embedding_model("nomic-embed-text", expected_dimension=768)
        assert m_nomic.embedding_length == 768

        m_mxbai = val.validate_embedding_model("mxbai-embed-large", expected_dimension=1024)
        assert m_mxbai.embedding_length == 1024

        with pytest.raises(EmbeddingDimensionMismatchError, match="768"):
            val.validate_embedding_model("nomic-embed-text", expected_dimension=1024)

    def test_local_chat_and_embedding_providers_telemetry(self) -> None:
        client = _build_mock_ollama_client()
        chat_prov = LocalChatProvider(
            model_name="qwen2.5:3b",
            enforce_4b_limit=True,
            client=client,
            validate_on_init=True,
        )
        out = chat_prov.generate("Is Author equivalent to Writer?")
        assert out["content"] == "yes"
        telem = chat_prov.get_telemetry_summary()
        assert telem["total_requests"] == 1
        assert telem["total_prompt_tokens"] == 42
        assert telem["total_completion_tokens"] == 1

        emb_prov = LocalEmbeddingProvider(
            model_name="nomic-embed-text",
            expected_dim=768,
            client=client,
            validate_on_init=True,
        )
        vecs = emb_prov.embed_documents(["conference paper", "review committee"])
        assert len(vecs) == 2
        assert len(vecs[0]) == 768
        emb_telem = emb_prov.get_telemetry_summary()
        assert emb_telem["total_requests"] == 1
        assert emb_telem["total_texts_embedded"] == 2

    def test_new_4b_profiles_in_app_config(self) -> None:
        for prof in ("local_4b_baseline", "local_4b_optimized", "local_4b_reasoning"):
            assert prof in VALID_PROFILES
            assert prof in STRICT_4B_PROFILES
            cfg = AppConfig.from_profile(prof)
            assert cfg.enforce_4b_limit is True
            assert cfg.max_parameters == 4_000_000_000
            assert cfg.vector_length == 768

        # Ensure upstream_lite_parity was NOT altered
        parity = AppConfig.from_profile("upstream_lite_parity")
        assert parity.default_llm == "llama3:8b"
        assert parity.default_embedding_model == "llama3:8b"
        assert parity.vector_length == 4096
        assert parity.enforce_4b_limit is False


class TestPhase3LiveLocalOllamaIntegration:
    """Genuine live integration tests against local loopback Ollama (127.0.0.1:11434) and PostgreSQL (127.0.0.1:5432)."""

    def test_live_ollama_discovery_and_strict_4b_enforcement(self) -> None:
        client = OllamaClient()
        assert client.is_reachable() is True
        reg = ModelRegistry(client)
        val = ModelValidator(reg)

        # Verify live qwen2.5:3b passes strict <=4.0B check (3,085,938,688 params)
        m_qwen = val.validate_chat_model("qwen2.5:3b", enforce_4b_limit=True)
        assert m_qwen.total_parameter_count == 3_085_938_688
        assert m_qwen.is_strict_4b_compliant is True

        # Verify live deepseek-r1:1.5b passes strict <=4.0B check (1,777,088,000 params)
        m_ds = val.validate_chat_model("deepseek-r1:1.5b", enforce_4b_limit=True)
        assert m_ds.total_parameter_count == 1_777_088_000
        assert m_ds.is_strict_4b_compliant is True

        # Verify live qwen3.5:4b (4,538,986,496 params) is REJECTED by strict <=4.0B validator
        with pytest.raises(ParameterLimitExceededError, match="4,538,986,496"):
            val.validate_chat_model("qwen3.5:4b", enforce_4b_limit=True)

        # Verify live dedicated embedding models and vector dimensions
        m_nomic = val.validate_embedding_model("nomic-embed-text", expected_dimension=768, verify_live_vector=True)
        assert m_nomic.embedding_length == 768

        m_mxbai = val.validate_embedding_model("mxbai-embed-large", expected_dimension=1024, verify_live_vector=True)
        assert m_mxbai.embedding_length == 1024


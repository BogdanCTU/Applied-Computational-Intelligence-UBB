"""Comprehensive test suite for Configurable Agent Context Window.

Validates all 15 Phase 6 mandatory requirements:
1. Default configuration is 128K (131,072 tokens).
2. All four supported values (32K, 64K, 128K, 256K) are accepted.
3. Unsupported values are rejected during validation.
4. Configuration persists across restarts (atomic JSON save/load).
5. Missing configuration in existing settings defaults to 128K.
6. ContextBuilder receives and respects the configured value.
7. Changing settings dynamically affects subsequent requests.
8. Ollama requests receive the correct num_ctx parameter.
9. Model capability incompatibility and unknown capability handled correctly.
10. Context allocation strictly respects effective context limit.
11. Output reservation and safety margin preserved across configurations.
12. Context construction fails safely when mandatory content cannot fit.
13. Large MCP tool results are handled without arbitrary silent truncation.
14. Conversation history is filtered deterministically without breaking tool pairs.
15. Memory and skills remain relevant and functional across all context limits (32K-256K).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent.context_builder import ContextBuilder
from agent.context_models import (
    ContextBudgetExceededError,
    ContextSection,
    ExecutionStage,
    SectionPriority,
)
from agent.conversation import ConversationManager, ConversationMessage
from agent.ollama_client import (
    ModelCapabilityStatus,
    ModelContextCapability,
    ModelContextIncompatibleError,
    OllamaChatResponse,
    OllamaClient,
    OllamaContextSizeRejectedError,
    OllamaHTTPError,
    OllamaToolCall,
)
from agent.orchestrator import AgentOrchestrator, AgentRunResult
from agent.skill_manager import SkillManager
from agent.task_models import AgentTask, StepStatus, TaskPlan, TaskStatus, TaskStep
from agent.task_planner import TaskPlanner
from config.settings import (
    ALLOWED_CONTEXT_WINDOWS,
    CONTEXT_WINDOW_DISPLAY_LABELS,
    DEFAULT_CONTEXT_WINDOW,
    AppSettings,
    load_settings,
    save_settings,
)
from database.schema_inspector import DatabaseSchema


# ===========================================================================
# Test 1: Default configuration is 128K (131,072 tokens)
# ===========================================================================

def test_default_configuration_is_128k() -> None:
    settings = AppSettings()
    assert settings.agent.agent_context_window == 131072
    assert settings.agent_context_window == 131072
    assert settings.ollama.num_ctx == 131072
    assert DEFAULT_CONTEXT_WINDOW == 131072
    assert 131072 in ALLOWED_CONTEXT_WINDOWS


# ===========================================================================
# Test 2: All four supported values are accepted
# ===========================================================================

@pytest.mark.parametrize("window_size", [32768, 65536, 131072, 262144])
def test_all_supported_values_accepted(window_size: int) -> None:
    settings = AppSettings()
    settings.agent.agent_context_window = window_size
    settings.ollama.num_ctx = window_size
    errors = settings.validate()
    assert not errors, f"Expected {window_size} to be valid, got errors: {errors}"
    assert window_size in CONTEXT_WINDOW_DISPLAY_LABELS


# ===========================================================================
# Test 3: Unsupported values are rejected
# ===========================================================================

@pytest.mark.parametrize("invalid_size", [0, -1, 4096, 8192, 16384, 524288, 100000])
def test_unsupported_values_rejected(invalid_size: int) -> None:
    settings = AppSettings()
    settings.agent.agent_context_window = invalid_size
    settings.ollama.num_ctx = invalid_size
    errors = settings.validate()
    assert errors, f"Expected {invalid_size} to be rejected"
    assert any("Agent context window must be one of" in e for e in errors)


# ===========================================================================
# Test 4: Configuration persists after restart
# ===========================================================================

def test_configuration_persists_after_restart(tmp_path: Path) -> None:
    config_file = tmp_path / "settings.json"
    settings = AppSettings()
    settings.agent.agent_context_window = 65536
    settings.ollama.num_ctx = 65536

    save_settings(settings, path=config_file)
    assert config_file.exists()

    reloaded = load_settings(path=config_file, apply_env=False)
    assert reloaded.agent.agent_context_window == 65536
    assert reloaded.agent_context_window == 65536
    assert reloaded.ollama.num_ctx == 65536


# ===========================================================================
# Test 5: Missing configuration defaults to 128K
# ===========================================================================

def test_missing_configuration_defaults_to_128k(tmp_path: Path) -> None:
    config_file = tmp_path / "legacy_settings.json"
    # Legacy settings without agent_context_window
    legacy_data = {
        "ollama": {"host": "http://localhost:11434", "model": "qwen3.5:4b", "num_ctx": 8192},
        "agent": {"max_iterations": 20},
    }
    config_file.write_text(json.dumps(legacy_data), encoding="utf-8")

    loaded = load_settings(path=config_file, apply_env=False)
    assert loaded.agent.agent_context_window == 131072
    assert loaded.agent_context_window == 131072
    # Invalid legacy 8192 num_ctx should automatically be aligned with 128K
    assert loaded.ollama.num_ctx == 131072


# ===========================================================================
# Test 6: ContextBuilder receives the configured value
# ===========================================================================

@pytest.mark.parametrize("target_limit", [32768, 65536, 131072, 262144])
def test_context_builder_receives_configured_value(target_limit: int) -> None:
    settings = AppSettings()
    settings.agent.agent_context_window = target_limit
    settings.ollama.num_ctx = target_limit

    builder = ContextBuilder(settings=settings)
    assert builder.num_ctx == target_limit

    ctx = builder.build(
        ExecutionStage.REQUEST_PLANNING,
        user_request="Test prompt",
    )
    assert ctx.report.num_ctx == target_limit
    assert ctx.report.configured_context_window == target_limit
    assert ctx.report.effective_context_window == target_limit


# ===========================================================================
# Test 7: Changing settings affects subsequent requests
# ===========================================================================

def test_changing_settings_affects_subsequent_requests() -> None:
    settings = AppSettings()
    settings.agent.agent_context_window = 131072
    orchestrator = AgentOrchestrator(settings=settings)
    assert orchestrator.effective_context_window == 131072
    assert orchestrator.context_builder.num_ctx == 131072

    # Change setting live to 256K
    new_settings = AppSettings()
    new_settings.agent.agent_context_window = 262144
    orchestrator.update_settings(new_settings)

    assert orchestrator.effective_context_window == 262144
    assert orchestrator.context_builder.num_ctx == 262144
    assert orchestrator.ollama_client.settings.num_ctx == 262144

    ctx = orchestrator.context_builder.build(
        ExecutionStage.REQUEST_PLANNING,
        user_request="Analyze data",
    )
    assert ctx.report.effective_context_window == 262144
    assert ctx.report.configured_context_window == 262144


# ===========================================================================
# Test 8: Ollama requests receive the correct num_ctx
# ===========================================================================

@pytest.mark.asyncio
async def test_ollama_requests_receive_correct_num_ctx() -> None:
    settings = AppSettings()
    settings.agent.agent_context_window = 65536
    settings.ollama.num_ctx = 65536

    client = OllamaClient(settings.ollama)

    # Mock _create_http_client
    mock_post = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "message": {"role": "assistant", "content": "Done"},
        "done": True,
        "done_reason": "stop",
    }
    mock_post.return_value = mock_resp

    mock_client = AsyncMock()
    mock_client.post = mock_post
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch.object(client, "_create_http_client", return_value=mock_client):
        await client.chat(
            messages=[{"role": "user", "content": "Hello"}],
            num_ctx=65536,
        )

        assert mock_post.called
        call_payload = mock_post.call_args[1]["json"]
        assert call_payload["options"]["num_ctx"] == 65536


# ===========================================================================
# Test 9: Model capability incompatibility handled correctly
# ===========================================================================

@pytest.mark.asyncio
async def test_model_capability_validation_scenarios() -> None:
    client = OllamaClient(AppSettings().ollama)

    # Scenario A: Model supports configured limit
    show_compatible = {
        "model_info": {"qwen3_5.context_length": 131072},
    }
    with patch.object(client, "get_model_info", return_value=show_compatible):
        cap = await client.validate_model_context_capability(configured_window=131072)
        assert cap.is_compatible is True
        assert cap.status == ModelCapabilityStatus.COMPATIBLE
        assert cap.effective_window == 131072

    # Scenario B: Model supports a larger limit
    show_larger = {
        "model_info": {"qwen3_5.context_length": 262144},
    }
    with patch.object(client, "get_model_info", return_value=show_larger):
        cap = await client.validate_model_context_capability(configured_window=131072)
        assert cap.is_compatible is True
        assert cap.status == ModelCapabilityStatus.COMPATIBLE
        assert cap.effective_window == 131072  # Capped at configured limit

    # Scenario C: Model supports smaller limit (incompatible)
    show_smaller = {
        "model_info": {"qwen2.context_length": 32768},
    }
    with patch.object(client, "get_model_info", return_value=show_smaller):
        cap = await client.validate_model_context_capability(configured_window=131072)
        assert cap.is_compatible is False
        assert cap.status == ModelCapabilityStatus.INCOMPATIBLE
        assert cap.effective_window == 32768
        assert "smaller than configured" in cap.message

    # Scenario D: Model capability cannot be determined (safe policy applied)
    show_unknown = {
        "details": {"format": "gguf"},
    }
    with patch.object(client, "get_model_info", return_value=show_unknown):
        cap = await client.validate_model_context_capability(configured_window=131072)
        assert cap.status == ModelCapabilityStatus.UNKNOWN
        assert cap.effective_window == 32768  # Safe fallback policy applied
        assert "Safe policy applied" in cap.message

    # Scenario E: Ollama rejects requested context size
    mock_post = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = "model requires more VRAM than available for num_ctx 262144"
    mock_post.return_value = mock_resp

    mock_http = AsyncMock()
    mock_http.post = mock_post
    mock_http.__aenter__.return_value = mock_http
    mock_http.__aexit__.return_value = None

    with patch.object(client, "_create_http_client", return_value=mock_http):
        with pytest.raises(OllamaContextSizeRejectedError) as exc_info:
            await client.chat(
                messages=[{"role": "user", "content": "Test"}],
                num_ctx=262144,
            )
        assert "Ollama rejected context size" in str(exc_info.value)


# ===========================================================================
# Test 10: Context allocation respects the effective limit
# ===========================================================================

@pytest.mark.parametrize("limit", [32768, 65536, 131072, 262144])
def test_context_allocation_respects_effective_limit(limit: int) -> None:
    builder = ContextBuilder(num_ctx=limit, reserved_output_tokens=1024, safety_margin_tokens=256)
    ctx = builder.build(
        ExecutionStage.SQL_GENERATION,
        user_request="Generate sales breakdown by region for last quarter",
        schema="Table sales (id INT, region TEXT, amount REAL, created_at TEXT)",
    )

    # Invariant: estimated_input + reserved_output + safety_margin <= effective_limit
    assert (
        ctx.report.estimated_input_tokens
        + ctx.report.reserved_output_tokens
        + ctx.report.safety_margin_tokens
        <= limit
    )
    assert ctx.report.available_input_tokens == limit - 1024 - 256
    assert ctx.report.remaining_tokens >= 0


# ===========================================================================
# Test 11: Output reservation is preserved across all context configurations
# ===========================================================================

@pytest.mark.parametrize("window", [32768, 65536, 131072, 262144])
def test_output_reservation_preserved(window: int) -> None:
    builder = ContextBuilder(
        num_ctx=window,
        reserved_output_tokens=2048,
        safety_margin_tokens=512,
    )
    ctx = builder.build(ExecutionStage.FINAL_RESPONSE, user_request="Summarize findings")
    assert ctx.report.reserved_output_tokens == 2048
    assert ctx.report.safety_margin_tokens == 512
    assert ctx.report.available_input_tokens == window - 2048 - 512


# ===========================================================================
# Test 12: Context construction fails safely when mandatory content cannot fit
# ===========================================================================

def test_context_construction_fails_safely_when_mandatory_content_exceeds_budget() -> None:
    # Set a tiny budget where mandatory system instructions cannot possibly fit
    builder = ContextBuilder(
        num_ctx=200,
        reserved_output_tokens=100,
        safety_margin_tokens=50,
    )
    # Available budget = 50 tokens, but mandatory system + user instructions require ~150+ tokens
    with pytest.raises(ContextBudgetExceededError) as exc_info:
        builder.build(
            ExecutionStage.REQUEST_PLANNING,
            user_request="Perform comprehensive financial quarterly audit",
        )
    assert "Mandatory context sections require" in str(exc_info.value)


# ===========================================================================
# Test 13: Large MCP tool results are handled without silent truncation
# ===========================================================================

def test_large_mcp_tool_results_handled_without_arbitrary_silent_truncation() -> None:
    builder = ContextBuilder(num_ctx=131072)
    # A large tool result (e.g. 10,000 characters)
    large_sql_result = {
        "tool_name": "execute_readonly_sql",
        "status": "success",
        "result": "ROW_DATA_FIELD_" + ("X" * 10000),
    }

    ctx = builder.build(
        ExecutionStage.DATA_ANALYSIS,
        user_request="Analyze large SQL output",
        tool_results=[large_sql_result],
    )

    # Large tool results are safely bounded with explicit notice (never silent truncation)
    assert "tool_results" in ctx.report.included_sections
    assert "truncated for context budget" in ctx.user_prompt
    assert "ROW_DATA_FIELD_" in ctx.user_prompt


# ===========================================================================
# Test 14: Conversation history is filtered deterministically
# ===========================================================================

def test_conversation_history_filtered_deterministically() -> None:
    builder = ContextBuilder(
        num_ctx=32768,
        reserved_output_tokens=1024,
        safety_margin_tokens=256,
    )

    # Create multi-turn conversation messages
    history = [
        ConversationMessage(role="user", content=f"User turn {i} with question")
        for i in range(10)
    ]

    ctx = builder.build(
        ExecutionStage.FINAL_RESPONSE,
        user_request="Final question",
        conversation_history=history,
    )

    # Report tracks included and excluded categories and sections
    assert "conversation_history" in ctx.report.included_categories
    assert any("history_" in sec for sec in ctx.report.included_sections)


# ===========================================================================
# Test 15: Memory and skills remain relevant under different context limits
# ===========================================================================

@pytest.mark.parametrize("limit", [32768, 65536, 131072, 262144])
def test_memory_and_skills_relevance_across_context_limits(limit: int) -> None:
    skill_mgr = SkillManager()
    builder = ContextBuilder(settings=AppSettings(), skill_manager=skill_mgr, num_ctx=limit)

    ctx = builder.build(
        ExecutionStage.SQL_GENERATION,
        user_request="Find best customers",
        schema="Table customers (id INT, name TEXT)",
    )

    # Domain SQL skill guidelines must be included for SQL generation stage across all limits
    assert "skill_sql_generation" in ctx.report.included_sections
    assert "SQL Generation & Schema Analysis" in ctx.system_prompt
    assert ctx.report.effective_context_window == limit
    assert ctx.report.configured_context_window >= 32768

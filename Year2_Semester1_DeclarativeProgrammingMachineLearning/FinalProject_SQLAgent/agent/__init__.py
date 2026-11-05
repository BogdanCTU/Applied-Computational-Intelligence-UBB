"""Agent orchestration package for the Local Report SQL Agent."""

from .events import ActivityCategory, ActivityEvent, mask_sensitive_data
from .conversation import ConversationManager, ConversationMessage
from .ollama_client import (
    OllamaChatResponse,
    OllamaClient,
    OllamaClientError,
    OllamaConnectionError,
    OllamaModelNotFoundError,
    OllamaResponseError,
    OllamaTimeoutError,
    OllamaToolCall,
)
from .orchestrator import (
    AgentEvent,
    AgentEventType,
    AgentOrchestrator,
    AgentRunResult,
    ApprovalCallbackType,
    ProgressCallbackType,
    detect_requested_report_format,
)
from .system_prompt import build_system_prompt
from .tool_handler import PERMITTED_TOOLS, ToolHandler, ToolHandlerError

__all__ = [
    "ActivityCategory",
    "ActivityEvent",
    "AgentEvent",
    "AgentEventType",
    "AgentOrchestrator",
    "AgentRunResult",
    "ApprovalCallbackType",
    "ConversationManager",
    "ConversationMessage",
    "OllamaChatResponse",
    "OllamaClient",
    "OllamaClientError",
    "OllamaConnectionError",
    "OllamaModelNotFoundError",
    "OllamaResponseError",
    "OllamaTimeoutError",
    "OllamaToolCall",
    "PERMITTED_TOOLS",
    "ProgressCallbackType",
    "ToolHandler",
    "ToolHandlerError",
    "build_system_prompt",
    "detect_requested_report_format",
]

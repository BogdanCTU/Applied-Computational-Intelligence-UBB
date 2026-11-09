"""Background Qt worker threads for executing agent workflows and checking Ollama status."""

from __future__ import annotations

import asyncio
import logging
import queue
from typing import Any

from PySide6.QtCore import QThread

from agent import AgentEvent, AgentEventType, AgentOrchestrator, OllamaClient
from config.settings import AppSettings

from .worker_signals import OllamaCheckSignals, WorkerSignals

log = logging.getLogger(__name__)


class AgentWorker(QThread):
    """Executes multi-turn agent reporting requests on a dedicated worker thread.

    Maintains a dedicated asyncio event loop on this thread to drive
    Ollama HTTP communication and stdio MCP subprocess tools without freezing the UI.
    """

    def __init__(
        self,
        orchestrator: AgentOrchestrator,
        user_message: str,
        *,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self.orchestrator = orchestrator
        self.user_message = user_message
        self.signals = WorkerSignals()
        self._cancel_event = asyncio.Event()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._is_cancelled = False

    def cancel(self) -> None:
        """Signal cooperative cancellation to the running agent."""
        self._is_cancelled = True
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._cancel_event.set)
        else:
            self._cancel_event.set()

    def run(self) -> None:
        """Thread entrypoint establishing the event loop."""
        import sys

        if sys.platform == "win32":
            try:
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            except Exception as e:  # noqa: BLE001
                log.warning("Could not set WindowsProactorEventLoopPolicy: %s", e)

        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self.signals.started.emit()

        try:
            self._loop.run_until_complete(self._execute())
        except Exception as exc:  # noqa: BLE001
            log.exception("Unhandled error inside AgentWorker thread")
            self.signals.error.emit(f"Internal worker error: {exc}")
        finally:
            try:
                # Cancel any lingering pending tasks on this worker's loop
                pending = asyncio.all_tasks(self._loop)
                for t in pending:
                    t.cancel()
                if pending:
                    self._loop.run_until_complete(
                        asyncio.gather(*pending, return_exceptions=True)
                    )
            except Exception:  # noqa: BLE001
                pass
            finally:
                self._loop.close()
                self._loop = None

    async def _execute(self) -> None:
        """Run process_message and propagate events."""

        def _approval_callback(sql_query: str, explanation: str) -> bool:
            """Cross-thread synchronous bridge requesting user approval from GUI thread."""
            if self._is_cancelled or self._cancel_event.is_set():
                log.info("Approval requested after cancellation; rejecting by default.")
                return False

            res_queue: queue.Queue[bool] = queue.Queue(maxsize=1)
            self.signals.approval_requested.emit(sql_query, explanation, res_queue)

            # Block worker thread until GUI user makes a choice
            try:
                approved = res_queue.get()
                return bool(approved)
            except Exception as e:  # noqa: BLE001
                log.warning("Exception waiting for approval queue: %s", e)
                return False

        def _progress_callback(event: AgentEvent) -> None:
            """Propagate fine-grained progress updates to Qt signals."""
            self.signals.progress_event.emit(event)

            # Propagate structured activity event if attached
            act = getattr(event, "activity_event", None) or event.data.get("activity_event")
            if act is not None:
                self.signals.activity_event.emit(act)

            if event.event_type == AgentEventType.THINKING:
                thinking_text = event.data.get("thinking", "")
                if thinking_text:
                    self.signals.thinking_update.emit(thinking_text)

            elif event.event_type == AgentEventType.SQL_PROPOSED:
                self.signals.sql_proposed.emit(
                    event.data.get("sql_query", ""),
                    event.data.get("explanation", ""),
                )

            elif event.event_type == AgentEventType.REPORT_GENERATED:
                self.signals.report_generated.emit(event.data)

        try:
            result = await self.orchestrator.process_message(
                self.user_message,
                approval_callback=_approval_callback,
                progress_callback=_progress_callback,
                cancel_event=self._cancel_event,
            )

            if result.status == "cancelled":
                self.signals.cancelled.emit()
            self.signals.finished.emit(result)

        except Exception as exc:  # noqa: BLE001
            log.exception("Error executing agent orchestrator: %s", exc)
            self.signals.error.emit(str(exc))


class OllamaCheckWorker(QThread):
    """Background thread to query Ollama connectivity and installed models."""

    def __init__(
        self,
        settings: AppSettings,
        *,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self.settings = settings
        self.signals = OllamaCheckSignals()

    def run(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._check())
        finally:
            loop.close()

    async def _check(self) -> None:
        client = OllamaClient(self.settings.ollama)
        try:
            is_connected, ver = await client.check_connection()
            if not is_connected:
                self.signals.check_completed.emit(False, ver, [])
                return

            models = await client.list_installed_models()
            self.signals.check_completed.emit(True, ver, models)
        except Exception as exc:  # noqa: BLE001
            self.signals.check_completed.emit(False, str(exc), [])


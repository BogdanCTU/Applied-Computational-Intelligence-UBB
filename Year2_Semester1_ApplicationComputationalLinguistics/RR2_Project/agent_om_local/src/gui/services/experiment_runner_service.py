"""Non-blocking Qt background experiment runner with DB mutex and cooperative cancellation."""

from __future__ import annotations

import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, QThread, Signal

from ..paths import ProjectPaths, resolve_project_paths
from .database_service import DatabaseService

WIZARD_14_STAGES: List[Dict[str, str]] = [
    {"index": "1", "key": "env_check", "title": "1. Environment & Service Verification"},
    {"index": "2", "key": "dataset_select", "title": "2. Ontology Dataset & Reference Selection"},
    {"index": "3", "key": "config_profile", "title": "3. Configuration Profile & Guardrails"},
    {"index": "4", "key": "1_ontology_loading", "title": "4. RDF/OWL Ontology Parsing"},
    {"index": "5", "key": "2_entity_extraction", "title": "5. Class & Property Entity Extraction"},
    {"index": "6", "key": "3_source_retrieval", "title": "6. Syntactic Normalization & Source Retrieval"},
    {"index": "7", "key": "4_target_retrieval", "title": "7. Lexical Annotation Explanation (LLM)"},
    {"index": "8", "key": "4_target_retrieval_sem", "title": "8. Semantic Subgraph & BNode Verbalization"},
    {"index": "9", "key": "5_vector_ingestion", "title": "9. PostgreSQL + pgvector Hybrid Memory Indexing"},
    {"index": "10", "key": "candidate_search", "title": "10. Per-Strategy Cosine Similarity Search"},
    {"index": "11", "key": "rrf_fusion", "title": "11. Reciprocal Rank Fusion (RRF)"},
    {"index": "12", "key": "6_matching_validation", "title": "12. Exact-Name Bypass & LLM Validation"},
    {"index": "13", "key": "reciprocal_merger", "title": "13. Bidirectional Reciprocal Merger"},
    {"index": "14", "key": "7_complete", "title": "14. Alignment Evaluation & Artifact Persistence"},
]


class _LocalExperimentWorker(QObject):
    """Worker executing `run_local_experiment` inside a dedicated `QThread`."""

    stage_updated = Signal(str, int, int, str)
    log_emitted = Signal(str)
    finished_ok = Signal(dict)
    cancelled = Signal(dict)
    failed = Signal(str)

    def __init__(self, params: Dict[str, Any], cancel_event: threading.Event):
        super().__init__()
        self.params = params
        self.cancel_event = cancel_event

    def run(self) -> None:
        db_name = str(self.params.get("db_name_override") or "agent_om_experimental")
        if not DatabaseService.acquire_db_lock(db_name, blocking=False):
            self.failed.emit(
                f"Database '{db_name}' is currently locked by another active run. "
                "Wait for it to complete or choose a different isolated database."
            )
            return

        try:
            # Import runner cleanly in both source and PyInstaller frozen modes
            from scripts.run_local_replication import run_local_experiment

            def _on_stage(stage: str, cur: int, tot: int, msg: str) -> None:
                ts = datetime.now().strftime("%H:%M:%S")
                self.log_emitted.emit(f"[{ts}] [{stage}] ({cur}/{tot}) {msg}")
                self.stage_updated.emit(stage, cur, tot, msg)

            summary = run_local_experiment(
                **self.params,
                stage_callback=_on_stage,
                should_cancel=self.cancel_event.is_set,
            )
            if summary.get("status") == "cancelled":
                self.log_emitted.emit(f"Run '{summary.get('experiment_id')}' safely cancelled.")
                self.cancelled.emit(summary)
            else:
                self.log_emitted.emit(
                    f"Run '{summary.get('experiment_id')}' completed in {summary.get('total_runtime_s')}s."
                )
                self.finished_ok.emit(summary)
        except Exception as exc:
            self.log_emitted.emit(f"ERROR: {type(exc).__name__}: {exc}")
            self.failed.emit(f"{type(exc).__name__}: {exc}")
        finally:
            DatabaseService.release_db_lock(db_name)


class _UpstreamSubprocessWorker(QObject):
    """Worker executing `scripts/run_upstream_isolated.py` as a cancellable subprocess."""

    stage_updated = Signal(str, int, int, str)
    log_emitted = Signal(str)
    finished_ok = Signal(dict)
    cancelled = Signal(dict)
    failed = Signal(str)

    def __init__(
        self,
        paths: ProjectPaths,
        experiment_id: str,
        max_entities: Optional[int],
        cancel_event: threading.Event,
    ):
        super().__init__()
        self.paths = paths
        self.experiment_id = experiment_id
        self.max_entities = max_entities
        self.cancel_event = cancel_event
        self._proc: Optional[subprocess.Popen[str]] = None

    def terminate_subprocess(self) -> None:
        if self._proc is not None and self._proc.poll() is None:
            try:
                self._proc.terminate()
            except Exception:
                pass

    def run(self) -> None:
        if not DatabaseService.acquire_db_lock("agent_om_upstream", blocking=False):
            self.failed.emit("Database 'agent_om_upstream' is locked by another active run.")
            return

        try:
            runner_script = self.paths.project_root / "scripts" / "run_upstream_isolated.py"
            py_exe = self.paths.project_root / ".venv" / "Scripts" / "python.exe"
            if not py_exe.is_file():
                py_exe = Path(sys.executable)
            cmd = [str(py_exe), str(runner_script), "--experiment-id", self.experiment_id]
            if self.max_entities:
                cmd.extend(["--max-entities", str(self.max_entities)])

            self.log_emitted.emit(f"Launching isolated upstream runner: {' '.join(cmd)}")
            self._proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            assert self._proc.stdout is not None
            for line in self._proc.stdout:
                stripped = line.rstrip()
                if stripped:
                    self.log_emitted.emit(stripped)
                    self.stage_updated.emit("upstream_isolated", 1, 1, stripped)
                if self.cancel_event.is_set():
                    self.terminate_subprocess()
                    break

            rc = self._proc.wait(timeout=15)
            summary_path = self.paths.replication_runs_dir / self.experiment_id / "run_summary.json"
            if self.cancel_event.is_set():
                self.cancelled.emit({"experiment_id": self.experiment_id, "status": "cancelled"})
            elif rc == 0 and summary_path.is_file():
                import json

                self.finished_ok.emit(json.loads(summary_path.read_text(encoding="utf-8")))
            else:
                self.failed.emit(f"Upstream isolated runner exited with code {rc}.")
        except Exception as exc:
            self.failed.emit(f"{type(exc).__name__}: {exc}")
        finally:
            DatabaseService.release_db_lock("agent_om_upstream")


class ExperimentRunnerService(QObject):
    """Controller managing non-blocking background execution and safe cancellation."""

    stage_updated = Signal(str, int, int, str)
    log_emitted = Signal(str)
    run_started = Signal(str)
    run_finished = Signal(dict)
    run_cancelled = Signal(dict)
    run_failed = Signal(str)

    def __init__(self, paths: ProjectPaths | None = None, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.paths = paths or resolve_project_paths()
        self._thread: Optional[QThread] = None
        self._worker: Optional[QObject] = None
        self._cancel_event = threading.Event()
        self._active_experiment_id: Optional[str] = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.isRunning()

    @property
    def active_experiment_id(self) -> Optional[str]:
        return self._active_experiment_id

    def start_local_run(self, **params: Any) -> None:
        if self.is_running:
            raise RuntimeError(
                f"Experiment '{self._active_experiment_id}' is already running. Cancel or wait before starting another."
            )
        self._cancel_event.clear()
        exp_id = str(params["experiment_id"])
        params.setdefault("output_base_dir", self.paths.replication_runs_dir)
        self._active_experiment_id = exp_id

        thread = QThread()
        worker = _LocalExperimentWorker(params=params, cancel_event=self._cancel_event)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.stage_updated.connect(self.stage_updated)
        worker.log_emitted.connect(self.log_emitted)
        worker.finished_ok.connect(self._handle_finished)
        worker.cancelled.connect(self._handle_cancelled)
        worker.failed.connect(self._handle_failed)

        worker.finished_ok.connect(thread.quit)
        worker.cancelled.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(self._cleanup_thread)

        self._thread = thread
        self._worker = worker
        self.run_started.emit(exp_id)
        thread.start()

    def start_upstream_isolated_run(
        self,
        experiment_id: str,
        max_entities: Optional[int] = None,
    ) -> None:
        if self.is_running:
            raise RuntimeError(f"Experiment '{self._active_experiment_id}' is already running.")
        self._cancel_event.clear()
        self._active_experiment_id = experiment_id

        thread = QThread()
        worker = _UpstreamSubprocessWorker(
            paths=self.paths,
            experiment_id=experiment_id,
            max_entities=max_entities,
            cancel_event=self._cancel_event,
        )
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.stage_updated.connect(self.stage_updated)
        worker.log_emitted.connect(self.log_emitted)
        worker.finished_ok.connect(self._handle_finished)
        worker.cancelled.connect(self._handle_cancelled)
        worker.failed.connect(self._handle_failed)

        worker.finished_ok.connect(thread.quit)
        worker.cancelled.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(self._cleanup_thread)

        self._thread = thread
        self._worker = worker
        self.run_started.emit(experiment_id)
        thread.start()

    def cancel_active_run(self) -> None:
        """Request safe cooperative cancellation of the active experiment."""
        if not self.is_running:
            return
        self.log_emitted.emit("Cancellation requested — stopping cleanly at current boundary...")
        self._cancel_event.set()
        if isinstance(self._worker, _UpstreamSubprocessWorker):
            self._worker.terminate_subprocess()

    def _handle_finished(self, summary: Dict[str, Any]) -> None:
        self.run_finished.emit(summary)

    def _handle_cancelled(self, summary: Dict[str, Any]) -> None:
        self.run_cancelled.emit(summary)

    def _handle_failed(self, err: str) -> None:
        self.run_failed.emit(err)

    def _cleanup_thread(self) -> None:
        self._active_experiment_id = None
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None
        if self._thread is not None:
            self._thread.deleteLater()
            self._thread = None


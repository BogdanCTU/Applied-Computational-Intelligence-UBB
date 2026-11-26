"""Python bridge to the .NET 9.0 RoslynPreprocessor CLI (single and persistent batch modes)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from bug_detector.config.settings import AppConfig, NormalizationConfig, load_config
from bug_detector.logging_utils import get_logger
from bug_detector.preprocessing.models import FileAnalysisResult

logger = get_logger(__name__)


class RoslynPreprocessorClient:
    """Manages invocation of the compiled RoslynPreprocessor .NET assembly."""

    def __init__(
        self,
        config: AppConfig | None = None,
        timeout_seconds: int | None = None,
    ) -> None:
        self.config = config or load_config()
        self.project_path: Path = self.config.roslyn_project_path
        self.dll_path: Path = self.config.roslyn_dll_path
        self.timeout_seconds = timeout_seconds or self.config.inference.roslyn_timeout_seconds
        self._proc: subprocess.Popen[str] | None = None

    def ensure_built(self, force_rebuild: bool = False) -> Path:
        """Ensure RoslynPreprocessor.dll is built in Release mode."""
        if self.dll_path.exists() and not force_rebuild:
            return self.dll_path
        if not self.project_path.exists():
            raise FileNotFoundError(f"RoslynPreprocessor project not found: {self.project_path}")

        logger.info("Building RoslynPreprocessor (%s)...", self.project_path)
        proc = subprocess.run(
            ["dotnet", "build", str(self.project_path), "-c", "Release"],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        if proc.returncode != 0 or not self.dll_path.exists():
            raise RuntimeError(
                f"RoslynPreprocessor build failed (rc={proc.returncode}): {proc.stdout}\n{proc.stderr}"
            )
        return self.dll_path

    def _start_batch_process(self) -> subprocess.Popen[str]:
        dll = self.ensure_built()
        return subprocess.Popen(
            ["dotnet", str(dll), "batch"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )

    def _ensure_batch_process(self) -> subprocess.Popen[str]:
        if self._proc is None or self._proc.poll() is not None:
            self._proc = self._start_batch_process()
        return self._proc

    def close(self) -> None:
        """Shut down the persistent batch subprocess if running."""
        if self._proc is not None:
            try:
                if self._proc.stdin and not self._proc.stdin.closed:
                    self._proc.stdin.close()
                self._proc.wait(timeout=5)
            except Exception:
                self._proc.kill()
            finally:
                self._proc = None

    def __enter__(self) -> "RoslynPreprocessorClient":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()

    def analyze_source(
        self,
        source_code: str,
        file_path: str = "Input.cs",
        mode: str = "file",
        normalization: NormalizationConfig | None = None,
        request_id: str | None = None,
    ) -> FileAnalysisResult:
        """Analyze a single C# file or method snippet via Roslyn."""
        norm = normalization or self.config.normalization
        payload = {
            "request_id": request_id,
            "mode": mode,
            "file_path": file_path,
            "source_code": source_code,
            "normalization": norm.model_dump(),
        }
        return self._send_batch_item(payload)

    def _send_batch_item(self, payload: dict[str, Any]) -> FileAnalysisResult:
        line_in = json.dumps(payload, ensure_ascii=False)
        for attempt in range(2):
            proc = self._ensure_batch_process()
            assert proc.stdin is not None and proc.stdout is not None
            try:
                proc.stdin.write(line_in + "\n")
                proc.stdin.flush()
                line_out = proc.stdout.readline()
                if not line_out:
                    raise EOFError("RoslynPreprocessor batch process closed stdout unexpectedly.")
                data = json.loads(line_out)
                return FileAnalysisResult.model_validate(data)
            except Exception as exc:
                logger.warning("Roslyn batch communication error (attempt %d): %s", attempt + 1, exc)
                self.close()
                if attempt == 1:
                    return FileAnalysisResult(
                        request_id=payload.get("request_id"),
                        success=False,
                        file_path=str(payload.get("file_path", "Input.cs")),
                        has_syntax_errors=True,
                        syntax_error_count=1,
                        error_message=f"RoslynPreprocessor bridge error: {exc}",
                    )
        raise RuntimeError("Unreachable")

    def analyze_batch(
        self,
        items: list[dict[str, Any]],
        normalization: NormalizationConfig | None = None,
    ) -> list[FileAnalysisResult]:
        """Analyze a list of {'source_code', 'file_path', 'mode', 'request_id'} dicts."""
        norm_dict = (normalization or self.config.normalization).model_dump()
        results: list[FileAnalysisResult] = []
        for idx, item in enumerate(items):
            payload = {
                "request_id": item.get("request_id", str(idx)),
                "mode": item.get("mode", "file"),
                "file_path": item.get("file_path", "Input.cs"),
                "source_code": item.get("source_code", ""),
                "normalization": item.get("normalization", norm_dict),
            }
            results.append(self._send_batch_item(payload))
        return results

    def analyze_file_path(self, path: Path, normalization: NormalizationConfig | None = None) -> FileAnalysisResult:
        """Read a `.cs` file from disk and analyze it with Roslyn."""
        text = Path(path).read_text(encoding="utf-8", errors="replace")
        return self.analyze_source(
            source_code=text,
            file_path=str(path),
            mode="file",
            normalization=normalization,
        )

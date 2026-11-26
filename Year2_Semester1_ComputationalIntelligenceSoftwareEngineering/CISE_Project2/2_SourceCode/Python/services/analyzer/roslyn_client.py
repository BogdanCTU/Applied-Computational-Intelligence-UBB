"""Python bridge to the Roslyn .NET C# Analyzer."""
from __future__ import annotations

import hashlib
import json
import subprocess
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.settings import PROJECT_ROOT
from utils.logger import setup_logger

logger = setup_logger("roslyn_client")


class RoslynClientError(Exception):
    """Base exception for Roslyn analyzer errors."""
    pass


class RoslynClient:
    """Invokes the Roslyn C# Analyzer CLI via dotnet subprocess for method, class, and file analysis."""

    ANALYZER_VERSION = "2.0.0"
    FEATURE_SCHEMA_VERSION = "3.0.0"

    def __init__(
        self,
        project_path: Optional[Path] = None,
        dll_path: Optional[Path] = None,
        timeout_seconds: int = 30,
        cache_size: int = 1024,
    ) -> None:
        default_proj = (
            PROJECT_ROOT / "2_SourceCode" / "RoslynAnalyzer" / "RoslynAnalyzer.csproj"
            if (PROJECT_ROOT / "2_SourceCode" / "RoslynAnalyzer" / "RoslynAnalyzer.csproj").exists()
            else PROJECT_ROOT / "roslyn_analyzer" / "RoslynAnalyzer.csproj"
        )
        default_dll = default_proj.parent / "bin" / "Release" / "net9.0" / "RoslynAnalyzer.dll"
        self.project_path = project_path or default_proj
        self.dll_path = dll_path or default_dll
        self.timeout_seconds = timeout_seconds
        self._cache_size = max(0, cache_size)
        self._source_cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._ensure_built()

    def _ensure_built(self) -> None:
        """Verify binary exists or build it."""
        if not self.dll_path.exists() and self.project_path.exists():
            logger.info(f"RoslynAnalyzer binary missing at {self.dll_path}. Building via dotnet...")
            proc = subprocess.run(
                ["dotnet", "build", str(self.project_path), "-c", "Release"],
                capture_output=True,
                text=True,
            )
            if proc.returncode != 0:
                raise RoslynClientError(f"Failed to build Roslyn analyzer: {proc.stderr}")

    @staticmethod
    def _normalize_code(code: str) -> str:
        return code.replace("\r\n", "\n").replace("\r", "\n")

    def _cache_get(self, key: str) -> Optional[Dict[str, Any]]:
        if self._cache_size <= 0 or key not in self._source_cache:
            return None
        self._source_cache.move_to_end(key)
        return self._source_cache[key]

    def _cache_put(self, key: str, value: Dict[str, Any]) -> None:
        if self._cache_size <= 0:
            return
        self._source_cache[key] = value
        self._source_cache.move_to_end(key)
        while len(self._source_cache) > self._cache_size:
            self._source_cache.popitem(last=False)

    def analyze_source(
        self,
        code: Optional[str] = None,
        file_path: Optional[Path | str] = None,
        line: Optional[int] = None,
        include_metrics: bool = True,
    ) -> Dict[str, Any]:
        """Run full Roslyn AST analysis returning file metadata, classes, methods, and diagnostics."""
        normalized_code = self._normalize_code(code) if (code is not None and not file_path) else None

        # Serve from cache when analyzing in-memory source without line filtering (or filter cached result)
        cache_key: Optional[str] = None
        if normalized_code is not None and include_metrics:
            cache_key = hashlib.sha256(normalized_code.encode("utf-8", errors="replace")).hexdigest()
            cached = self._cache_get(cache_key)
            if cached is not None:
                if line is None:
                    return cached
                return self._filter_response_by_line(cached, line)

        cmd = ["dotnet", str(self.dll_path)]
        if file_path:
            cmd.extend(["--file", str(file_path)])
        if line is not None and normalized_code is None:
            cmd.extend(["--line", str(line)])
        if not include_metrics:
            cmd.append("--no-metrics")

        try:
            proc = subprocess.run(
                cmd,
                input=normalized_code,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                encoding="utf-8",
            )
            if proc.returncode != 0:
                logger.error(f"Roslyn analyzer returned exit code {proc.returncode}: {proc.stderr}")
                raise RoslynClientError(f"Roslyn analyzer error: {proc.stderr or proc.stdout}")

            data = json.loads(proc.stdout)
            if not data.get("success"):
                raise RoslynClientError(f"Roslyn analysis failed: {data.get('error')}")

            if cache_key is not None:
                self._cache_put(cache_key, data)

            if line is not None and normalized_code is not None:
                return self._filter_response_by_line(data, line)
            return data
        except subprocess.TimeoutExpired:
            raise RoslynClientError("Roslyn analyzer timed out.")
        except json.JSONDecodeError as e:
            raise RoslynClientError(f"Failed to parse Roslyn JSON output: {e}\nRaw output: {proc.stdout}")

    @staticmethod
    def _filter_response_by_line(data: Dict[str, Any], line: int) -> Dict[str, Any]:
        """Filter cached AST response by 1-based line number, ordering innermost classes first."""
        methods = [
            m for m in data.get("methods", [])
            if m.get("start_line", 0) <= line <= m.get("end_line", 0)
        ]
        classes = [
            c for c in data.get("classes", [])
            if c.get("start_line", 0) <= line <= c.get("end_line", 0)
        ]
        classes.sort(key=lambda c: (c.get("end_line", 0) - c.get("start_line", 0), c.get("start_line", 0)))
        filtered = dict(data)
        filtered["methods"] = methods
        filtered["classes"] = classes
        return filtered

    def analyze_batch(
        self,
        items: List[Dict[str, Any]],
        timeout_seconds: int = 180,
    ) -> Dict[str, Dict[str, Any]]:
        """Analyze multiple C# files or snippets in a single dotnet process via --batch-stdin."""
        if not items:
            return {}

        results: Dict[str, Dict[str, Any]] = {}
        uncached_payloads: List[str] = []

        for item in items:
            item_id = str(item["id"])
            raw_code = item.get("code")
            if raw_code is not None and not item.get("file_path") and not item.get("no_metrics", False):
                norm = self._normalize_code(raw_code)
                ckey = hashlib.sha256(norm.encode("utf-8", errors="replace")).hexdigest()
                cached = self._cache_get(ckey)
                if cached is not None:
                    line = item.get("line")
                    results[item_id] = self._filter_response_by_line(cached, line) if line is not None else cached
                    continue
                req_obj = {"id": item_id, "code": norm, "line": item.get("line"), "no_metrics": False}
            else:
                req_obj = {
                    "id": item_id,
                    "code": self._normalize_code(raw_code) if raw_code is not None else None,
                    "file_path": str(item["file_path"]) if item.get("file_path") else None,
                    "line": item.get("line"),
                    "no_metrics": bool(item.get("no_metrics", False)),
                }
            uncached_payloads.append(json.dumps(req_obj))

        if not uncached_payloads:
            return results

        cmd = ["dotnet", str(self.dll_path), "--batch-stdin"]
        try:
            proc = subprocess.run(
                cmd,
                input="\n".join(uncached_payloads) + "\n",
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                encoding="utf-8",
            )
            if proc.returncode != 0:
                raise RoslynClientError(f"Roslyn batch analyzer error: {proc.stderr or proc.stdout}")

            for raw_line in proc.stdout.splitlines():
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                envelope = json.loads(raw_line)
                item_id = str(envelope.get("id", ""))
                resp = envelope.get("response", {})
                results[item_id] = resp
            return results
        except subprocess.TimeoutExpired:
            raise RoslynClientError("Roslyn batch analyzer timed out.")
        except json.JSONDecodeError as e:
            raise RoslynClientError(f"Failed to parse Roslyn batch JSON output: {e}")

    def extract_methods(self, code: Optional[str] = None, file_path: Optional[Path | str] = None, line: Optional[int] = None) -> List[Dict[str, Any]]:
        """Extract method locations, signatures, and bodies using Roslyn AST."""
        data = self.analyze_source(code=code, file_path=file_path, line=line)
        return data.get("methods", [])

    def extract_classes(self, code: Optional[str] = None, file_path: Optional[Path | str] = None, line: Optional[int] = None) -> List[Dict[str, Any]]:
        """Extract class/struct/record declarations, locations, and isolated class-level metrics."""
        data = self.analyze_source(code=code, file_path=file_path, line=line)
        return data.get("classes", [])

    def find_enclosing_method(self, code: str, line_number: int) -> Optional[Dict[str, Any]]:
        """Find the specific method that encloses a given 1-based line number."""
        methods = self.extract_methods(code=code, line=line_number)
        return methods[0] if methods else None

    def find_enclosing_class(self, code: str, line_number: int) -> Optional[Dict[str, Any]]:
        """Find the innermost class/struct/record that encloses a given 1-based line number."""
        classes = self.extract_classes(code=code, line=line_number)
        return classes[0] if classes else None

    def calculate_method_metrics(self, code: str) -> Optional[Dict[str, Any]]:
        """Calculate the 26 static code metrics for an isolated method or file."""
        methods = self.extract_methods(code=code)
        if not methods:
            return None
        return methods[0].get("metrics")

    def calculate_class_metrics(self, code: str) -> Optional[Dict[str, Any]]:
        """Calculate the 40 static class-level code metrics for a C# class."""
        classes = self.extract_classes(code=code)
        if not classes:
            return None
        return classes[0].get("metrics")

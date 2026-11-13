"""Python bridge to the Roslyn .NET C# Analyzer."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.settings import PROJECT_ROOT
from src.utils.logger import setup_logger

logger = setup_logger("roslyn_client")


class RoslynClientError(Exception):
    """Base exception for Roslyn analyzer errors."""
    pass


class RoslynClient:
    """Invokes the Roslyn C# Analyzer CLI via dotnet subprocess."""

    def __init__(self, project_path: Optional[Path] = None, dll_path: Optional[Path] = None) -> None:
        self.project_path = project_path or (PROJECT_ROOT / "roslyn_analyzer" / "RoslynAnalyzer.csproj")
        self.dll_path = dll_path or (PROJECT_ROOT / "roslyn_analyzer" / "bin" / "Release" / "net9.0" / "RoslynAnalyzer.dll")
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

    def extract_methods(self, code: Optional[str] = None, file_path: Optional[Path | str] = None, line: Optional[int] = None) -> List[Dict[str, Any]]:
        """Extract method locations, signatures, and bodies using Roslyn AST."""
        cmd = ["dotnet", str(self.dll_path)]
        if file_path:
            cmd.extend(["--file", str(file_path)])
        if line is not None:
            cmd.extend(["--line", str(line)])

        # Normalize newlines to prevent Windows \r\r\n line-offset inflation
        input_data = code.replace("\r\n", "\n").replace("\r", "\n") if (code is not None and not file_path) else None

        try:
            proc = subprocess.run(
                cmd,
                input=input_data,
                capture_output=True,
                text=True,
                timeout=30,
                encoding="utf-8",
            )
            if proc.returncode != 0:
                logger.error(f"Roslyn analyzer returned exit code {proc.returncode}: {proc.stderr}")
                raise RoslynClientError(f"Roslyn analyzer error: {proc.stderr or proc.stdout}")

            data = json.loads(proc.stdout)
            if not data.get("success"):
                raise RoslynClientError(f"Roslyn analysis failed: {data.get('error')}")

            return data.get("methods", [])
        except subprocess.TimeoutExpired:
            raise RoslynClientError("Roslyn analyzer timed out.")
        except json.JSONDecodeError as e:
            raise RoslynClientError(f"Failed to parse Roslyn JSON output: {e}\nRaw output: {proc.stdout}")

    def find_enclosing_method(self, code: str, line_number: int) -> Optional[Dict[str, Any]]:
        """Find the specific method that encloses a given 1-based line number."""
        methods = self.extract_methods(code=code, line=line_number)
        return methods[0] if methods else None

    def calculate_method_metrics(self, code: str) -> Optional[Dict[str, Any]]:
        """Calculate the 26 static code metrics for an isolated method or file."""
        methods = self.extract_methods(code=code)
        if not methods:
            return None
        return methods[0].get("metrics")

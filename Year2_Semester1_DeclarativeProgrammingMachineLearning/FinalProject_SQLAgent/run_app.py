"""Convenience launcher script for the Report SQL Agent desktop application."""

from __future__ import annotations

import sys
import traceback


def _fallback_log_fatal(exc: BaseException) -> None:
    try:
        from config.paths import user_data_root
        crash_log = user_data_root() / "logs" / "startup_crash.log"
        crash_log.parent.mkdir(parents=True, exist_ok=True)
        with open(crash_log, "a", encoding="utf-8") as f:
            f.write(f"\n--- Startup Crash ({type(exc).__name__}) ---\n{traceback.format_exc()}\n")
    except Exception:
        pass


if __name__ == "__main__":
    try:
        from app.main import main
        sys.exit(main())
    except Exception as exc:
        _fallback_log_fatal(exc)
        sys.stderr.write(f"Fatal launcher error: {exc}\n")
        sys.exit(1)


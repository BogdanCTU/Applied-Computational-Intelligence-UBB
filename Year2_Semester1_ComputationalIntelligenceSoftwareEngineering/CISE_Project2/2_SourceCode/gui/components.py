"""Shared UI helpers for compact tables, source rendering, and state loading."""

from __future__ import annotations

import html
import json
from typing import Any

import pandas as pd
import streamlit as st

from bug_detector.config import AppConfig, load_config
from bug_detector.db import BugDetectorRepository, DatabaseManager


def get_app_context() -> tuple[AppConfig, BugDetectorRepository]:
    cfg = load_config()
    repo = BugDetectorRepository(DatabaseManager(cfg.db_path))
    return cfg, repo


def render_source_excerpt(source_code: str, start_line: int | None = None, end_line: int | None = None) -> None:
    """Render C# source with 1-based line numbers and optional highlighted method span."""
    lines = source_code.splitlines()
    if not lines:
        st.code("", language="csharp")
        return

    rows_html: list[str] = []
    for idx, text in enumerate(lines, start=1):
        in_span = start_line is not None and end_line is not None and start_line <= idx <= end_line
        bg = "#fff4cc" if in_span else "transparent"
        marker = ">" if in_span else " "
        escaped = html.escape(text)
        rows_html.append(
            f'<div style="background:{bg};white-space:pre;font-family:monospace;font-size:12.5px;line-height:1.45;">'
            f'<span style="color:#666;user-select:none;">{marker} {idx:4d} | </span>{escaped}</div>'
        )
    st.markdown(
        '<div style="border:1px solid #d0d7de;border-radius:4px;padding:8px;max-height:420px;overflow:auto;">'
        + "".join(rows_html)
        + "</div>",
        unsafe_allow_html=True,
    )


def format_metrics_table(metrics: dict[str, Any]) -> pd.DataFrame:
    keys = [
        ("sample_count", "Samples"),
        ("repository_count", "Repositories"),
        ("bug_count", "BUG (1)"),
        ("clean_count", "CLEAN (0)"),
        ("accuracy", "Accuracy"),
        ("precision", "Precision"),
        ("recall", "Recall"),
        ("f1", "F1-Score"),
        ("specificity", "Specificity"),
        ("fpr", "FPR"),
        ("fnr", "FNR"),
        ("roc_auc", "ROC-AUC"),
        ("pr_auc", "PR-AUC"),
        ("brier_score", "Brier Score"),
        ("uncertain_rate", "Uncertain Rate"),
        ("selective_f1", "Selective F1"),
        ("selective_fpr", "Selective FPR"),
    ]
    rows = [{"Metric": label, "Value": metrics.get(k)} for k, label in keys if k in metrics]
    return pd.DataFrame(rows)


def safe_json_loads(raw: str | None, default: Any = None) -> Any:
    if not raw:
        return default
    try:
        return json.loads(raw)
    except Exception:
        return default

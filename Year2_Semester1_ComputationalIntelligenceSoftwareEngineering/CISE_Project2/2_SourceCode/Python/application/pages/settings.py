"""Settings & System Configuration Page."""
from __future__ import annotations

from pathlib import Path
import streamlit as st
from core.settings import AppSettings
from database.repository import RepositoryDB


def render_settings(db: RepositoryDB, settings: AppSettings) -> None:
    st.title("Settings")
    st.caption("Configure local storage paths, GitHub API authentication, Roslyn analyzer path, and prediction thresholds.")

    with st.form("settings_form"):
        st.subheader("GitHub API Authentication")
        current_token = settings.github.token or ""
        token_masked = f"{current_token[:4]}...{current_token[-4:]}" if len(current_token) > 8 else ("Set" if current_token else "Not Set")
        st.caption(f"Token status: {token_masked}")
        token = st.text_input(
            "GitHub Personal Access Token",
            value="",
            type="password",
            placeholder="ghp_... (leave empty to keep current)",
        )

        st.subheader("Local Storage Paths")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            repo_dir = st.text_input("Cloned repositories directory", value=str(settings.storage.repositories_dir))
            db_path = st.text_input("SQLite database path", value=str(settings.storage.database_path))
        with col_s2:
            models_dir = st.text_input("Models directory", value=str(settings.storage.models_dir))
            exports_dir = st.text_input("Dataset exports directory", value=str(settings.storage.exports_dir))

        st.subheader("Roslyn C# Analyzer")
        roslyn_proj = st.text_input("Roslyn analyzer project (.csproj)", value=str(settings.roslyn.project_path))
        if not Path(roslyn_proj).exists():
            st.warning(f"Roslyn project file not found at `{roslyn_proj}`.")

        st.subheader("Prediction Thresholds and Privacy")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            low_thresh = st.slider(
                "Low risk ceiling",
                0.10,
                0.45,
                float(settings.prediction.low_risk_threshold),
                0.05,
            )
            med_thresh = st.slider(
                "Medium risk ceiling",
                0.50,
                0.85,
                float(settings.prediction.medium_risk_threshold),
                0.05,
            )

        with col_p2:
            persist_hist = st.checkbox(
                "Persist prediction history in SQLite",
                value=settings.prediction.persist_history,
            )
            persist_src = st.checkbox(
                "Store raw C# method source in prediction records",
                value=settings.prediction.persist_source_code,
            )

        models = db.list_models()
        if models:
            model_opts = {f"#{m['id']}: {m['name']} ({m['algorithm']})": m["id"] for m in models}
            st.selectbox("Default model", list(model_opts.keys()), index=0)

        submitted = st.form_submit_button("Save Session Configuration", width="stretch")
        if submitted:
            if token.strip():
                settings.github.token = token.strip()
            settings.storage.repositories_dir = Path(repo_dir)
            settings.storage.database_path = Path(db_path)
            settings.storage.models_dir = Path(models_dir)
            settings.storage.exports_dir = Path(exports_dir)
            settings.roslyn.project_path = Path(roslyn_proj)
            settings.prediction.low_risk_threshold = low_thresh
            settings.prediction.medium_risk_threshold = med_thresh
            settings.prediction.persist_history = persist_hist
            settings.prediction.persist_source_code = persist_src
            st.caption("Session configuration updated.")

    st.subheader("Maintenance")
    if st.button("Erase Prediction History", width="stretch"):
        deleted = db.clear_predictions()
        st.caption(f"Cleared {deleted} prediction records.")

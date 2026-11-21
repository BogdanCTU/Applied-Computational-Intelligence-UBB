"""Settings & System Configuration Page."""
from __future__ import annotations

from pathlib import Path
import streamlit as st
from core.settings import AppSettings
from database.repository import RepositoryDB
from ml.model_manager import ModelManager


def render_settings(db: RepositoryDB, settings: AppSettings) -> None:
    st.title("Settings")
    st.caption(
        "Configure repository collection constraints, Roslyn analyzer path, GitHub API authentication, "
        "risk presentation tiers, and unified model defaults."
    )

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

        st.subheader("Collection & SZZ Pipeline Constraints")
        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            target_repos = st.number_input("Target repositories", min_value=10, max_value=300, value=settings.collection.target_repositories)
            commit_limit = st.number_input("Commit mining limit per repo", min_value=50, max_value=2000, value=settings.collection.commit_mining_limit)
        with col_c2:
            max_concurrent = st.number_input("Max concurrent repo ops", min_value=1, max_value=8, value=settings.collection.max_concurrent_repos)
            cp_interval = st.number_input("Checkpoint interval (repos)", min_value=1, max_value=25, value=settings.collection.checkpoint_interval)
        with col_c3:
            roslyn_timeout = st.number_input("Roslyn timeout (seconds)", min_value=10, max_value=300, value=settings.roslyn.timeout_seconds)
            st.caption(f"Clone strategy: `{settings.collection.clone_strategy}` (required for SZZ)")

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

        st.subheader("Risk Tiers and Privacy")
        st.caption("Binary predictions apply each model bundle's stored optimized decision threshold; risk tiers organize triage priorities.")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            low_thresh = st.slider("Low risk ceiling", 0.10, 0.45, float(settings.prediction.low_risk_threshold), 0.05)
            med_thresh = st.slider("Medium risk ceiling", 0.50, 0.85, float(settings.prediction.medium_risk_threshold), 0.05)
        with col_p2:
            persist_hist = st.checkbox("Persist prediction history in SQLite", value=settings.prediction.persist_history)
            persist_src = st.checkbox("Store analyzed C# source code in prediction logs", value=settings.prediction.persist_source_code)

        models = ModelManager(settings.storage.models_dir, db=db).list_saved_models()
        if models:
            model_opts = {
                f"{m.get('name')} ({m.get('granularity', 'method')} | {m.get('algorithm')} | tau={float(m.get('decision_threshold', 0.50)):.2f})": m.get("id")
                for m in models
            }
            st.selectbox("Default model (Unified Registry)", list(model_opts.keys()), index=0)

        submitted = st.form_submit_button("Save Session Configuration", width="stretch")
        if submitted:
            if token.strip():
                settings.github.token = token.strip()
            settings.collection.target_repositories = int(target_repos)
            settings.collection.commit_mining_limit = int(commit_limit)
            settings.collection.max_concurrent_repos = int(max_concurrent)
            settings.collection.checkpoint_interval = int(cp_interval)
            settings.roslyn.timeout_seconds = int(roslyn_timeout)
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

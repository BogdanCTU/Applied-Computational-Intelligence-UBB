"""Settings & System Configuration Page."""
from __future__ import annotations

from pathlib import Path
import streamlit as st
from config.settings import AppSettings
from src.database.repository import RepositoryDB


def render_settings(db: RepositoryDB, settings: AppSettings) -> None:
    st.header("⚙️ Application & Environment Settings")
    st.markdown("Configure local storage paths, GitHub API authentication, Roslyn Analyzer, and defect prediction guardrails.")

    with st.form("settings_form"):
        # 1. GitHub API Authentication
        st.subheader("1. GitHub API Authentication")
        current_token = settings.github.token or ""
        token_masked = f"{current_token[:4]}...{current_token[-4:]}" if len(current_token) > 8 else ("Set" if current_token else "Not Set")
        st.caption(f"Current Token Status: **{token_masked}**")
        token = st.text_input(
            "GitHub Personal Access Token (PAT)",
            value="",
            type="password",
            help="Optional. Raises rate limits from 60 to 5,000 requests per hour. Never logged or exposed.",
            placeholder="ghp_xxxxxxxxxxxxxxxxxxxx (leave empty to keep current)",
        )

        st.markdown("---")

        # 2. Local Storage Directories
        st.subheader("2. Local Storage Directories")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            repo_dir = st.text_input("Repositories Cloned Directory", value=str(settings.storage.repositories_dir))
            db_path = st.text_input("SQLite Database Path", value=str(settings.storage.database_path))
        with col_s2:
            models_dir = st.text_input("Trained Models Directory", value=str(settings.storage.models_dir))
            exports_dir = st.text_input("Dataset Exports Directory", value=str(settings.storage.exports_dir))

        st.markdown("---")

        # 3. Roslyn Analyzer & .NET Configuration
        st.subheader("3. Microsoft Roslyn C# Analyzer")
        roslyn_proj = st.text_input("Roslyn Analyzer Project Path (.csproj)", value=str(settings.roslyn.project_path))
        proj_exists = Path(roslyn_proj).exists()
        if proj_exists:
            st.success(f"✅ Roslyn project found at `{roslyn_proj}`")
        else:
            st.warning(f"⚠️ Roslyn project file not found at `{roslyn_proj}`")

        st.markdown("---")

        # 4. Machine Learning & Prediction Configuration
        st.subheader("4. Real-Time Defect Prediction & Privacy Guardrails")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            low_thresh = st.slider(
                "Low Risk Score Ceiling (0.00 – ceiling = Low risk)",
                0.10, 0.45, float(settings.prediction.low_risk_threshold), 0.05,
            )
            med_thresh = st.slider(
                "Medium Risk Score Ceiling (ceiling – 1.00 = High risk)",
                0.50, 0.85, float(settings.prediction.medium_risk_threshold), 0.05,
            )

        with col_p2:
            persist_hist = st.checkbox(
                "Persist Prediction History in SQLite",
                value=settings.prediction.persist_history,
                help="Stores prediction metrics and estimated risk in local database.",
            )
            persist_src = st.checkbox(
                "Store Raw C# Method Source in Prediction Records",
                value=settings.prediction.persist_source_code,
                help="Disabled by default for code privacy. If disabled, only extracted numerical metrics are logged.",
            )

        # 5. Default Model Selection
        models = db.list_models()
        if models:
            model_opts = {f"#{m['id']}: {m['name']} ({m['algorithm']})": m["id"] for m in models}
            def_idx = 0
            st.selectbox("Default Model for Quick Predictions", list(model_opts.keys()), index=def_idx)

        submitted = st.form_submit_button("💾 Save Session Configuration", use_container_width=True)
        if submitted:
            # Update settings in session memory
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

            st.success("✅ Configuration saved for the current session! (To persist across application restarts, set environment variables or `.env`).")

    # Clear History Utility
    st.markdown("---")
    st.subheader("🧹 Privacy Actions")
    col_cl1, col_cl2 = st.columns([2, 1])
    with col_cl1:
        st.write("Erase all logged predictions from local SQLite storage permanently.")
    with col_cl2:
        if st.button("🗑️ Erase Prediction History", use_container_width=True):
            deleted = db.clear_predictions()
            st.success(f"Cleared {deleted} prediction records.")

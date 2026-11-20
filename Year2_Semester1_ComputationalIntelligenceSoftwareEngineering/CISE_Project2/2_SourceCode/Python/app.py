"""Streamlit Main Application Entrypoint.
Provides navigation layout and session state management across all pages.
"""
from __future__ import annotations

import sys
from pathlib import Path

_current_dir = Path(__file__).resolve().parent
if str(_current_dir) not in sys.path:
    sys.path.insert(0, str(_current_dir))

import pandas as pd
import streamlit as st
from core.settings import get_settings
from database.connection import Database
from database.repository import RepositoryDB

st.set_page_config(
    page_title="C# Defect Predictor",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "settings" not in st.session_state:
    st.session_state.settings = get_settings()

if "db" not in st.session_state:
    db = Database(st.session_state.settings.storage.database_path)
    st.session_state.db = db
    st.session_state.repo_db = RepositoryDB(db)


def main() -> None:
    with st.sidebar:
        st.subheader("C# Defect Predictor")
        st.caption("Method-level software defect prediction")

        page_options = [
            "Dashboard",
            "Repository Collection",
            "Bug Analysis & SZZ",
            "Dataset Management",
            "Model Training",
            "Model Evaluation",
            "Real-World Bug Prediction",
            "Settings",
        ]

        if "current_page" not in st.session_state:
            st.session_state.current_page = page_options[0]

        selected_page = st.radio(
            "Navigation",
            options=page_options,
            index=page_options.index(st.session_state.current_page) if st.session_state.current_page in page_options else 0,
        )
        st.session_state.current_page = selected_page

        try:
            stats = st.session_state.repo_db.get_summary_statistics()
            st.subheader("Workspace Summary")
            summary_df = pd.DataFrame(
                [
                    {"Item": "Repositories", "Count": f"{stats['repositories_total']} ({stats['repositories_cloned']} cloned)"},
                    {"Item": "Commits", "Count": f"{stats['commits_total']} ({stats['commits_bug_fix']} fixes)"},
                    {"Item": "Observations", "Count": str(stats["observations_total"])},
                    {"Item": "Defect-prone (1)", "Count": str(stats["observations_buggy"])},
                    {"Item": "Candidate-clean (0)", "Count": str(stats["observations_non_buggy"])},
                    {"Item": "Datasets / Models", "Count": f"{stats['datasets_count']} / {stats['models_count']}"},
                ]
            )
            st.dataframe(summary_df, hide_index=True, width="stretch")
        except Exception:
            pass

        st.caption("CISE Project 2 | Babes-Bolyai University")

    if selected_page == "Dashboard":
        from application.pages.dashboard import render_dashboard
        render_dashboard(st.session_state.repo_db, st.session_state.settings)
    elif selected_page == "Repository Collection":
        from application.pages.repository_collection import render_repository_collection
        render_repository_collection(st.session_state.repo_db, st.session_state.settings)
    elif selected_page == "Bug Analysis & SZZ":
        from application.pages.bug_analysis import render_bug_analysis
        render_bug_analysis(st.session_state.repo_db, st.session_state.settings)
    elif selected_page == "Dataset Management":
        from application.pages.dataset_management import render_dataset_management
        render_dataset_management(st.session_state.repo_db, st.session_state.settings)
    elif selected_page == "Model Training":
        from application.pages.model_training import render_model_training
        render_model_training(st.session_state.repo_db, st.session_state.settings)
    elif selected_page == "Model Evaluation":
        from application.pages.model_evaluation import render_model_evaluation
        render_model_evaluation(st.session_state.repo_db, st.session_state.settings)
    elif selected_page == "Real-World Bug Prediction":
        from application.pages.bug_prediction import render_bug_prediction
        render_bug_prediction(st.session_state.repo_db, st.session_state.settings)
    elif selected_page == "Settings":
        from application.pages.settings import render_settings
        render_settings(st.session_state.repo_db, st.session_state.settings)


if __name__ == "__main__":
    main()

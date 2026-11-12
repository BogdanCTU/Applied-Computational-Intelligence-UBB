"""Streamlit Main Application Entrypoint.
Provides the navigation layout and session state management across all pages.
"""
from __future__ import annotations

import streamlit as st
from config.settings import get_settings
from src.database.connection import Database
from src.database.repository import RepositoryDB

# Configure main page settings
st.set_page_config(
    page_title="C# Defect Predictor | ML Bug Detection",
    page_icon="🐛",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize settings and database in session state
if "settings" not in st.session_state:
    st.session_state.settings = get_settings()

if "db" not in st.session_state:
    db = Database(st.session_state.settings.storage.database_path)
    st.session_state.db = db
    st.session_state.repo_db = RepositoryDB(db)


def main() -> None:
    # Sidebar navigation
    with st.sidebar:
        st.title("🐛 C# Defect Predictor")
        st.caption("Machine Learning-Based Bug Detection for C#")
        st.markdown("---")

        page_options = [
            "📊 Dashboard",
            "📥 Repository Collection",
            "🔍 Bug Analysis & SZZ",
            "📁 Dataset Management",
            "🧠 Model Training",
            "📈 Model Evaluation",
            "🎯 Real-World Bug Prediction",
            "⚙️ Settings",
        ]

        if "current_page" not in st.session_state:
            st.session_state.current_page = page_options[0]

        selected_page = st.radio(
            "Navigation",
            options=page_options,
            index=page_options.index(st.session_state.current_page) if st.session_state.current_page in page_options else 0,
        )
        st.session_state.current_page = selected_page

        st.markdown("---")
        # Global quick stats
        try:
            stats = st.session_state.repo_db.get_summary_statistics()
            st.markdown("### 📌 Workspace Stats")
            st.write(f"**Repositories:** {stats['repositories_total']} ({stats['repositories_cloned']} cloned)")
            st.write(f"**Commits:** {stats['commits_total']} ({stats['commits_bug_fix']} bug-fixes)")
            st.write(f"**Observations:** {stats['observations_total']}")
            st.write(f"  • Buggy (1): `{stats['observations_buggy']}`")
            st.write(f"  • Non-buggy (0): `{stats['observations_non_buggy']}`")
            st.write(f"  • Uncertain (-1): `{stats['observations_uncertain']}`")
            st.write(f"**Datasets:** {stats['datasets_count']} | **Models:** {stats['models_count']}")
        except Exception:
            pass

        st.markdown("---")
        st.caption("Academic CISE Project 2 • Antigravity AI")

    # Render selected page
    if selected_page == "📊 Dashboard":
        from ui.pages.dashboard import render_dashboard
        render_dashboard(st.session_state.repo_db, st.session_state.settings)
    elif selected_page == "📥 Repository Collection":
        from ui.pages.repository_collection import render_repository_collection
        render_repository_collection(st.session_state.repo_db, st.session_state.settings)
    elif selected_page == "🔍 Bug Analysis & SZZ":
        from ui.pages.bug_analysis import render_bug_analysis
        render_bug_analysis(st.session_state.repo_db, st.session_state.settings)
    elif selected_page == "📁 Dataset Management":
        from ui.pages.dataset_management import render_dataset_management
        render_dataset_management(st.session_state.repo_db, st.session_state.settings)
    elif selected_page == "🧠 Model Training":
        from ui.pages.model_training import render_model_training
        render_model_training(st.session_state.repo_db, st.session_state.settings)
    elif selected_page == "📈 Model Evaluation":
        from ui.pages.model_evaluation import render_model_evaluation
        render_model_evaluation(st.session_state.repo_db, st.session_state.settings)
    elif selected_page == "🎯 Real-World Bug Prediction":
        from ui.pages.bug_prediction import render_bug_prediction
        render_bug_prediction(st.session_state.repo_db, st.session_state.settings)
    elif selected_page == "⚙️ Settings":
        from ui.pages.settings import render_settings
        render_settings(st.session_state.repo_db, st.session_state.settings)


if __name__ == "__main__":
    main()


"""Dashboard page: active model, dataset summary, independent evaluation, recent runs."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from gui.components import format_metrics_table, get_app_context, safe_json_loads


def render() -> None:
    st.header("Dashboard")
    cfg, repo = get_app_context()

    datasets = repo.list_dataset_versions()
    models = repo.list_models()
    active_model = repo.get_active_model()
    runs = repo.list_detection_runs(limit=15)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Active Model", active_model["model_version"] if active_model else "None")
    if datasets:
        ds = datasets[0]
        c2.metric("Dataset Samples", f"{ds['valid_records']:,}")
        c3.metric("Repositories", ds["repository_count"])
        c4.metric("BUG / CLEAN", f"{ds['bug_count']} / {ds['clean_count']}")
    else:
        c2.metric("Dataset Samples", 0)
        c3.metric("Repositories", 0)
        c4.metric("BUG / CLEAN", "0 / 0")

    st.subheader("Active Model Configuration")
    if active_model:
        st.caption(
            f"Algorithm: {active_model['algorithm']} | Experiment: {active_model['experiment_code']} | "
            f"Groups: {', '.join(safe_json_loads(active_model['feature_groups_json'], []))} | "
            f"Thresholds (low / center / high): {active_model['threshold_low']:.3f} / "
            f"{active_model['threshold_center']:.3f} / {active_model['threshold_high']:.3f}"
        )
        with repo.db.connect() as conn:
            eval_rows = conn.execute(
                "SELECT evaluation_split, metrics_json FROM evaluation_results WHERE model_version = ? ORDER BY evaluation_id",
                (active_model["model_version"],),
            ).fetchall()
        if eval_rows:
            tabs = st.tabs([r["evaluation_split"] for r in eval_rows])
            for tab, erow in zip(tabs, eval_rows):
                with tab:
                    m = safe_json_loads(erow["metrics_json"], {})
                    st.dataframe(format_metrics_table(m), width="stretch", hide_index=True)
    else:
        st.info("No active model is registered yet. Run experiments or train a model on the Model Training page.")

    st.subheader("Registered Models")
    if models:
        mdf = pd.DataFrame(
            [
                {
                    "Model Version": m["model_version"],
                    "Experiment": m["experiment_code"],
                    "Dataset": m["dataset_version"],
                    "Low": m["threshold_low"],
                    "Center": m["threshold_center"],
                    "High": m["threshold_high"],
                    "Active": bool(m["is_active"]),
                    "Created": m["created_at"],
                }
                for m in models
            ]
        )
        st.dataframe(mdf, width="stretch", hide_index=True)
    else:
        st.write("No models registered.")

    st.subheader("Recent Detection Runs")
    if runs:
        rdf = pd.DataFrame(
            [
                {
                    "Run ID": r["run_id"],
                    "File": r["file_name"],
                    "Mode": r["input_mode"],
                    "Status": r["analysis_status"],
                    "Methods": r["method_count"],
                    "BUG": r["bug_count"],
                    "CLEAN": r["clean_count"],
                    "UNCERTAIN": r["uncertain_count"],
                    "Timestamp": r["created_at"],
                }
                for r in runs
            ]
        )
        st.dataframe(rdf, width="stretch", hide_index=True)
    else:
        st.write("No manual or CLI detection runs recorded yet.")


if __name__ == "__main__":
    render()

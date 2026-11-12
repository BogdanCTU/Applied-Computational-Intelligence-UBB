"""Real-World Bug Prediction Page: Single-Method, Full-File Batch Inference, and Validation."""
from __future__ import annotations

import io
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd
import plotly.express as px
import streamlit as st

from config.settings import AppSettings
from src.analyzer.roslyn_client import RoslynClient
from src.database.repository import RepositoryDB
from src.ml.model_manager import ModelManager
from src.ml.predictor import (
    BugPredictor,
    MethodPrediction,
    PredictorError,
    NoMethodsFoundError,
    ModelCompatibilityError,
)


def render_risk_badge(risk_category: str, risk_score: float) -> str:
    """Return colored markdown badge for risk presentation."""
    if risk_category == "Low risk":
        return f":green[🟢 **Low risk** (Estimated Risk Score: {risk_score:.3f})]"
    elif risk_category == "Medium risk":
        return f":orange[🟡 **Medium risk** (Estimated Risk Score: {risk_score:.3f})]"
    else:
        return f":red[🔴 **High risk** (Estimated Risk Score: {risk_score:.3f})]"


def render_bug_prediction(db: RepositoryDB, settings: AppSettings) -> None:
    st.header("🎯 Real-Time C# Method Bug Prediction & Defect Risk Scoring")
    st.markdown("""
    Analyze previously unseen C# source code, extract 24 static code metrics using **Microsoft Roslyn**,
    and estimate defect risk using a trained **Random Forest** model.
    """)

    st.info(
        "**Defect Risk Interpretation**: Risk scores are model-estimated defect propensities based on structural "
        "and complexity metrics. A high-risk score indicates structural patterns commonly associated with defects; "
        "it is **not a proof of a defect**, nor does a low-risk score guarantee code correctness."
    )

    # 1. Model Selector
    model_mgr = ModelManager(settings.storage.models_dir, db=db)
    models = model_mgr.list_saved_models()

    if not models:
        st.warning("No trained models found. Please train a Random Forest classifier in **Model Training** first.")
        return

    col_m1, col_m2 = st.columns([2, 1])
    with col_m1:
        model_options = {
            f"{m.get('name', 'unnamed')} (ID: {m.get('id', 'N/A')} | {m.get('algorithm', 'RF')})": m
            for m in models
        }
        selected_label = st.selectbox("Select Trained Model for Inference", list(model_options.keys()))
        selected_model = model_options[selected_label]
    with col_m2:
        st.caption(f"**Model Artifact:** `{Path(selected_model.get('model_file_path', '')).name}`")
        st.caption(f"**Dataset ID:** #{selected_model.get('dataset_id', 'N/A')}")

    # Initialize Predictor
    try:
        predictor = BugPredictor.from_model_identifier(
            model_identifier=selected_model["model_file_path"],
            models_dir=settings.storage.models_dir,
            model_id=selected_model.get("id"),
            db=db,
            low_threshold=settings.prediction.low_risk_threshold,
            medium_threshold=settings.prediction.medium_risk_threshold,
            persist_history=settings.prediction.persist_history,
            persist_source_code=settings.prediction.persist_source_code,
        )
    except ModelCompatibilityError as e:
        st.error(f"Model Compatibility Error: {e}")
        return
    except Exception as e:
        st.error(f"Failed to load model bundle: {e}")
        return

    # 2. Tabs
    tab_single, tab_file, tab_validation, tab_history = st.tabs([
        "✏️ Single Method Analysis",
        "📂 Full .cs File Analysis",
        "🧪 Repository Ground-Truth Validation",
        "📜 Prediction History & Privacy",
    ])

    sample_method = """public int CalculateDiscount(int customerAge, int purchaseTotal, bool isMember)
{
    int discount = 0;
    if (customerAge > 65)
    {
        discount += 15;
    }
    if (purchaseTotal > 100)
    {
        if (isMember)
        {
            discount += 20;
        }
        else
        {
            discount += 5;
        }
    }
    return discount;
}"""

    # -------------------------------------------------------------
    # TAB 1: Single Method Analysis
    # -------------------------------------------------------------
    with tab_single:
        st.subheader("Analyze Single C# Method")
        st.caption("Paste a standalone C# method or expression-bodied method snippet to evaluate.")

        col_inp, col_opts = st.columns([3, 1])
        with col_inp:
            method_code = st.text_area(
                "C# Method Code",
                value=sample_method,
                height=240,
                key="txt_single_method",
            )
        with col_opts:
            st.markdown("**Configured Risk Thresholds:**")
            st.write(f"- Low: `0.00 – {predictor.low_threshold:.2f}`")
            st.write(f"- Medium: `{predictor.low_threshold + 0.01:.2f} – {predictor.medium_threshold:.2f}`")
            st.write(f"- High: `{predictor.medium_threshold + 0.01:.2f} – 1.00`")
            st.caption("Thresholds can be adjusted in **⚙️ Settings**.")

        if st.button("🚀 Analyze Method & Predict Defect Risk", key="btn_single_predict", use_container_width=True):
            with st.spinner("Extracting Roslyn AST metrics and evaluating model..."):
                try:
                    preds = predictor.predict_code(method_code)
                    if not preds:
                        st.warning("No methods extracted from snippet.")
                    else:
                        p = preds[0]
                        st.success(f"Analysis complete for method `{p.method_name}`!")

                        # 1. Prediction summary card
                        st.markdown("### Prediction Outcome")
                        c_res1, c_res2, c_res3, c_res4 = st.columns(4)
                        c_res1.metric("Method Name", p.method_name)
                        c_res2.metric("Enclosing Class", p.class_name or "(Standalone)")
                        c_res3.metric("Defect Risk Score", f"{p.risk_score:.3f}")
                        c_res4.metric("Classification", "Buggy (1)" if p.predicted_label == 1 else "Clean (0)")

                        st.markdown(f"**Risk Level:** {render_risk_badge(p.risk_category, p.risk_score)}")

                        # 2. Influential metrics & explanations
                        st.markdown("#### Influential Metrics & Structural Explanations")
                        if p.influential_metrics:
                            inf_df = pd.DataFrame(p.influential_metrics)
                            inf_df = inf_df.rename(columns={
                                "feature": "Metric",
                                "value": "Measured Value",
                                "threshold": "Alert Threshold",
                                "global_importance": "Model Global Importance",
                                "interpretation": "Engineering Context",
                            })
                            st.dataframe(inf_df, use_container_width=True, hide_index=True)
                        else:
                            st.info("No structural complexity thresholds exceeded. Metrics are within normal operating ranges.")

                        st.caption(
                            "💡 *Note:* Global feature importance represents the tree ensemble's aggregate weight across all training "
                            "repositories. The influential metrics above highlight structural indicators of this specific method that exceed "
                            "heuristic risk thresholds."
                        )

                        # 3. All 24 Extracted Roslyn Metrics
                        with st.expander("🔍 View All 24 Extracted Roslyn Static Code Metrics"):
                            m_df = pd.DataFrame([{"Metric": k, "Extracted Value": v} for k, v in p.metrics.items()])
                            st.dataframe(m_df, use_container_width=True, hide_index=True)

                except NoMethodsFoundError as nfe:
                    st.error(f"Method Extraction Error: {nfe}")
                except PredictorError as pe:
                    st.error(f"Prediction Error: {pe}")
                except Exception as e:
                    st.error(f"Unexpected Error: {e}")

    # -------------------------------------------------------------
    # TAB 2: Full C# File Analysis
    # -------------------------------------------------------------
    with tab_file:
        st.subheader("Analyze Complete .cs File")
        st.caption("Upload a complete C# source file containing multiple classes or methods for batch evaluation.")

        uploaded_cs = st.file_uploader("Upload .cs File", type=["cs"], key="uploader_cs_file")

        if uploaded_cs:
            file_content = uploaded_cs.read().decode("utf-8", errors="replace")
            st.caption(f"Loaded `{uploaded_cs.name}` ({len(file_content.splitlines())} lines).")

            if st.button("🚀 Analyze All Methods in File", key="btn_file_predict", use_container_width=True):
                with st.spinner(f"Extracting methods and analyzing '{uploaded_cs.name}'..."):
                    try:
                        file_preds = predictor.predict_code(file_content, file_name=uploaded_cs.name)
                        st.session_state["file_preds"] = file_preds
                        st.session_state["file_name"] = uploaded_cs.name
                    except NoMethodsFoundError as nfe:
                        st.warning(f"No methods found in file: {nfe}")
                    except Exception as e:
                        st.error(f"File analysis failed: {e}")

        # Display cached file predictions if present
        if "file_preds" in st.session_state and st.session_state.get("file_name"):
            file_preds: List[MethodPrediction] = st.session_state["file_preds"]
            st.markdown(f"### Results for `{st.session_state['file_name']}` ({len(file_preds)} methods detected)")

            # Aggregate stats
            high_count = sum(1 for p in file_preds if p.risk_category == "High risk")
            med_count = sum(1 for p in file_preds if p.risk_category == "Medium risk")
            low_count = sum(1 for p in file_preds if p.risk_category == "Low risk")

            c_f1, c_f2, c_f3, c_f4 = st.columns(4)
            c_f1.metric("Total Methods", len(file_preds))
            c_f2.metric("High Risk Methods", high_count)
            c_f3.metric("Medium Risk Methods", med_count)
            c_f4.metric("Low Risk Methods", low_count)

            st.caption("⚠️ *A file is not defective merely because one method has elevated risk; inspect methods individually.*")

            # Filters and sorting
            col_flt1, col_flt2 = st.columns(2)
            with col_flt1:
                filter_cat = st.multiselect(
                    "Filter by Risk Category",
                    ["High risk", "Medium risk", "Low risk"],
                    default=["High risk", "Medium risk", "Low risk"],
                )
            with col_flt2:
                sort_opt = st.selectbox("Sort By", ["Risk Score (Descending)", "Risk Score (Ascending)", "Method Name", "Lines of Code (LOC)"])

            filtered_preds = [p for p in file_preds if p.risk_category in filter_cat]

            if sort_opt == "Risk Score (Descending)":
                filtered_preds.sort(key=lambda x: x.risk_score, reverse=True)
            elif sort_opt == "Risk Score (Ascending)":
                filtered_preds.sort(key=lambda x: x.risk_score)
            elif sort_opt == "Method Name":
                filtered_preds.sort(key=lambda x: x.method_name)
            elif sort_opt == "Lines of Code (LOC)":
                filtered_preds.sort(key=lambda x: x.metrics.get("loc", 0), reverse=True)

            # Table representation
            table_rows = []
            for p in filtered_preds:
                table_rows.append({
                    "Method Name": p.method_name,
                    "Class": p.class_name,
                    "Lines": f"L{p.start_line}-L{p.end_line}",
                    "Risk Category": p.risk_category,
                    "Risk Score": p.risk_score,
                    "Predicted Class": "Buggy (1)" if p.predicted_label == 1 else "Clean (0)",
                    "Complexity (CC)": p.metrics.get("cyclomatic_complexity", 0),
                    "LOC": p.metrics.get("loc", 0),
                    "Nesting Depth": p.metrics.get("max_nesting_depth", 0),
                })

            df_table = pd.DataFrame(table_rows)
            st.dataframe(df_table, use_container_width=True, hide_index=True)

            # CSV Export
            csv_buf = io.StringIO()
            df_table.to_csv(csv_buf, index=False)
            st.download_button(
                label="📥 Export Prediction Results to CSV",
                data=csv_buf.getvalue(),
                file_name=f"predictions_{st.session_state['file_name']}.csv",
                mime="text/csv",
                use_container_width=True,
            )

    # -------------------------------------------------------------
    # TAB 3: Repository Ground-Truth Validation
    # -------------------------------------------------------------
    with tab_validation:
        st.subheader("Validation on Mined Repository Observations")
        st.markdown("""
        Select previously mined methods from your local repositories to evaluate the predictor
        against ground-truth SZZ and heuristic labels. Inspect **False Positives** and **False Negatives**.
        """)

        train_repos = set(predictor.split_summary.get("train_repositories", []))
        test_repos = set(predictor.split_summary.get("test_repositories", []))

        col_vopt1, col_vopt2 = st.columns([2, 1])
        with col_vopt1:
            strict_holdout = st.checkbox(
                "Filter Out Training Repositories (Strict No-Leakage Benchmark)",
                value=True if train_repos else False,
                help="Ensures validation is performed strictly on holdout test or unseen repositories.",
            )
        with col_vopt2:
            st.caption(f"Model Training Repos: `{len(train_repos)}` | Holdout Repos: `{len(test_repos)}`")

        obs_list = db.list_observations()
        # Filter observations with valid labels (1 or 0)
        eval_obs = [o for o in obs_list if o.get("label") in (0, 1)]
        if strict_holdout and train_repos:
            eval_obs = [o for o in eval_obs if o.get("repository_id") not in train_repos]

        if not eval_obs:
            st.info(
                "No eligible labeled observations found. "
                "If strict filter is enabled, ensure observations from holdout or unseen repositories are mined in **Bug Analysis**."
            )
        else:
            st.write(f"Eligible validation observations: **{len(eval_obs)}**")

            val_limit = st.slider("Number of Observations to Benchmark", 5, min(100, len(eval_obs)), min(20, len(eval_obs)), 5)

            if st.button("🧪 Run Validation Benchmark on Mined Observations", use_container_width=True):
                with st.spinner("Extracting features and evaluating predictions..."):
                    results = []
                    for obs in eval_obs[:val_limit]:
                        feat = db.get_features(obs["id"])
                        if not feat:
                            continue

                        raw_metrics = feat.get("raw_metrics", {})
                        if not raw_metrics:
                            # Reconstruct from features table columns
                            raw_metrics = {k: v for k, v in feat.items() if k not in ("id", "observation_id", "extracted_at", "raw_metrics_json", "raw_metrics")}

                        pred = predictor.predict_from_metrics(
                            metrics=raw_metrics,
                            method_name=obs.get("method_name", "Method"),
                            class_name=obs.get("class_name", "Class"),
                            file_name=obs.get("file_path"),
                        )

                        actual_label = obs["label"]
                        predicted_label = pred.predicted_label

                        # Check correctness
                        is_correct = (actual_label == predicted_label)
                        outcome = "True Positive" if (actual_label == 1 and predicted_label == 1) else (
                            "True Negative" if (actual_label == 0 and predicted_label == 0) else (
                                "False Positive" if (actual_label == 0 and predicted_label == 1) else "False Negative"
                            )
                        )

                        r_id = obs["repository_id"]
                        part_name = "Holdout Test" if r_id in test_repos else ("Training" if r_id in train_repos else "Unseen / External")

                        results.append({
                            "Observation ID": obs["id"],
                            "Repository ID": r_id,
                            "Partition": part_name,
                            "Method": obs["method_name"],
                            "Actual Ground Truth": "Buggy (1)" if actual_label == 1 else "Clean (0)",
                            "Predicted Class": "Buggy (1)" if predicted_label == 1 else "Clean (0)",
                            "Risk Score": pred.risk_score,
                            "Risk Category": pred.risk_category,
                            "Outcome": outcome,
                            "Correct": "✅ Yes" if is_correct else "❌ No",
                        })

                    if results:
                        res_df = pd.DataFrame(results)
                        st.markdown("#### Benchmark Validation Results")

                        # Summary stats
                        acc = sum(1 for r in results if "✅" in r["Correct"]) / len(results)
                        tp = sum(1 for r in results if r["Outcome"] == "True Positive")
                        fp = sum(1 for r in results if r["Outcome"] == "False Positive")
                        tn = sum(1 for r in results if r["Outcome"] == "True Negative")
                        fn = sum(1 for r in results if r["Outcome"] == "False Negative")

                        c_v1, c_v2, c_v3, c_v4 = st.columns(4)
                        c_v1.metric("Validation Accuracy", f"{acc:.1%}")
                        c_v2.metric("True Positives (TP)", tp)
                        c_v3.metric("False Positives (FP)", fp)
                        c_v4.metric("False Negatives (FN)", fn)

                        st.dataframe(res_df, use_container_width=True, hide_index=True)

                        # Filter for Error Analysis (FP / FN)
                        st.markdown("##### Error Analysis: Inspect False Positives & False Negatives")
                        err_df = res_df[res_df["Outcome"].isin(["False Positive", "False Negative"])]
                        if not err_df.empty:
                            st.dataframe(err_df, use_container_width=True, hide_index=True)
                            st.caption(
                                "False Positives usually stem from clean methods with high structural complexity (e.g. parsers or dispatch tables). "
                                "False Negatives often represent subtle semantic or one-line logic bugs with simple syntax structures."
                            )
                        else:
                            st.success("Zero misclassifications in this validation sample!")

    # -------------------------------------------------------------
    # TAB 4: Prediction History & Privacy
    # -------------------------------------------------------------
    with tab_history:
        st.subheader("Inference History & Privacy Guardrails")
        st.markdown("""
        All predictions are computed strictly on your local machine. No code or telemetry is ever transmitted externally.
        """)

        history_rows = db.list_predictions(limit=100)
        c_h1, c_h2, c_h3 = st.columns(3)
        c_h1.metric("Stored Predictions", len(history_rows))
        c_h2.metric("History Logging", "Enabled" if settings.prediction.persist_history else "Disabled")
        c_h3.metric("Raw Code Storage", "Enabled" if settings.prediction.persist_source_code else "Disabled (Privacy Safe)")

        col_act1, col_act2 = st.columns([1, 1])
        with col_act1:
            if st.button("🗑️ Clear Prediction History", key="btn_clear_hist", use_container_width=True):
                deleted = db.clear_predictions()
                st.success(f"Cleared {deleted} prediction records from database.")
                st.rerun()

        if history_rows:
            st.markdown("#### Recent Predictions")
            h_df = pd.DataFrame(history_rows)
            display_cols = ["id", "method_name", "class_name", "file_name", "risk_score", "risk_category", "predicted_label", "created_at"]
            display_cols = [c for c in display_cols if c in h_df.columns]
            st.dataframe(h_df[display_cols], use_container_width=True, hide_index=True)
        else:
            st.info("No prediction history recorded.")

"""Real-World Bug Detection Page: C# Class Input, Multi-Class .cs File Upload, Validation & History."""
from __future__ import annotations

import io
from pathlib import Path
from typing import List
import pandas as pd
import streamlit as st

from core.settings import AppSettings
from database.repository import RepositoryDB
from ml.model_manager import ModelManager
from ml.predictor import (
    BugPredictor,
    ClassPrediction,
    FilePredictionResult,
    ModelCompatibilityError,
    NoClassesFoundError,
    NoMethodsFoundError,
    PredictorError,
)


def _highlight_class_rows(row: pd.Series) -> List[str]:
    if row.get("Predicted Classification") == "Defect-Prone (1)" or row.get("Risk Category") == "High risk":
        return ["background-color: rgba(192, 57, 43, 0.14)"] * len(row)
    return [""] * len(row)


def render_bug_prediction(db: RepositoryDB, settings: AppSettings) -> None:
    st.title("Real-World Bug Detection")
    st.caption(
        "Static ML bug detection for C# classes and complete .cs source files. "
        "Predictions are probabilistic defect indications grounded in historical SZZ evidence, "
        "not formal verification or proof of confirmed defects."
    )

    model_mgr = ModelManager(settings.storage.models_dir, db=db)
    models = model_mgr.list_saved_models()

    if not models:
        st.warning("No trained models found. Train a model in Model Training first.")
        return

    col_m1, col_m2 = st.columns([2, 1])
    with col_m1:
        model_options = {
            f"{m.get('name', 'unnamed')} ({m.get('granularity', 'method')} | {m.get('algorithm', 'Model')} | tau={float(m.get('decision_threshold', 0.50)):.2f})": m
            for m in models
        }
        selected_label = st.selectbox("Model (Unified Registry)", list(model_options.keys()))
        selected_model = model_options[selected_label]
    with col_m2:
        st.caption(f"Artifact: `{Path(selected_model.get('model_file_path', '')).name}`")
        st.caption(
            f"Granularity: `{selected_model.get('granularity', 'method')}` | "
            f"Dataset v`{selected_model.get('dataset_version') or selected_model.get('dataset_id', 'N/A')}` | "
            f"Threshold: `{float(selected_model.get('decision_threshold', 0.50)):.2f}`"
        )

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
        st.error(f"Model compatibility error: {e}")
        return
    except Exception as e:
        st.error(f"Failed to load model bundle: {e}")
        return

    tab_class, tab_file, tab_validation, tab_history = st.tabs([
        "C# Class Analysis (Input A)",
        "C# Source File Upload (Input B)",
        "Repository Class Validation",
        "Prediction History & Diagnostics",
    ])

    sample_class = """namespace OrderProcessing
{
    public class DiscountService
    {
        private readonly decimal _maxRate = 0.40m;

        public decimal ComputeDiscount(decimal totalAmount, int itemCount, bool isVip, string? couponCode)
        {
            if (totalAmount <= 0)
            {
                throw new ArgumentOutOfRangeException(nameof(totalAmount));
            }

            decimal rate = isVip ? 0.15m : 0.05m;
            if (!string.IsNullOrWhiteSpace(couponCode))
            {
                for (int i = 0; i < itemCount; i++)
                {
                    if (couponCode.StartsWith("PROMO") && totalAmount > 100m)
                    {
                        rate += 0.02m;
                    }
                }
            }

            return rate > _maxRate ? totalAmount * _maxRate : totalAmount * rate;
        }
    }
}"""

    # TAB 1: Input A — C# Class Analysis
    with tab_class:
        st.subheader("Single C# Class Analysis")
        col_inp, col_opts = st.columns([3, 1])
        with col_inp:
            class_code = st.text_area(
                "Paste a complete C# class, struct, or record",
                value=sample_class,
                height=290,
                key="txt_single_class",
            )
        with col_opts:
            st.caption(f"Applied Classification Threshold: `{predictor.decision_threshold:.2f}`")
            st.table(pd.DataFrame([
                {"Risk Tier": "Low risk", "Probability": f"0.00 - {predictor.low_threshold:.2f}"},
                {"Risk Tier": "Medium risk", "Probability": f"{predictor.low_threshold + 0.01:.2f} - {predictor.medium_threshold:.2f}"},
                {"Risk Tier": "High risk", "Probability": f"{predictor.medium_threshold + 0.01:.2f} - 1.00"},
            ]))

        if st.button("Analyze Class", key="btn_class_predict", width="stretch"):
            if predictor.granularity != "class" and "class_loc" not in predictor.preprocessor.feature_names_in_:
                st.warning(
                    "Selected model is a preserved method-level bundle. Select a class-level model above "
                    "(e.g. `class_precision_champion_v3`) or use Legacy Method Diagnostics in Tab 4."
                )
            else:
                with st.spinner("Extracting 40 Roslyn class metrics and running inference..."):
                    try:
                        file_res = predictor.predict_csharp_file(code=class_code, file_name="SubmittedClass.cs")
                        cp = file_res.class_predictions[0]
                        st.session_state["last_class_pred"] = cp
                    except NoClassesFoundError as nce:
                        st.error(f"Class extraction error: {nce}")
                    except PredictorError as pe:
                        st.error(f"Prediction error: {pe}")
                    except Exception as e:
                        st.error(f"Unexpected error: {e}")

        if "last_class_pred" in st.session_state:
            cp: ClassPrediction = st.session_state["last_class_pred"]
            st.subheader("Class Detection Result")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Class", cp.class_name)
            m2.metric("Defect Probability", f"{cp.defect_probability:.3f}")
            m3.metric(
                "Predicted Classification",
                "Defect-Prone Class (1)" if cp.predicted_label == 1 else "Candidate-Clean Class (0)",
            )
            m4.metric("Risk Category", cp.risk_category)

            meta_df = pd.DataFrame([{
                "Qualified Name": cp.qualified_class_name,
                "Namespace": cp.namespace_name,
                "Kind": cp.type_kind,
                "Line Range": f"L{cp.start_line}-L{cp.end_line}",
                "Methods": cp.method_count,
                "Class LOC": cp.loc,
                "Total CC": cp.cyclomatic_complexity,
                "Threshold": f"{cp.decision_threshold:.2f}",
            }])
            st.dataframe(meta_df, hide_index=True, width="stretch")

            st.subheader("Influential Structural Indicators")
            if cp.influential_metrics:
                inf_df = pd.DataFrame(cp.influential_metrics).rename(columns={
                    "feature": "Metric",
                    "value": "Value",
                    "threshold": "Reference Threshold",
                    "global_importance": "Global Importance",
                    "interpretation": "Context",
                })
                st.dataframe(inf_df, hide_index=True, width="stretch")
            else:
                st.caption("No heuristic structural complexity alerts triggered.")

            with st.expander("All 40 Extracted Roslyn Class Metrics"):
                m_df = pd.DataFrame([{"Metric": k, "Value": v} for k, v in cp.metrics.items()])
                st.dataframe(m_df, hide_index=True, width="stretch")

    # TAB 2: Input B — Complete .cs File Analysis
    with tab_file:
        st.subheader("Complete C# Source File Analysis (.cs)")
        st.caption(
            "Analyzes every class, struct, and record inside the uploaded .cs file independently, "
            "then computes a file-level summary. File risk reflects class predictions rather than confirmed bugs."
        )

        uploaded_cs = st.file_uploader("Upload C# source file", type=["cs"], key="uploader_cs_file")
        if uploaded_cs:
            file_content = uploaded_cs.read().decode("utf-8", errors="replace")
            st.caption(f"Loaded `{uploaded_cs.name}` ({len(file_content.splitlines())} lines).")

            if st.button("Analyze C# File", key="btn_file_predict", width="stretch"):
                if predictor.granularity != "class" and "class_loc" not in predictor.preprocessor.feature_names_in_:
                    st.warning("Please select a class-level model in the model selector above for .cs file analysis.")
                else:
                    with st.spinner(f"Parsing all classes in '{uploaded_cs.name}'..."):
                        try:
                            file_res = predictor.predict_csharp_file(code=file_content, file_name=uploaded_cs.name)
                            st.session_state["file_pred_result"] = file_res
                        except NoClassesFoundError as nce:
                            st.warning(f"No classes found in file: {nce}")
                        except Exception as e:
                            st.error(f"File analysis failed: {e}")

        if "file_pred_result" in st.session_state:
            fres: FilePredictionResult = st.session_state["file_pred_result"]
            st.subheader(f"File-Level Summary: {fres.file_name}")
            st.caption(fres.disclaimer)

            c_f1, c_f2, c_f3, c_f4, c_f5 = st.columns(5)
            c_f1.metric("Classes Analyzed", fres.classes_analyzed_count)
            c_f2.metric("Classes Flagged", fres.classes_flagged_count)
            c_f3.metric("Highest Risk Score", f"{fres.highest_class_risk_score:.3f}")
            c_f4.metric("Mean Class Risk", f"{fres.mean_class_risk_score:.3f}")
            c_f5.metric("File Risk Category", fres.file_risk_category)

            table_rows = [
                {
                    "Class": c.class_name,
                    "Namespace": c.namespace_name,
                    "Type": c.type_kind,
                    "Lines": f"L{c.start_line}-L{c.end_line}",
                    "Methods": c.method_count,
                    "LOC": c.loc,
                    "Total CC": c.cyclomatic_complexity,
                    "Defect Probability": round(c.defect_probability, 4),
                    "Predicted Classification": "Defect-Prone (1)" if c.predicted_label == 1 else "Candidate-Clean (0)",
                    "Risk Category": c.risk_category,
                }
                for c in sorted(fres.class_predictions, key=lambda x: x.defect_probability, reverse=True)
            ]
            df_table = pd.DataFrame(table_rows)
            styled = df_table.style.apply(_highlight_class_rows, axis=1)
            st.dataframe(styled, width="stretch", hide_index=True)

            # Detailed per-class drill-down
            st.subheader("Individual Class Detail View")
            class_choices = {
                f"{c.qualified_class_name} (L{c.start_line}-L{c.end_line} | Prob: {c.defect_probability:.3f})": c
                for c in fres.class_predictions
            }
            chosen_c_label = st.selectbox("Select analyzed class", list(class_choices.keys()))
            chosen_cls = class_choices[chosen_c_label]
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                st.caption("Influential Metrics")
                if chosen_cls.influential_metrics:
                    st.dataframe(pd.DataFrame(chosen_cls.influential_metrics), hide_index=True, width="stretch")
                else:
                    st.caption("No complexity alerts exceeded.")
            with col_d2:
                st.caption("All 40 Class Metrics")
                st.dataframe(
                    pd.DataFrame([{"Metric": k, "Value": v} for k, v in chosen_cls.metrics.items()]),
                    hide_index=True,
                    width="stretch",
                )

            csv_buf = io.StringIO()
            df_table.to_csv(csv_buf, index=False)
            st.download_button(
                label="Download Class Predictions CSV",
                data=csv_buf.getvalue(),
                file_name=f"class_predictions_{fres.file_name}.csv",
                mime="text/csv",
                width="stretch",
            )

    # TAB 3: Repository Class Validation
    with tab3:
        st.subheader("Validation on Mined Class Observations")
        st.caption("Evaluate the loaded model against SZZ-labeled and candidate-clean class observations in SQLite.")

        train_repos = set(predictor.split_summary.get("train_repositories", []))
        test_repos = set(predictor.split_summary.get("test_repositories", []))
        strict_holdout = st.checkbox("Exclude training repositories (Holdout only)", value=bool(train_repos))
        st.caption(f"Training repos: {len(train_repos)} | Holdout repos: {len(test_repos)}")

        obs_list = db.list_class_observations_with_features(exclude_uncertain=True)
        if strict_holdout and train_repos:
            obs_list = [o for o in obs_list if o.get("repository_id") not in train_repos]

        if not obs_list:
            st.caption("No eligible class observations match current filter.")
        else:
            val_limit = st.slider("Class observations to evaluate", 10, min(500, len(obs_list)), min(50, len(obs_list)), 10)
            if st.button("Run Class Validation Benchmark", width="stretch"):
                results = []
                for obs in obs_list[:val_limit]:
                    pred = predictor.predict_class_from_metrics(
                        metrics=obs,
                        class_name=obs["class_name"],
                        qualified_class_name=obs["qualified_class_name"],
                        namespace_name=obs.get("namespace_name", "Global"),
                        file_name=obs["file_path"],
                        persist_record=False,
                    )
                    actual = int(obs["label"])
                    plabel = pred.predicted_label
                    outcome = (
                        "True Positive" if (actual == 1 and plabel == 1)
                        else "True Negative" if (actual == 0 and plabel == 0)
                        else "False Positive" if (actual == 0 and plabel == 1)
                        else "False Negative"
                    )
                    results.append({
                        "Repository": obs["repository_name"],
                        "Class": obs["qualified_class_name"],
                        "Actual": "Defect-Prone (1)" if actual == 1 else "Candidate-Clean (0)",
                        "Predicted": "Defect-Prone (1)" if plabel == 1 else "Candidate-Clean (0)",
                        "Probability": pred.defect_probability,
                        "Outcome": outcome,
                    })
                res_df = pd.DataFrame(results)
                tp = sum(1 for r in results if r["Outcome"] == "True Positive")
                fp = sum(1 for r in results if r["Outcome"] == "False Positive")
                fn = sum(1 for r in results if r["Outcome"] == "False Negative")
                tn = sum(1 for r in results if r["Outcome"] == "True Negative")
                prec = tp / max(1, tp + fp)
                rec = tp / max(1, tp + fn)
                cv1, cv2, cv3, cv4 = st.columns(4)
                cv1.metric("Precision", f"{prec:.1%}")
                cv2.metric("Recall", f"{rec:.1%}")
                cv3.metric("TP / FP", f"{tp} / {fp}")
                cv4.metric("TN / FN", f"{tn} / {fn}")
                st.dataframe(res_df, hide_index=True, width="stretch")

    # TAB 4: Prediction History & Legacy Method Diagnostic Mode
    with tab4:
        st.subheader("Prediction History & Provenance")
        history_rows = db.list_predictions(limit=100)
        c_h1, c_h2, c_h3 = st.columns(3)
        c_h1.metric("Stored Predictions", len(history_rows))
        c_h2.metric("History Logging", "Enabled" if settings.prediction.persist_history else "Disabled")
        c_h3.metric("Source Storage", "Enabled" if settings.prediction.persist_source_code else "Disabled")

        if st.button("Clear Prediction History", key="btn_clear_hist", width="stretch"):
            db.clear_predictions()
            st.rerun()

        if history_rows:
            h_df = pd.DataFrame(history_rows)
            display_cols = [
                c for c in [
                    "id", "granularity", "model_name", "dataset_version", "decision_threshold",
                    "class_name", "namespace_name", "file_name", "risk_score", "risk_category",
                    "predicted_label", "created_at",
                ] if c in h_df.columns
            ]
            st.dataframe(h_df[display_cols], width="stretch", hide_index=True)
        else:
            st.caption("No prediction history recorded.")

        with st.expander("Legacy Single-Method Diagnostic Mode"):
            st.caption("Available when a preserved method-level bundle (e.g. `et_nested_opt_v3_depth6_leaf6_log2`) is selected.")
            method_snip = st.text_area("Method snippet", value="public int Add(int a, int b) => a + b;", height=120)
            if st.button("Run Method Diagnostic", key="btn_legacy_method"):
                try:
                    mpreds = predictor.predict_code(method_snip)
                    st.dataframe(
                        pd.DataFrame([
                            {
                                "Method": p.method_name,
                                "Score": p.risk_score,
                                "Label": p.predicted_label,
                                "Category": p.risk_category,
                            }
                            for p in mpreds
                        ]),
                        hide_index=True,
                        width="stretch",
                    )
                except (NoMethodsFoundError, PredictorError) as e:
                    st.error(str(e))

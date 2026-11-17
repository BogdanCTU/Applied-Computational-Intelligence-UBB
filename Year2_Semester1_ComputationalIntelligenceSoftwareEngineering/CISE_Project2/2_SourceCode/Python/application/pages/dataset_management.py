"""Dataset Management Page: Feature Extraction, Overview, Statistical Analysis, and CSV Export."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from core.settings import AppSettings
from database.repository import RepositoryDB
from services.dataset.feature_extractor import FeatureExtractor
from services.dataset.dataset_builder import DatasetBuilder, DEFAULT_NUMERICAL_FEATURES
from services.dataset.exporter import DatasetExporter


def render_dataset_management(db: RepositoryDB, settings: AppSettings) -> None:
    st.title("Dataset Management")
    st.caption("Extract 26 Roslyn static code metrics, inspect metric distributions, and export versioned datasets.")

    extractor = FeatureExtractor(db)
    builder = DatasetBuilder(db)
    exporter = DatasetExporter(db, settings.storage.exports_dir)

    tab1, tab2, tab3, tab4 = st.tabs([
        "Feature Extraction",
        "Dataset Overview",
        "Metric Distributions",
        "Snapshots and Export",
    ])

    # TAB 1: Feature Extraction
    with tab1:
        st.subheader("Roslyn Static Code Metric Extraction")
        st.caption(f"Analyzer: Microsoft.CodeAnalysis.CSharp v4.12.0 (.NET 9.0) | Version: {FeatureExtractor.ANALYZER_VERSION}")

        all_obs = db.list_observations()
        total_obs = len(all_obs)
        needing_extraction = db.get_observations_needing_features(include_failed=False)
        failed_obs = db.get_observations_needing_features(include_failed=True)
        failed_count = len(failed_obs) - len(needing_extraction)
        extracted_count = total_obs - len(needing_extraction)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Observations", total_obs)
        c2.metric("Extracted", extracted_count)
        c3.metric("Pending", len(needing_extraction))
        c4.metric("Failed", failed_count)

        col_b1, col_b2 = st.columns(2)
        with col_b1:
            if st.button("Run Batch Feature Extraction", width="stretch", disabled=len(needing_extraction) == 0):
                p_bar = st.progress(0.1, text="Extracting Roslyn metrics...")

                def on_feat_prog(msg: str, pct: float) -> None:
                    p_bar.progress(pct, text=msg)

                extractor.batch_extract(progress_callback=on_feat_prog)
                st.rerun()

        with col_b2:
            if st.button("Re-Extract All Observations", width="stretch", disabled=total_obs == 0):
                p_bar = st.progress(0.1, text="Re-extracting Roslyn metrics...")

                def on_feat_prog2(msg: str, pct: float) -> None:
                    p_bar.progress(pct, text=msg)

                extractor.batch_extract(force=True, progress_callback=on_feat_prog2)
                st.rerun()

    # TAB 2: Dataset Overview
    with tab2:
        st.subheader("Versioned Dataset Snapshots")
        datasets = db.list_datasets()
        if datasets:
            df_ds = pd.DataFrame(datasets)[
                ["id", "name", "version", "total_count", "buggy_count", "non_buggy_count", "uncertain_count", "created_at"]
            ]
            st.dataframe(df_ds, hide_index=True, width="stretch")
        else:
            st.caption("No dataset snapshots recorded.")

        st.subheader("Observation Pool Breakdown")
        obs_records = db.list_observations()
        if obs_records:
            df_obs = pd.DataFrame(obs_records)
            col_o1, col_o2 = st.columns(2)
            with col_o1:
                label_df = pd.DataFrame([
                    {"Class": "Defect-Prone (1)", "Count": int((df_obs["label"] == 1).sum())},
                    {"Class": "Candidate-Clean (0)", "Count": int((df_obs["label"] == 0).sum())},
                    {"Class": "Uncertain (-1)", "Count": int((df_obs["label"] == -1).sum())},
                ])
                label_df["Share"] = (label_df["Count"] / len(df_obs) * 100).round(1).astype(str) + "%"
                st.table(label_df)
            with col_o2:
                ev_df = df_obs["evidence_category"].value_counts().reset_index()
                ev_df.columns = ["Evidence Category", "Count"]
                st.table(ev_df)
        else:
            st.caption("No observations recorded.")

    # TAB 3: Metric Distributions
    with tab3:
        st.subheader("Static Code Metric Analysis")
        st.caption("Statistical associations between code metrics and defect labels reflect historical patterns, not direct causality.")

        query_sql = """
        SELECT o.label, f.*
        FROM observations o
        JOIN features f ON o.id = f.observation_id
        WHERE f.status = 'success' AND o.label != -1
        """
        with db.db.session() as conn:
            feat_rows = conn.execute(query_sql).fetchall()

        if not feat_rows:
            st.warning("No extracted feature records found. Run feature extraction in Tab 1 first.")
        else:
            df_feat = pd.DataFrame([dict(r) for r in feat_rows])
            df_feat["Label_Text"] = df_feat["label"].map({1: "Defect-Prone (1)", 0: "Candidate-Clean (0)"})

            col_s1, col_s2 = st.columns([1, 2])
            available_metrics = [m for m in DEFAULT_NUMERICAL_FEATURES if m in df_feat.columns]

            with col_s1:
                default_idx = available_metrics.index("cyclomatic_complexity") if "cyclomatic_complexity" in available_metrics else 0
                selected_metric = st.selectbox("Metric", available_metrics, index=default_idx)
                desc_df = df_feat[selected_metric].describe().reset_index()
                desc_df.columns = ["Statistic", "Value"]
                desc_df["Value"] = desc_df["Value"].round(3)
                st.table(desc_df)

            with col_s2:
                fig_box = px.box(
                    df_feat,
                    x="Label_Text",
                    y=selected_metric,
                    color="Label_Text",
                    title=f"Distribution of {selected_metric} by Class",
                    color_discrete_map={"Defect-Prone (1)": "#4a7bb0", "Candidate-Clean (0)": "#5b9e78"},
                )
                fig_box.update_layout(showlegend=False, margin=dict(l=20, r=20, t=40, b=20))
                st.plotly_chart(fig_box, width="stretch")

            with st.expander("Metric Correlation Matrix (Pearson r)"):
                corr_features = [
                    "loc",
                    "cyclomatic_complexity",
                    "max_nesting_depth",
                    "parameter_count",
                    "statement_count",
                    "loop_count",
                    "method_call_count",
                    "assignment_count",
                ]
                available_corr = [c for c in corr_features if c in df_feat.columns]
                if len(available_corr) >= 2:
                    corr_matrix = df_feat[available_corr].corr().round(2)
                    fig_corr = px.imshow(
                        corr_matrix,
                        text_auto=True,
                        aspect="auto",
                        color_continuous_scale="Blues",
                    )
                    st.plotly_chart(fig_corr, width="stretch")

    # TAB 4: Snapshots & CSV Export
    with tab4:
        st.subheader("Create Versioned Dataset Snapshot")

        col_sn1, col_sn2 = st.columns(2)
        with col_sn1:
            snap_name = st.text_input("Snapshot name", value="csharp_methods_dataset")
            snap_version = st.text_input("Version tag", value="1.0.0")
        with col_sn2:
            snap_desc = st.text_area("Description", value="Balanced C# method static metrics dataset.")

        exclude_uncert = st.checkbox("Exclude uncertain observations (Label = -1)", value=True)

        with st.expander("Feature Selection (26 Metrics)"):
            selected_metrics = st.multiselect(
                "Included features",
                options=DEFAULT_NUMERICAL_FEATURES,
                default=DEFAULT_NUMERICAL_FEATURES,
            )

        if st.button("Build Dataset Snapshot", width="stretch"):
            try:
                builder.generate_dataset_snapshot(
                    name=snap_name,
                    version=snap_version,
                    description=snap_desc,
                    exclude_uncertain=exclude_uncert,
                    feature_names=selected_metrics,
                )
                st.rerun()
            except Exception as e:
                st.error(f"Snapshot creation failed: {e}")

        st.subheader("Export Snapshot")
        datasets_list = db.list_datasets()
        if not datasets_list:
            st.caption("No datasets available to export.")
        else:
            ds_choices = {f"#{d['id']}: {d['name']} (v{d['version']} - {d['total_count']} items)": d["id"] for d in datasets_list}
            chosen_label = st.selectbox("Snapshot to export", list(ds_choices.keys()))
            chosen_id = ds_choices[chosen_label]

            col_exp1, col_exp2 = st.columns(2)
            with col_exp1:
                if st.button("Export to Disk", width="stretch"):
                    try:
                        exp_res = exporter.export_to_csv(chosen_id, overwrite=True)
                        st.caption(f"Exported {exp_res['rows_exported']} rows to `{exp_res['csv_path']}`.")
                    except Exception as e:
                        st.error(f"Export failed: {e}")

            with col_exp2:
                records = db.get_dataset_dataframe_records(chosen_id)
                if records:
                    csv_bytes = pd.DataFrame(records).to_csv(index=False).encode("utf-8")
                    st.download_button(
                        label="Download CSV",
                        data=csv_bytes,
                        file_name=f"dataset_{chosen_id}.csv",
                        mime="text/csv",
                        width="stretch",
                    )

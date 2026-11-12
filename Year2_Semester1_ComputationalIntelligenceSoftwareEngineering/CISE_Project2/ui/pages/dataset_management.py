"""Dataset Management Page: Feature Extraction, Overview, Statistical Analysis, and Versioned CSV Export."""
from __future__ import annotations

import json
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.figure_factory as ff
import streamlit as st

from config.settings import AppSettings
from src.database.repository import RepositoryDB
from src.dataset.feature_extractor import FeatureExtractor
from src.dataset.dataset_builder import DatasetBuilder, DEFAULT_NUMERICAL_FEATURES
from src.dataset.exporter import DatasetExporter


def render_dataset_management(db: RepositoryDB, settings: AppSettings) -> None:
    st.header("📁 Dataset Management, Feature Engineering & Versioning")
    st.markdown("""
    Extract 24 Roslyn static code metrics from method observations, audit distributions,
    inspect feature correlations, and build reproducible, versioned ML datasets for training.
    """)

    extractor = FeatureExtractor(db)
    builder = DatasetBuilder(db)
    exporter = DatasetExporter(db, settings.storage.exports_dir)

    tab1, tab2, tab3, tab4 = st.tabs([
        "⚡ Feature Extraction",
        "📊 Dataset Overview",
        "📈 Feature Analysis & Distributions",
        "💾 Dataset Snapshots & CSV Export",
    ])

    # -------------------------------------------------------------
    # TAB 1: Feature Extraction
    # -------------------------------------------------------------
    with tab1:
        st.subheader("1. Extract Roslyn Static Code Metrics")
        st.caption("Parses method syntax trees using Microsoft.CodeAnalysis to calculate structural, complexity, and OOP metrics.")

        all_obs = db.list_observations()
        total_obs = len(all_obs)
        needing_extraction = db.get_observations_needing_features(include_failed=False)
        failed_obs = db.get_observations_needing_features(include_failed=True)
        failed_count = len(failed_obs) - len(needing_extraction)
        extracted_count = total_obs - len(needing_extraction)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Observations", total_obs)
        c2.metric("Features Extracted", extracted_count)
        c3.metric("Awaiting Extraction", len(needing_extraction))
        c4.metric("Failed Extractions", failed_count)

        st.markdown(f"**Analyzer Engine:** `Microsoft.CodeAnalysis.CSharp` v4.12.0 (.NET 9.0) | **Analyzer Version:** `{FeatureExtractor.ANALYZER_VERSION}`")

        col_b1, col_b2 = st.columns([1, 1])
        with col_b1:
            if st.button("🚀 Run Batch Feature Extraction", use_container_width=True, disabled=len(needing_extraction) == 0):
                p_bar = st.progress(0.1, text="Extracting Roslyn metrics...")
                def on_feat_prog(msg: str, pct: float) -> None:
                    p_bar.progress(pct, text=msg)

                res = extractor.batch_extract(progress_callback=on_feat_prog)
                st.success(f"Feature extraction completed: {res['success']} succeeded, {res['failed']} failed.")
                st.rerun()

        with col_b2:
            if st.button("🔄 Force Re-Extract All Observations", use_container_width=True, disabled=total_obs == 0):
                p_bar = st.progress(0.1, text="Re-extracting all Roslyn metrics...")
                def on_feat_prog2(msg: str, pct: float) -> None:
                    p_bar.progress(pct, text=msg)

                res = extractor.batch_extract(force=True, progress_callback=on_feat_prog2)
                st.success(f"Re-extracted metrics: {res['success']} succeeded, {res['failed']} failed.")
                st.rerun()

    # -------------------------------------------------------------
    # TAB 2: Dataset Overview
    # -------------------------------------------------------------
    with tab2:
        st.subheader("2. Dataset Snapshots & Observations Summary")
        datasets = db.list_datasets()

        if datasets:
            st.markdown("### Versioned Dataset Snapshots")
            df_ds = pd.DataFrame(datasets)[["id", "name", "version", "total_count", "buggy_count", "non_buggy_count", "uncertain_count", "created_at"]]
            st.dataframe(df_ds, use_container_width=True)
        else:
            st.info("No dataset snapshots created yet. Use Tab 4 to create a snapshot.")

        st.markdown("---")
        st.markdown("### Observations Pool Breakdown")
        obs_records = db.list_observations()
        if obs_records:
            df_obs = pd.DataFrame(obs_records)
            col_o1, col_o2 = st.columns(2)
            with col_o1:
                label_counts = df_obs["label"].value_counts().rename({1: "Buggy (1)", 0: "Candidate Clean (0)", -1: "Uncertain (-1)"})
                fig_pie = px.pie(
                    values=label_counts.values,
                    names=label_counts.index,
                    title="Defect Label Distribution",
                    color_discrete_sequence=["#e74c3c", "#2ecc71", "#f39c12"],
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            with col_o2:
                st.markdown("**Evidence Categories:**")
                ev_counts = df_obs["evidence_category"].value_counts()
                st.dataframe(ev_counts, use_container_width=True)
        else:
            st.info("No observations recorded yet.")

    # -------------------------------------------------------------
    # TAB 3: Feature Analysis & Distributions
    # -------------------------------------------------------------
    with tab3:
        st.subheader("3. Static Code Metric Statistical Analysis")
        st.caption("Inspect distributions, correlations, and differences between buggy and clean methods.")

        # Pull all observations with features
        query_sql = """
        SELECT o.label, f.*
        FROM observations o
        JOIN features f ON o.id = f.observation_id
        WHERE f.status = 'success' AND o.label != -1
        """
        with db.db.session() as conn:
            feat_rows = conn.execute(query_sql).fetchall()

        if not feat_rows:
            st.warning("No successful feature records found. Please run Feature Extraction in Tab 1 first.")
        else:
            df_feat = pd.DataFrame([dict(r) for r in feat_rows])
            df_feat["Label_Text"] = df_feat["label"].map({1: "Buggy (1)", 0: "Candidate Clean (0)"})

            st.info("⚠️ **Notice:** Statistical correlations between code metrics and defect labels describe historical patterns and do NOT establish direct causality.")

            col_s1, col_s2 = st.columns([1, 2])
            available_metrics = [m for m in DEFAULT_NUMERICAL_FEATURES if m in df_feat.columns]

            with col_s1:
                selected_metric = st.selectbox("Select Metric to Inspect", available_metrics, index=available_metrics.index("cyclomatic_complexity") if "cyclomatic_complexity" in available_metrics else 0)
                st.markdown(f"**Descriptive Statistics for `{selected_metric}`:**")
                st.dataframe(df_feat[selected_metric].describe(), use_container_width=True)

            with col_s2:
                fig_box = px.box(
                    df_feat,
                    x="Label_Text",
                    y=selected_metric,
                    color="Label_Text",
                    title=f"Distribution of '{selected_metric}' by Label",
                    color_discrete_map={"Buggy (1)": "#e74c3c", "Candidate Clean (0)": "#2ecc71"},
                )
                st.plotly_chart(fig_box, use_container_width=True)

            st.markdown("---")
            st.subheader("Metric Correlation Heatmap")
            corr_features = ["loc", "cyclomatic_complexity", "max_nesting_depth", "parameter_count", "statement_count", "loop_count", "method_call_count", "assignment_count"]
            available_corr = [c for c in corr_features if c in df_feat.columns]
            if len(available_corr) >= 2:
                corr_matrix = df_feat[available_corr].corr().round(2)
                fig_corr = px.imshow(
                    corr_matrix,
                    text_auto=True,
                    aspect="auto",
                    title="Feature Correlation Matrix (Pearson r)",
                    color_continuous_scale="Blues",
                )
                st.plotly_chart(fig_corr, use_container_width=True)

    # -------------------------------------------------------------
    # TAB 4: Dataset Snapshots & CSV Export
    # -------------------------------------------------------------
    with tab4:
        st.subheader("4. Generate Reproducible Dataset Snapshot & Export")

        col_sn1, col_sn2 = st.columns(2)
        with col_sn1:
            snap_name = st.text_input("Dataset Snapshot Name", value="csharp_methods_dataset")
            snap_version = st.text_input("Version Tag", value="1.0.0")
        with col_sn2:
            snap_desc = st.text_area("Description", value="Balanced C# method static metrics dataset generated via SZZ.")

        exclude_uncert = st.checkbox("Exclude Uncertain Observations (Label = -1)", value=True, help="Removes ambiguous observations to keep supervised training pure.")

        with st.expander("Feature Selection (24 Metrics)", expanded=False):
            selected_metrics = st.multiselect(
                "Features to include in ML matrix",
                options=DEFAULT_NUMERICAL_FEATURES,
                default=DEFAULT_NUMERICAL_FEATURES,
            )

        if st.button("🔨 Build Versioned Dataset Snapshot", use_container_width=True):
            try:
                ds_id, stats = builder.generate_dataset_snapshot(
                    name=snap_name,
                    version=snap_version,
                    description=snap_desc,
                    exclude_uncertain=exclude_uncert,
                    feature_names=selected_metrics,
                )
                st.success(
                    f"Created Dataset Snapshot #{ds_id} ('{snap_name}' v{snap_version})! "
                    f"Total: {stats['total_observations']} (Buggy: {stats['buggy_count']}, Clean: {stats['clean_count']}, Excluded: {stats['uncertain_excluded']})"
                )
                st.rerun()
            except Exception as e:
                st.error(f"Snapshot build failed: {e}")

        st.markdown("---")
        st.subheader("Export Snapshot to CSV & Metadata JSON")

        datasets_list = db.list_datasets()
        if not datasets_list:
            st.info("No datasets available to export. Create a snapshot above.")
        else:
            ds_choices = {f"#{d['id']}: {d['name']} (v{d['version']} - {d['total_count']} items)": d["id"] for d in datasets_list}
            chosen_label = st.selectbox("Select Snapshot to Export", list(ds_choices.keys()))
            chosen_id = ds_choices[chosen_label]

            col_exp1, col_exp2 = st.columns(2)
            with col_exp1:
                if st.button("📁 Export to Local Disk (exports/)", use_container_width=True):
                    try:
                        exp_res = exporter.export_to_csv(chosen_id, overwrite=True)
                        st.success(f"Exported {exp_res['rows_exported']} rows to `{exp_res['csv_path']}` and metadata to `{exp_res['metadata_path']}`!")
                    except Exception as e:
                        st.error(f"Export failed: {e}")

            with col_exp2:
                # Provide direct browser download button
                records = db.get_dataset_dataframe_records(chosen_id)
                if records:
                    csv_bytes = pd.DataFrame(records).to_csv(index=False).encode("utf-8")
                    st.download_button(
                        label="⬇️ Download CSV Directly",
                        data=csv_bytes,
                        file_name=f"dataset_{chosen_id}.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )

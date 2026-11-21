"""Dataset Management Page: Class-Level Feature Extraction, Distributions, and Versioned Export."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from core.settings import AppSettings
from database.repository import CLASS_FEATURE_NAMES, RepositoryDB
from services.dataset.feature_extractor import FeatureExtractor
from services.dataset.dataset_builder import DatasetBuilder, DEFAULT_NUMERICAL_FEATURES
from services.dataset.exporter import DatasetExporter


def render_dataset_management(db: RepositoryDB, settings: AppSettings) -> None:
    st.title("Dataset Management")
    st.caption("Inspect class-level and preserved method-level datasets, Roslyn metric distributions, and manifests.")

    extractor = FeatureExtractor(db)
    builder = DatasetBuilder(db)
    exporter = DatasetExporter(db, settings.storage.exports_dir)

    tab1, tab2, tab3, tab4 = st.tabs([
        "Class Feature Extraction",
        "Dataset Snapshots & Repositories",
        "Metric Distributions",
        "Snapshot Builder & Export",
    ])

    # TAB 1: Feature Extraction
    with tab1:
        st.subheader("Roslyn Class-Level Static Metric Extraction (40 Features)")
        st.caption(f"Analyzer: Microsoft.CodeAnalysis.CSharp (.NET 9.0) v{FeatureExtractor.ANALYZER_VERSION} | Schema v{FeatureExtractor.CLASS_SCHEMA_VERSION}")

        all_cls_obs = db.list_class_observations()
        total_cls = len(all_cls_obs)
        needing_ext = db.get_class_observations_needing_features(include_failed=False)
        failed_obs = db.get_class_observations_needing_features(include_failed=True)
        failed_cnt = len(failed_obs) - len(needing_ext)
        extracted_cnt = total_cls - len(needing_ext)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Class Observations", total_cls)
        c2.metric("Extracted", extracted_cnt)
        c3.metric("Pending", len(needing_ext))
        c4.metric("Failed", failed_cnt)

        cb1, cb2 = st.columns(2)
        with cb1:
            if st.button("Extract Pending Class Features", width="stretch", disabled=len(needing_ext) == 0):
                p_bar = st.progress(0.1, text="Running Roslyn class analyzer...")
                extractor.batch_extract_classes(progress_callback=lambda msg, pct: p_bar.progress(pct, text=msg))
                st.rerun()
        with cb2:
            if st.button("Re-Extract All Class Features", width="stretch", disabled=total_cls == 0):
                p_bar = st.progress(0.1, text="Re-extracting Roslyn class metrics...")
                extractor.batch_extract_classes(force=True, progress_callback=lambda msg, pct: p_bar.progress(pct, text=msg))
                st.rerun()

    # TAB 2: Dataset Snapshots & Repository Distribution
    with tab2:
        st.subheader("Versioned Dataset Snapshots")
        datasets = db.list_datasets()
        if datasets:
            cols = [c for c in ["id", "name", "version", "granularity", "repository_count", "total_count", "buggy_count", "non_buggy_count", "created_at"] if c in datasets[0]]
            st.dataframe(pd.DataFrame(datasets)[cols], hide_index=True, width="stretch")

            ds_map = {f"#{d['id']}: {d['name']} (v{d['version']} | {d.get('granularity', 'method')})": d["id"] for d in datasets}
            chosen = st.selectbox("Inspect Repository Distribution for Dataset", list(ds_map.keys()))
            ds_id = ds_map[chosen]
            ds_stats = builder.compute_dataset_statistics(ds_id, [])
            repo_dist = ds_stats.get("repository_distribution", {})
            if repo_dist:
                st.caption(f"Repositories included: {len(repo_dist)} | Defect-prone: {ds_stats.get('buggy_count', 0)} | Candidate-clean: {ds_stats.get('clean_count', 0)}")
                dist_df = pd.DataFrame([{"Repository": k, "Observations": v} for k, v in sorted(repo_dist.items(), key=lambda x: x[1], reverse=True)])
                st.dataframe(dist_df, hide_index=True, width="stretch")
        else:
            st.caption("No dataset snapshots recorded.")

    # TAB 3: Metric Distributions
    with tab3:
        st.subheader("Class-Level Metric Analysis")
        st.caption("Associations between static structural metrics and historical defect labels do not imply direct causality.")

        rows = db.list_class_observations_with_features(exclude_uncertain=True)
        if not rows:
            st.warning("No extracted class feature records found. Run collection or batch extraction first.")
        else:
            df_feat = pd.DataFrame(rows)
            df_feat["Label_Text"] = df_feat["label"].map({1: "Defect-Prone Class (1)", 0: "Candidate-Clean Class (0)"})
            avail = [f for f in CLASS_FEATURE_NAMES if f in df_feat.columns]

            col_s1, col_s2 = st.columns([1, 2])
            with col_s1:
                def_idx = avail.index("total_cyclomatic_complexity") if "total_cyclomatic_complexity" in avail else 0
                selected_metric = st.selectbox("Class Metric", avail, index=def_idx)
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
                    title=f"Distribution of {selected_metric} by Class Label",
                    color_discrete_map={"Defect-Prone Class (1)": "#4a7bb0", "Candidate-Clean Class (0)": "#5b9e78"},
                )
                fig_box.update_layout(showlegend=False, margin=dict(l=20, r=20, t=40, b=20))
                st.plotly_chart(fig_box, width="stretch")

    # TAB 4: Snapshots & Export
    with tab4:
        st.subheader("Create Versioned Class Dataset Snapshot")
        col_sn1, col_sn2 = st.columns(2)
        with col_sn1:
            snap_name = st.text_input("Snapshot name", value="csharp_class_custom")
            snap_version = st.text_input("Version tag", value="3.1.0")
        with col_sn2:
            snap_desc = st.text_area("Description", value="Deduplicated class-level C# defect detection snapshot.")

        selected_metrics = st.multiselect("Included 40 class features", options=CLASS_FEATURE_NAMES, default=CLASS_FEATURE_NAMES)
        if st.button("Build Class Dataset Snapshot", width="stretch"):
            try:
                builder.generate_class_dataset_snapshot(
                    name=snap_name,
                    version=snap_version,
                    description=snap_desc,
                    feature_names=selected_metrics,
                    overwrite=True,
                )
                st.rerun()
            except Exception as e:
                st.error(f"Snapshot creation failed: {e}")

        st.subheader("Export Snapshot & Manifest")
        datasets_list = db.list_datasets()
        if datasets_list:
            ds_choices = {f"#{d['id']}: {d['name']} (v{d['version']} - {d['total_count']} items)": d["id"] for d in datasets_list}
            chosen_id = ds_choices[st.selectbox("Snapshot to export", list(ds_choices.keys()))]
            col_exp1, col_exp2 = st.columns(2)
            with col_exp1:
                if st.button("Export CSV + Manifest to Disk", width="stretch"):
                    try:
                        exp_res = exporter.export_to_csv(chosen_id, overwrite=True)
                        st.caption(f"Exported {exp_res['rows_exported']} rows to `{exp_res['csv_path']}` (SHA-256: `{exp_res['sha256_checksum'][:12]}...`).")
                    except Exception as e:
                        st.error(f"Export failed: {e}")
            with col_exp2:
                records = db.get_dataset_dataframe_records(chosen_id)
                if records:
                    st.download_button(
                        label="Download CSV",
                        data=pd.DataFrame(records).to_csv(index=False).encode("utf-8"),
                        file_name=f"dataset_{chosen_id}.csv",
                        mime="text/csv",
                        width="stretch",
                    )

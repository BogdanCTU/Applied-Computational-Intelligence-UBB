"""Bug Analysis Page: Bug-Fix Detection, SZZ Localization, and Class-Level Label Auditing."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from core.settings import AppSettings
from database.repository import RepositoryDB
from services.mining.bug_fix_detector import BugFixDetector
from services.mining.szz_analyzer import SZZAnalyzer
from services.labeling.label_manager import LabelManager


def render_bug_analysis(db: RepositoryDB, settings: AppSettings) -> None:
    st.title("Bug Analysis and SZZ Attribution")
    st.caption("Inspect heuristic bug-fixing commits, SZZ line-blame traces, and class-level defect provenance.")

    repos = db.list_repositories()
    cloned_repos = [r for r in repos if r["is_cloned"] and r.get("local_path")]

    if not cloned_repos:
        st.warning("No cloned repositories available. Clone a repository in Repository Collection first.")
        return

    repo_options = {f"{r['full_name']} (ID: {r['id']} | Classes: {r.get('class_observations_count', 0)})": r for r in cloned_repos}
    selected_label = st.selectbox("Target Repository", list(repo_options.keys()))
    selected_repo = repo_options[selected_label]
    repo_id = selected_repo["id"]
    local_path = selected_repo["local_path"]

    bug_detector = BugFixDetector(db=db)
    szz_analyzer = SZZAnalyzer(db=db)
    label_mgr = LabelManager(db=db)

    tab1, tab2, tab3, tab4 = st.tabs([
        "Bug-Fixing Commits",
        "SZZ Defect Localization",
        "Class Observations (Primary)",
        "Legacy Method Observations",
    ])

    # TAB 1: Bug-Fixing Commits
    with tab1:
        st.subheader("Bug-Fixing Commit Detection")
        col_d1, col_d2, col_d3 = st.columns([2, 1, 1])
        with col_d1:
            threshold = st.slider("Confidence threshold", 0.30, 0.90, 0.50, 0.05)
        with col_d2:
            strict_mode = st.checkbox("Strict class-mining filters", value=True)
        with col_d3:
            if st.button("Run Bug-Fix Detector", width="stretch"):
                with st.spinner("Analyzing repository commits..."):
                    bug_detector.detect_in_repository(repo_id, threshold=threshold, force=True, strict_mode=strict_mode)
                    st.rerun()

        filter_col1, filter_col2 = st.columns([1, 2])
        with filter_col1:
            filter_mode = st.radio("Display filter", ["Bug Fixes Only", "All Commits"])
        with filter_col2:
            search_kw = st.text_input("Filter commit message", placeholder="null, crash, #123")

        commits = db.list_commits(repository_id=repo_id, bug_fix_only=(filter_mode == "Bug Fixes Only"), limit=300)
        if search_kw:
            commits = [c for c in commits if search_kw.lower() in (c["message"] or "").lower()]

        if commits:
            st.caption(f"Matching commits: {len(commits)}")
            commits_summary = pd.DataFrame(commits[:100])[
                ["commit_sha", "committed_date", "author_name", "is_bug_fix", "bug_fix_confidence", "review_status", "message"]
            ]
            st.dataframe(commits_summary, hide_index=True, width="stretch")

            for c in commits[:15]:
                cid = c["id"]
                sha = c["commit_sha"]
                tag = "BUG FIX" if c["is_bug_fix"] == 1 else "REGULAR"
                conf = c.get("bug_fix_confidence", 0.0)
                with st.expander(f"[{tag}] {sha[:8]} (Confidence: {conf:.2f}) — {(c['message'] or '').splitlines()[0][:80]}"):
                    st.code(c["message"] or "", language="text")
                    st.caption(f"Evidence: {c.get('bug_fix_evidence') or 'N/A'}")
                    cb1, cb2, cb3 = st.columns(3)
                    if cb1.button("Confirm Bug Fix", key=f"conf_fix_{cid}", width="stretch"):
                        db.update_commit_review_status(cid, "confirmed", is_bug_fix=True)
                        st.rerun()
                    if cb2.button("Reject Bug Fix", key=f"rej_fix_{cid}", width="stretch"):
                        db.update_commit_review_status(cid, "rejected", is_bug_fix=False)
                        st.rerun()
                    if cb3.button("Reset Review", key=f"rst_fix_{cid}", width="stretch"):
                        db.update_commit_review_status(cid, "unreviewed", is_bug_fix=None)
                        st.rerun()
        else:
            st.caption("No commits match filter criteria.")

    # TAB 2: SZZ Analysis
    with tab2:
        st.subheader("SZZ Line-Blame Tracing")
        st.caption("Traces deleted or modified production C# lines in fixing commits via git blame (-w -M -C).")
        if st.button("Run SZZ Algorithm", width="stretch"):
            p_bar = st.progress(0.1, text="Running SZZ blame analysis...")
            try:
                szz_analyzer.run_repository_szz(
                    repository_id=repo_id,
                    local_path=local_path,
                    progress_callback=lambda msg, pct: p_bar.progress(pct, text=msg),
                )
                st.rerun()
            except Exception as e:
                st.error(f"SZZ analysis failed: {e}")

        traces = db.list_szz_results(repository_id=repo_id)
        if traces:
            st.caption(f"Total SZZ traces: {len(traces)}")
            df_traces = pd.DataFrame(traces)[
                ["fixing_commit_sha", "inducing_commit_sha", "file_path", "deleted_line_number", "deleted_line_content", "confidence"]
            ]
            st.dataframe(df_traces, hide_index=True, width="stretch")
        else:
            st.caption("No SZZ traces recorded for this repository.")

        locs = db.list_class_bug_localizations(repository_id=repo_id)
        if locs:
            st.subheader("Verified Historical Class & Method Localizations")
            st.dataframe(
                pd.DataFrame(locs)[
                    ["qualified_class_name", "method_name", "method_start_line", "method_end_line", "affected_line_ranges_json", "localization_status", "bug_fix_commit_sha"]
                ],
                hide_index=True,
                width="stretch",
            )

    # TAB 3: Class Observations (Primary)
    with tab3:
        st.subheader("Class-Level Observation Extraction & Attribution")
        st.caption("Maps SZZ traces to enclosing classes (Label 1) and samples untouched HEAD classes (Label 0).")

        col_m1, col_m2 = st.columns(2)
        with col_m1:
            if st.button("Extract Defect-Prone Classes (Label 1)", width="stretch"):
                with st.spinner("Mapping SZZ traces to enclosing C# classes..."):
                    label_mgr.create_class_observations_from_szz(repo_id, local_path)
                    st.rerun()
        with col_m2:
            clean_count = st.number_input("Candidate-clean class sample limit", min_value=5, max_value=100, value=25, step=5)
            if st.button("Sample Candidate-Clean Classes (Label 0)", width="stretch"):
                with st.spinner("Sampling candidate-clean classes from HEAD..."):
                    label_mgr.sample_candidate_clean_classes(repo_id, local_path, target_count=int(clean_count))
                    st.rerun()

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            label_filter = st.selectbox("Filter by label", ["All", "Defect-Prone (1)", "Candidate-Clean (0)", "Uncertain (-1)"], key="cls_lbl_flt")
        with col_f2:
            class_search = st.text_input("Filter by class or file", placeholder="Validator, Parser")

        target_label = {"Defect-Prone (1)": 1, "Candidate-Clean (0)": 0, "Uncertain (-1)": -1}.get(label_filter)
        cls_obs = db.list_class_observations(repository_id=repo_id, label=target_label)
        if class_search:
            cls_obs = [
                o for o in cls_obs
                if class_search.lower() in o["qualified_class_name"].lower() or class_search.lower() in o["file_path"].lower()
            ]

        if cls_obs:
            st.caption(f"Class observations: {len(cls_obs)} (showing top 15 expandable records)")
            cls_summary = pd.DataFrame(cls_obs)[
                ["id", "qualified_class_name", "type_kind", "file_path", "start_line", "end_line", "label", "szz_trace_count", "evidence_category"]
            ]
            st.dataframe(cls_summary, hide_index=True, width="stretch")

            for obs in cls_obs[:15]:
                oid = obs["id"]
                lbl = obs["label"]
                tag = "DEFECT-PRONE (1)" if lbl == 1 else ("CANDIDATE-CLEAN (0)" if lbl == 0 else "UNCERTAIN (-1)")
                with st.expander(f"[{tag}] {obs['qualified_class_name']} ({obs['file_path']} L{obs['start_line']}-L{obs['end_line']})"):
                    st.caption(
                        f"Evidence: {obs['evidence_category']} | SZZ traces: {obs.get('szz_trace_count', 0)} | "
                        f"Fix Commit: {obs.get('bug_fix_commit_sha') or 'None'} | BIC: {obs.get('bug_inducing_commit_sha') or 'None'}"
                    )
                    c1, c2 = st.columns(2)
                    with c1:
                        st.caption("Pre-fix or sampled class source:")
                        st.code(obs["source_code"][:4000], language="csharp")
                    with c2:
                        st.caption("Post-fix source:")
                        if obs.get("corrected_code"):
                            st.code(obs["corrected_code"][:4000], language="csharp")
                        else:
                            st.caption("Not applicable.")

                    ca1, ca2, ca3 = st.columns(3)
                    if ca1.button("Label 1 (Defect-Prone)", key=f"cobs_bug_{oid}", width="stretch"):
                        db.update_class_observation_label(oid, 1, "manual_override_buggy")
                        st.rerun()
                    if ca2.button("Label 0 (Candidate-Clean)", key=f"cobs_clean_{oid}", width="stretch"):
                        db.update_class_observation_label(oid, 0, "manual_override_clean")
                        st.rerun()
                    if ca3.button("Label -1 (Uncertain)", key=f"cobs_uncert_{oid}", width="stretch"):
                        label_mgr.mark_class_observation_uncertain(oid, "manual_override_uncertain")
                        st.rerun()
        else:
            st.caption("No class observations match the filter.")

    # TAB 4: Legacy Method Observations
    with tab4:
        st.subheader("Historical Method-Level Observations (Preserved)")
        method_obs = db.list_observations(repository_id=repo_id)
        if method_obs:
            st.dataframe(
                pd.DataFrame(method_obs)[["id", "class_name", "method_name", "file_path", "label", "evidence_category"]],
                hide_index=True,
                width="stretch",
            )
        else:
            st.caption("No legacy method observations for this repository.")

"""Repository Collection Page: Paginated GitHub Discovery, Resumable 100+ Collection, and Repo Operations."""
from __future__ import annotations

import json
import re
from pathlib import Path
import pandas as pd
import streamlit as st

from core.settings import AppSettings
from repositories.github_client import GitHubClient, GitHubAPIError, RateLimitExceededError
from repositories.repository_manager import RepositoryManager, RepositoryManagerError
from repositories.commit_collector import CommitCollector
from database.repository import RepositoryDB


def parse_github_url(url: str) -> tuple[str, str]:
    """Extract owner and repository name from a GitHub URL or owner/repo string."""
    cleaned = url.strip().rstrip("/")
    if cleaned.endswith(".git"):
        cleaned = cleaned[:-4]

    pattern = r"(?:https?://github\.com/)?([^/\s]+)/([^/\s]+)$"
    match = re.search(pattern, cleaned)
    if not match:
        raise ValueError(f"Invalid repository specification: '{url}'. Expected 'owner/repo' or 'https://github.com/owner/repo'.")
    return match.group(1), match.group(2)


def render_repository_collection(db: RepositoryDB, settings: AppSettings) -> None:
    st.title("Repository Collection")
    st.caption("Discover, rank, clone, and incrementally mine 100+ public C# repositories with resumable checkpoints.")

    gh_client = GitHubClient(token=settings.github.token)
    repo_mgr = RepositoryManager(settings.storage.repositories_dir, db=db)
    commit_collector = CommitCollector(db)

    tab1, tab2, tab3, tab4 = st.tabs([
        "Batch Discovery (100+)",
        "Collection Runs & Progress",
        "Manual Import",
        "Managed Repositories",
    ])

    # TAB 1: GitHub Discovery
    with tab1:
        st.subheader("Paginated GitHub C# Repository Discovery & Ranking")
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        with col1:
            keywords = st.text_input("Keywords or topic (optional)", placeholder="parser, serialization, orm")
        with col2:
            min_stars = st.number_input("Min stars", min_value=10, value=settings.collection.min_stars, step=25)
        with col3:
            min_size_kb = st.number_input("Min size (KB)", min_value=50, value=settings.collection.min_repo_size_kb, step=50)
        with col4:
            target_disc = st.number_input("Discovery target", min_value=15, max_value=300, value=120, step=15)

        col_opts1, col_opts2 = st.columns(2)
        with col_opts1:
            exclude_forks = st.checkbox("Exclude forks", value=True)
        with col_opts2:
            exclude_archived = st.checkbox("Exclude archived repositories", value=True)

        c_btn1, c_btn2 = st.columns(2)
        with c_btn1:
            if st.button("Discover & Rank C# Repositories", width="stretch"):
                with st.spinner("Querying GitHub Search API across stratified star bands..."):
                    try:
                        if keywords and keywords.strip():
                            res = gh_client.search_repositories(
                                keywords=keywords,
                                min_stars=min_stars,
                                min_size_kb=min_size_kb,
                                exclude_forks=exclude_forks,
                                exclude_archived=exclude_archived,
                                per_page=min(100, int(target_disc)),
                            )
                            st.session_state["search_results"] = res["items"]
                            st.caption(f"Discovered {res['total_count']} matching repositories (showing {len(res['items'])}).")
                        else:
                            disc = gh_client.discover_csharp_repositories(
                                target_count=int(target_disc),
                                min_stars=int(min_stars),
                                min_size_kb=int(min_size_kb),
                                max_size_kb=settings.collection.max_repo_size_kb,
                                exclude_forks=exclude_forks,
                                exclude_archived=exclude_archived,
                            )
                            st.session_state["search_results"] = disc["selected"]
                            st.caption(
                                f"Discovered {disc['discovered_total']} candidates | "
                                f"Selected {disc['selected_total']} | Excluded {disc['excluded_total']}"
                            )
                    except RateLimitExceededError as e:
                        st.error(f"GitHub API rate limit reached: {e}. Configure a GitHub token in Settings.")
                    except GitHubAPIError as e:
                        st.error(f"GitHub search error: {e}")

        with c_btn2:
            items = st.session_state.get("search_results", [])
            if st.button("Register All Discovered Candidates in DB", width="stretch", disabled=not items):
                registered_n = 0
                for repo_item in items:
                    db.upsert_repository({
                        "full_name": repo_item["full_name"],
                        "name": repo_item["name"],
                        "owner": repo_item["owner"],
                        "url": repo_item["url"],
                        "description": repo_item.get("description"),
                        "license": repo_item.get("license", "Unknown"),
                        "default_branch": repo_item.get("default_branch", "main"),
                        "stars": repo_item.get("stars", 0),
                        "forks": repo_item.get("forks", 0),
                        "size_kb": repo_item.get("size_kb", 0),
                        "selection_score": repo_item.get("selection_score", 0.0),
                        "selection_rank": repo_item.get("selection_rank"),
                        "selection_reason": repo_item.get("selection_reason"),
                        "is_selected": repo_item.get("is_selected", True),
                    })
                    registered_n += 1
                st.caption(f"Registered {registered_n} candidate repositories.")
                st.rerun()

        items = st.session_state.get("search_results", [])
        if items:
            st.subheader(f"Ranked Candidates ({len(items)})")
            cand_df = pd.DataFrame([
                {
                    "Rank": r.get("selection_rank", "-"),
                    "Repository": r["full_name"],
                    "Score": r.get("selection_score", 0.0),
                    "Stars": r.get("stars", 0),
                    "Size (KB)": r.get("size_kb", 0),
                    "License": r.get("license", "Unknown"),
                }
                for r in items[:100]
            ])
            st.dataframe(cand_df, hide_index=True, width="stretch")

    # TAB 2: Collection Runs & Resumable Progress
    with tab2:
        st.subheader("Multi-Repository Collection Status")
        runs = db.list_collection_runs()
        if runs:
            runs_df = pd.DataFrame(runs)[
                ["run_id", "target_repositories", "discovered_count", "selected_count", "processed_count", "excluded_count", "failed_count", "status", "started_at"]
            ]
            st.dataframe(runs_df, hide_index=True, width="stretch")
        else:
            st.caption("No batch collection runs logged in SQLite yet.")

        cp_path = settings.storage.processed_dir / "collection_checkpoint_v3.json"
        if cp_path.exists():
            cp = json.loads(cp_path.read_text(encoding="utf-8"))
            c_cp1, c_cp2, c_cp3, c_cp4 = st.columns(4)
            c_cp1.metric("Checkpoint Target", cp.get("target_repos", 100))
            c_cp2.metric("Processed OK", len(cp.get("processed", {})))
            c_cp3.metric("Excluded", len(cp.get("excluded", {})))
            c_cp4.metric("Failed", len(cp.get("failed", {})))

            if cp.get("excluded"):
                with st.expander("Excluded Repositories & Reasons"):
                    excl_rows = [{"Repository": k, "Reason": v.get("reason", "")} for k, v in cp["excluded"].items()]
                    st.dataframe(pd.DataFrame(excl_rows), hide_index=True, width="stretch")
        st.caption(
            "CLI command for resumable 100+ collection: "
            "`python 2_SourceCode/Scripts/run_100_repo_class_pipeline.py --target-repos 106`"
        )

    # TAB 3: Manual Import
    with tab3:
        st.subheader("Register Repository by URL")
        manual_url = st.text_input("Repository URL or slug", placeholder="https://github.com/owner/repository")
        clone_immediately = st.checkbox("Clone repository history immediately", value=True)

        if st.button("Register Repository", width="stretch"):
            if not manual_url:
                st.warning("Provide a repository URL or owner/repository slug.")
            else:
                try:
                    owner, name = parse_github_url(manual_url)
                    full_name = f"{owner}/{name}"

                    try:
                        meta = gh_client.get_repository(owner, name)
                    except Exception:
                        meta = {
                            "description": "Manually registered repository",
                            "license": "Unknown",
                            "default_branch": "main",
                            "stars": 0,
                            "forks": 0,
                            "size_kb": 0,
                            "clone_url": f"https://github.com/{full_name}.git",
                        }

                    repo_id = db.upsert_repository({
                        "full_name": full_name,
                        "name": name,
                        "owner": owner,
                        "url": f"https://github.com/{full_name}",
                        "description": meta.get("description"),
                        "license": meta.get("license", "Unknown"),
                        "default_branch": meta.get("default_branch", "main"),
                        "stars": meta.get("stars", 0),
                        "forks": meta.get("forks", 0),
                        "size_kb": meta.get("size_kb", 0),
                    })
                    st.caption(f"Registered '{full_name}' (ID: {repo_id}).")

                    if clone_immediately:
                        progress_bar = st.progress(0.1, text=f"Cloning {full_name}...")

                        def on_progress(msg: str, pct: float) -> None:
                            progress_bar.progress(pct, text=msg)

                        repo_mgr.clone_or_update(
                            url=meta.get("clone_url", f"https://github.com/{full_name}.git"),
                            owner=owner,
                            name=name,
                            default_branch=meta.get("default_branch", "main"),
                            progress_callback=on_progress,
                        )
                        st.rerun()
                except ValueError as ve:
                    st.error(str(ve))
                except RepositoryManagerError as rme:
                    st.error(f"Clone operation failed: {rme}")

    # TAB 4: Managed Repositories
    with tab4:
        st.subheader("Managed Repositories")
        repos = db.list_repositories()
        if not repos:
            st.caption("No repositories registered in the database.")
            return

        repo_table = [
            {
                "ID": r["id"],
                "Repository": r["full_name"],
                "Status": r.get("status", "registered"),
                "Score": r.get("selection_score", 0.0),
                "Stars": r.get("stars", 0),
                "Prod .cs": r.get("production_cs_files_count", 0),
                "Commits": r.get("commits_mined_count", 0),
                "Bug Fixes": r.get("bug_fixes_count", 0),
                "SZZ Traces": r.get("szz_traces_count", 0),
                "Classes": r.get("class_observations_count", 0),
                "Exclusion Reason": r.get("exclusion_reason") or "",
            }
            for r in repos
        ]
        st.dataframe(pd.DataFrame(repo_table), hide_index=True, width="stretch")

        st.subheader("Single Repository Operations")
        repo_choices = {f"#{r['id']}: {r['full_name']} ({r['status']})": r for r in repos}
        selected_r_label = st.selectbox("Select Repository", list(repo_choices.keys()))
        repo = repo_choices[selected_r_label]
        repo_id = repo["id"]

        c_act1, c_act2, c_act3 = st.columns(3)
        with c_act1:
            clone_btn_label = "Pull / Update" if repo["is_cloned"] else "Clone Repository"
            if st.button(clone_btn_label, key=f"btn_sync_{repo_id}", width="stretch"):
                try:
                    repo_mgr.clone_or_update(
                        url=repo["url"] if repo["url"].endswith(".git") else f"{repo['url']}.git",
                        owner=repo["owner"],
                        name=repo["name"],
                        default_branch=repo["default_branch"],
                    )
                    st.rerun()
                except Exception as e:
                    st.error(f"Sync failed: {e}")

        with c_act2:
            if st.button("Extract Commits", key=f"btn_commits_{repo_id}", disabled=not repo["is_cloned"], width="stretch"):
                if not repo["local_path"] or not Path(repo["local_path"]).exists():
                    st.error("Repository local directory does not exist on disk.")
                else:
                    try:
                        commit_collector.extract_and_persist_fast(repository_id=repo_id, local_path=repo["local_path"])
                        st.rerun()
                    except Exception as e:
                        st.error(f"Commit extraction error: {e}")

        with c_act3:
            if st.button("Unlink from DB", key=f"btn_del_{repo_id}", width="stretch"):
                db.delete_repository(repo_id)
                st.rerun()

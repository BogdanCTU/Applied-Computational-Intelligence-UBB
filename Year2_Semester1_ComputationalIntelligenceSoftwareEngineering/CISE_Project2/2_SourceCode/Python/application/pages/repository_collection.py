"""Repository Collection Page: GitHub Discovery, Manual Registration, Cloning, and Commit Extraction."""
from __future__ import annotations

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
    st.caption("Discover, register, clone, and extract commit histories from C# GitHub repositories.")

    gh_client = GitHubClient(token=settings.github.token)
    repo_mgr = RepositoryManager(settings.storage.repositories_dir, db=db)
    commit_collector = CommitCollector(db)

    tab1, tab2, tab3 = st.tabs(["GitHub Discovery", "Manual Import", "Managed Repositories"])

    # TAB 1: GitHub Discovery
    with tab1:
        st.subheader("Search GitHub Repositories")
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
        with col1:
            keywords = st.text_input("Keywords or topic (optional)", placeholder="parser, serialization, roslyn")
        with col2:
            min_stars = st.number_input("Min stars", min_value=0, value=100, step=50)
        with col3:
            min_size_kb = st.number_input("Min size (KB)", min_value=0, value=100, step=100)
        with col4:
            limit = st.slider("Results limit", min_value=5, max_value=50, value=15, step=5)

        col_opts1, col_opts2 = st.columns(2)
        with col_opts1:
            exclude_forks = st.checkbox("Exclude forks", value=True)
        with col_opts2:
            exclude_archived = st.checkbox("Exclude archived repositories", value=True)

        if st.button("Search GitHub Repositories", width="stretch"):
            with st.spinner("Querying GitHub Search API..."):
                try:
                    search_results = gh_client.search_repositories(
                        keywords=keywords,
                        min_stars=min_stars,
                        min_size_kb=min_size_kb,
                        exclude_forks=exclude_forks,
                        exclude_archived=exclude_archived,
                        per_page=limit,
                    )
                    st.session_state["search_results"] = search_results["items"]
                    st.caption(f"Discovered {search_results['total_count']} repositories (showing {len(search_results['items'])}).")
                except RateLimitExceededError as e:
                    st.error(f"GitHub API rate limit reached: {e}. Configure a GitHub token in Settings.")
                except GitHubAPIError as e:
                    st.error(f"GitHub search error: {e}")

        items = st.session_state.get("search_results", [])
        if items:
            st.subheader("Discovered Repositories")
            for repo_item in items:
                with st.expander(f"{repo_item['full_name']} | Stars: {repo_item['stars']} | License: {repo_item['license']}"):
                    st.write(f"Description: {repo_item['description'] or 'None'}")
                    st.write(f"Default branch: `{repo_item['default_branch']}` | Size: {repo_item['size_kb']} KB | URL: {repo_item['url']}")

                    if st.button("Register and Clone", key=f"btn_clone_{repo_item['full_name']}"):
                        db.upsert_repository({
                            "full_name": repo_item["full_name"],
                            "name": repo_item["name"],
                            "owner": repo_item["owner"],
                            "url": repo_item["url"],
                            "description": repo_item["description"],
                            "license": repo_item["license"],
                            "default_branch": repo_item["default_branch"],
                            "stars": repo_item["stars"],
                            "forks": repo_item["forks"],
                            "size_kb": repo_item["size_kb"],
                        })
                        progress_bar = st.progress(0.1, text=f"Cloning {repo_item['full_name']}...")

                        def on_progress(msg: str, pct: float) -> None:
                            progress_bar.progress(pct, text=msg)

                        try:
                            repo_mgr.clone_or_update(
                                url=repo_item["clone_url"],
                                owner=repo_item["owner"],
                                name=repo_item["name"],
                                default_branch=repo_item["default_branch"],
                                progress_callback=on_progress,
                            )
                            st.rerun()
                        except RepositoryManagerError as err:
                            st.error(f"Clone failed: {err}")

    # TAB 2: Manual Import
    with tab2:
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

                    meta: dict = {}
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

    # TAB 3: Managed Repositories
    with tab3:
        st.subheader("Managed Local Repositories")
        repos = db.list_repositories()
        if not repos:
            st.caption("No repositories registered in the database.")
            return

        repo_table = []
        for r in repos:
            repo_table.append({
                "ID": r["id"],
                "Repository": r["full_name"],
                "Status": r["status"],
                "Cloned": bool(r["is_cloned"]),
                "Branch": r["default_branch"],
                "Stars": r["stars"],
                "Commits in DB": db.get_commits_count(r["id"]),
                "Last Synced": r.get("last_sync_at") or "Never",
            })
        st.dataframe(pd.DataFrame(repo_table), hide_index=True, width="stretch")

        st.subheader("Repository Operations")
        for repo in repos:
            repo_id = repo["id"]
            commits_count = db.get_commits_count(repo_id)

            with st.expander(f"{repo['full_name']} (ID: {repo_id} | Status: {repo['status']} | Commits: {commits_count})"):
                if repo["local_path"]:
                    st.code(repo["local_path"], language="text")

                c_act1, c_act2, c_act3 = st.columns(3)

                with c_act1:
                    clone_btn_label = "Pull / Update" if repo["is_cloned"] else "Clone Repository"
                    if st.button(clone_btn_label, key=f"btn_sync_{repo_id}", width="stretch"):
                        p_bar = st.progress(0.1, text="Syncing repository...")

                        def on_prog(msg: str, pct: float) -> None:
                            p_bar.progress(pct, text=msg)

                        try:
                            repo_mgr.clone_or_update(
                                url=repo["url"] if repo["url"].endswith(".git") else f"{repo['url']}.git",
                                owner=repo["owner"],
                                name=repo["name"],
                                default_branch=repo["default_branch"],
                                progress_callback=on_prog,
                            )
                            st.rerun()
                        except Exception as e:
                            st.error(f"Sync failed: {e}")

                with c_act2:
                    if st.button("Extract Commits", key=f"btn_commits_{repo_id}", disabled=not repo["is_cloned"], width="stretch"):
                        if not repo["local_path"] or not Path(repo["local_path"]).exists():
                            st.error("Repository local directory does not exist on disk.")
                        else:
                            p_bar = st.progress(0.1, text="Extracting commits...")

                            def on_commit_prog(msg: str, pct: float) -> None:
                                p_bar.progress(pct, text=msg)

                            try:
                                commit_collector.extract_and_persist(
                                    repository_id=repo_id,
                                    local_path=repo["local_path"],
                                    progress_callback=on_commit_prog,
                                )
                                st.rerun()
                            except Exception as e:
                                st.error(f"Commit extraction error: {e}")

                with c_act3:
                    if st.button("Unlink from DB", key=f"btn_del_{repo_id}", width="stretch"):
                        db.delete_repository(repo_id)
                        st.rerun()

                recent_commits = db.list_commits(repository_id=repo_id, limit=20)
                if recent_commits:
                    st.caption("Recent commits (up to 20):")
                    df_c = pd.DataFrame(recent_commits)[["commit_sha", "committed_date", "author_name", "modifies_csharp", "message"]]
                    st.dataframe(df_c, hide_index=True, width="stretch")

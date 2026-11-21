"""Database repository providing typed CRUD operations for class/file and legacy method entities."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Set, Tuple
from database.connection import Database
from database.schema import CLASS_FEATURE_COLUMNS


CLASS_FEATURE_NAMES: List[str] = [col for col, _ in CLASS_FEATURE_COLUMNS]


class RepositoryDB:
    """Data Access Object for all bug detection domain entities."""

    def __init__(self, db: Database) -> None:
        self.db = db

    # ---------------------------------------------------------
    # Repositories & Collection Runs
    # ---------------------------------------------------------
    def upsert_repository(self, repo_data: Dict[str, Any]) -> int:
        """Insert or update a repository record and return its ID."""
        sql = """
        INSERT INTO repositories (
            full_name, name, owner, url, description, license,
            default_branch, stars, forks, size_kb, is_cloned,
            local_path, status, last_sync_at,
            selection_score, selection_rank, selection_reason, exclusion_reason,
            is_selected, is_fork, is_archived, pushed_at, created_at_gh,
            production_cs_files_count, commits_mined_count, bug_fixes_count,
            szz_traces_count, class_observations_count, processing_error, collection_run_id,
            updated_at
        ) VALUES (
            :full_name, :name, :owner, :url, :description, :license,
            :default_branch, :stars, :forks, :size_kb, :is_cloned,
            :local_path, :status, :last_sync_at,
            :selection_score, :selection_rank, :selection_reason, :exclusion_reason,
            :is_selected, :is_fork, :is_archived, :pushed_at, :created_at_gh,
            :production_cs_files_count, :commits_mined_count, :bug_fixes_count,
            :szz_traces_count, :class_observations_count, :processing_error, :collection_run_id,
            CURRENT_TIMESTAMP
        )
        ON CONFLICT(full_name) DO UPDATE SET
            description = COALESCE(excluded.description, repositories.description),
            license = COALESCE(excluded.license, repositories.license),
            default_branch = COALESCE(excluded.default_branch, repositories.default_branch),
            stars = COALESCE(excluded.stars, repositories.stars),
            forks = COALESCE(excluded.forks, repositories.forks),
            size_kb = COALESCE(excluded.size_kb, repositories.size_kb),
            is_cloned = COALESCE(excluded.is_cloned, repositories.is_cloned),
            local_path = COALESCE(excluded.local_path, repositories.local_path),
            status = COALESCE(excluded.status, repositories.status),
            last_sync_at = COALESCE(excluded.last_sync_at, repositories.last_sync_at),
            selection_score = COALESCE(excluded.selection_score, repositories.selection_score),
            selection_rank = COALESCE(excluded.selection_rank, repositories.selection_rank),
            selection_reason = COALESCE(excluded.selection_reason, repositories.selection_reason),
            exclusion_reason = COALESCE(excluded.exclusion_reason, repositories.exclusion_reason),
            is_selected = COALESCE(excluded.is_selected, repositories.is_selected),
            is_fork = COALESCE(excluded.is_fork, repositories.is_fork),
            is_archived = COALESCE(excluded.is_archived, repositories.is_archived),
            pushed_at = COALESCE(excluded.pushed_at, repositories.pushed_at),
            created_at_gh = COALESCE(excluded.created_at_gh, repositories.created_at_gh),
            production_cs_files_count = COALESCE(excluded.production_cs_files_count, repositories.production_cs_files_count),
            commits_mined_count = COALESCE(excluded.commits_mined_count, repositories.commits_mined_count),
            bug_fixes_count = COALESCE(excluded.bug_fixes_count, repositories.bug_fixes_count),
            szz_traces_count = COALESCE(excluded.szz_traces_count, repositories.szz_traces_count),
            class_observations_count = COALESCE(excluded.class_observations_count, repositories.class_observations_count),
            processing_error = excluded.processing_error,
            collection_run_id = COALESCE(excluded.collection_run_id, repositories.collection_run_id),
            updated_at = CURRENT_TIMESTAMP
        RETURNING id;
        """
        payload = {
            "full_name": repo_data["full_name"],
            "name": repo_data["name"],
            "owner": repo_data["owner"],
            "url": repo_data["url"],
            "description": repo_data.get("description"),
            "license": repo_data.get("license"),
            "default_branch": repo_data.get("default_branch", "main"),
            "stars": repo_data.get("stars", 0),
            "forks": repo_data.get("forks", 0),
            "size_kb": repo_data.get("size_kb", 0),
            "is_cloned": repo_data.get("is_cloned", 0),
            "local_path": repo_data.get("local_path"),
            "status": repo_data.get("status", "registered"),
            "last_sync_at": repo_data.get("last_sync_at"),
            "selection_score": repo_data.get("selection_score", 0.0),
            "selection_rank": repo_data.get("selection_rank"),
            "selection_reason": repo_data.get("selection_reason"),
            "exclusion_reason": repo_data.get("exclusion_reason"),
            "is_selected": 1 if repo_data.get("is_selected", True) else 0,
            "is_fork": 1 if repo_data.get("is_fork", False) else 0,
            "is_archived": 1 if repo_data.get("is_archived", False) else 0,
            "pushed_at": repo_data.get("pushed_at"),
            "created_at_gh": repo_data.get("created_at_gh"),
            "production_cs_files_count": repo_data.get("production_cs_files_count"),
            "commits_mined_count": repo_data.get("commits_mined_count"),
            "bug_fixes_count": repo_data.get("bug_fixes_count"),
            "szz_traces_count": repo_data.get("szz_traces_count"),
            "class_observations_count": repo_data.get("class_observations_count"),
            "processing_error": repo_data.get("processing_error"),
            "collection_run_id": repo_data.get("collection_run_id"),
        }
        with self.db.session() as conn:
            cursor = conn.execute(sql, payload)
            row = cursor.fetchone()
            return row["id"] if row else -1

    def get_repository_by_id(self, repo_id: int) -> Optional[Dict[str, Any]]:
        with self.db.session() as conn:
            row = conn.execute("SELECT * FROM repositories WHERE id = ?", (repo_id,)).fetchone()
            return dict(row) if row else None

    def get_repository_by_full_name(self, full_name: str) -> Optional[Dict[str, Any]]:
        with self.db.session() as conn:
            row = conn.execute("SELECT * FROM repositories WHERE full_name = ?", (full_name,)).fetchone()
            return dict(row) if row else None

    def list_repositories(self, selected_only: bool = False) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM repositories"
        if selected_only:
            sql += " WHERE is_selected = 1"
        sql += " ORDER BY stars DESC, collected_at DESC"
        with self.db.session() as conn:
            rows = conn.execute(sql).fetchall()
            return [dict(r) for r in rows]

    def update_repository_status(
        self,
        repo_id: int,
        status: str,
        is_cloned: Optional[bool] = None,
        local_path: Optional[str] = None,
        last_sync_at: Optional[str] = None,
        processing_error: Optional[str] = None,
        exclusion_reason: Optional[str] = None,
        class_observations_count: Optional[int] = None,
    ) -> None:
        updates = ["status = ?", "updated_at = CURRENT_TIMESTAMP"]
        params: List[Any] = [status]
        if is_cloned is not None:
            updates.append("is_cloned = ?")
            params.append(1 if is_cloned else 0)
        if local_path is not None:
            updates.append("local_path = ?")
            params.append(local_path)
        if last_sync_at is not None:
            updates.append("last_sync_at = ?")
            params.append(last_sync_at)
        if processing_error is not None:
            updates.append("processing_error = ?")
            params.append(processing_error)
        if exclusion_reason is not None:
            updates.append("exclusion_reason = ?")
            params.append(exclusion_reason)
        if class_observations_count is not None:
            updates.append("class_observations_count = ?")
            params.append(class_observations_count)
        params.append(repo_id)

        sql = f"UPDATE repositories SET {', '.join(updates)} WHERE id = ?"
        with self.db.session() as conn:
            conn.execute(sql, params)

    def update_repository_metrics(self, repo_id: int, metrics: Dict[str, Any]) -> None:
        """Update repository-level mining counts and optional exclusion status."""
        allowed = [
            "production_cs_files_count",
            "commits_mined_count",
            "bug_fixes_count",
            "szz_traces_count",
            "class_observations_count",
            "exclusion_reason",
            "processing_error",
            "status",
            "is_selected",
        ]
        updates = ["updated_at = CURRENT_TIMESTAMP"]
        params: List[Any] = []
        for col in allowed:
            if col in metrics:
                updates.append(f"{col} = ?")
                params.append(metrics[col])
        if len(updates) == 1:
            return
        params.append(repo_id)
        sql = f"UPDATE repositories SET {', '.join(updates)} WHERE id = ?"
        with self.db.session() as conn:
            conn.execute(sql, params)

    def update_repository_cloned_status(self, repo_id: int, is_cloned: bool, local_path: str) -> None:
        """Compatibility wrapper for updating clone status."""
        self.update_repository_status(
            repo_id=repo_id,
            status="cloned" if is_cloned else "registered",
            is_cloned=is_cloned,
            local_path=local_path,
        )

    def delete_repository(self, repo_id: int) -> bool:
        """Remove repository metadata and associated commits from DB (does NOT delete local git files)."""
        with self.db.session() as conn:
            cursor = conn.execute("DELETE FROM repositories WHERE id = ?", (repo_id,))
            return cursor.rowcount > 0

    def upsert_collection_run(self, run_data: Dict[str, Any]) -> int:
        sql = """
        INSERT INTO repository_collection_runs (
            run_id, target_repositories, discovered_count, selected_count,
            processed_count, excluded_count, failed_count, status,
            config_json, checkpoint_path
        ) VALUES (
            :run_id, :target_repositories, :discovered_count, :selected_count,
            :processed_count, :excluded_count, :failed_count, :status,
            :config_json, :checkpoint_path
        )
        ON CONFLICT(run_id) DO UPDATE SET
            discovered_count = excluded.discovered_count,
            selected_count = excluded.selected_count,
            processed_count = excluded.processed_count,
            excluded_count = excluded.excluded_count,
            failed_count = excluded.failed_count,
            status = excluded.status,
            completed_at = CASE WHEN excluded.status IN ('completed', 'failed') THEN CURRENT_TIMESTAMP ELSE repository_collection_runs.completed_at END
        RETURNING id;
        """
        payload = {
            "run_id": run_data["run_id"],
            "target_repositories": run_data.get("target_repositories", 100),
            "discovered_count": run_data.get("discovered_count", 0),
            "selected_count": run_data.get("selected_count", 0),
            "processed_count": run_data.get("processed_count", 0),
            "excluded_count": run_data.get("excluded_count", 0),
            "failed_count": run_data.get("failed_count", 0),
            "status": run_data.get("status", "running"),
            "config_json": json.dumps(run_data.get("config", {})) if isinstance(run_data.get("config"), dict) else run_data.get("config_json"),
            "checkpoint_path": run_data.get("checkpoint_path"),
        }
        with self.db.session() as conn:
            row = conn.execute(sql, payload).fetchone()
            return row["id"] if row else -1

    def list_collection_runs(self) -> List[Dict[str, Any]]:
        with self.db.session() as conn:
            rows = conn.execute("SELECT * FROM repository_collection_runs ORDER BY started_at DESC").fetchall()
            return [dict(r) for r in rows]

    # ---------------------------------------------------------
    # Commits
    # ---------------------------------------------------------
    def upsert_commit(self, commit_data: Dict[str, Any]) -> int:
        """Insert or update a commit record and return its ID."""
        sql = """
        INSERT INTO commits (
            repository_id, commit_sha, parent_sha, parent_shas,
            author_name, author_email, committed_date, committer_date,
            message, files_changed_count, insertions, deletions,
            modifies_csharp, is_bug_fix, bug_fix_confidence, bug_fix_evidence, analyzed_at
        ) VALUES (
            :repository_id, :commit_sha, :parent_sha, :parent_shas,
            :author_name, :author_email, :committed_date, :committer_date,
            :message, :files_changed_count, :insertions, :deletions,
            :modifies_csharp, :is_bug_fix, :bug_fix_confidence, :bug_fix_evidence, :analyzed_at
        )
        ON CONFLICT(repository_id, commit_sha) DO UPDATE SET
            parent_shas = COALESCE(excluded.parent_shas, commits.parent_shas),
            committer_date = COALESCE(excluded.committer_date, commits.committer_date),
            files_changed_count = excluded.files_changed_count,
            insertions = excluded.insertions,
            deletions = excluded.deletions,
            modifies_csharp = excluded.modifies_csharp,
            is_bug_fix = excluded.is_bug_fix,
            bug_fix_confidence = excluded.bug_fix_confidence,
            bug_fix_evidence = excluded.bug_fix_evidence,
            analyzed_at = COALESCE(excluded.analyzed_at, commits.analyzed_at)
        RETURNING id;
        """
        payload = self._build_commit_payload(commit_data)
        with self.db.session() as conn:
            cursor = conn.execute(sql, payload)
            row = cursor.fetchone()
            return row["id"] if row else -1

    @staticmethod
    def _build_commit_payload(commit_data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "repository_id": commit_data["repository_id"],
            "commit_sha": commit_data["commit_sha"],
            "parent_sha": commit_data.get("parent_sha"),
            "parent_shas": commit_data.get("parent_shas"),
            "author_name": commit_data.get("author_name"),
            "author_email": commit_data.get("author_email"),
            "committed_date": commit_data.get("committed_date"),
            "committer_date": commit_data.get("committer_date"),
            "message": commit_data.get("message"),
            "files_changed_count": commit_data.get("files_changed_count", 0),
            "insertions": commit_data.get("insertions", 0),
            "deletions": commit_data.get("deletions", 0),
            "modifies_csharp": commit_data.get("modifies_csharp", 0),
            "is_bug_fix": commit_data.get("is_bug_fix", 0),
            "bug_fix_confidence": commit_data.get("bug_fix_confidence", 0.0),
            "bug_fix_evidence": commit_data.get("bug_fix_evidence"),
            "analyzed_at": commit_data.get("analyzed_at"),
        }

    def batch_insert_commits_with_files(self, items: List[Tuple[Dict[str, Any], List[Dict[str, Any]]]]) -> int:
        """Persist commits and commit_files inside a single SQLite transaction."""
        if not items:
            return 0
        commit_sql = """
        INSERT INTO commits (
            repository_id, commit_sha, parent_sha, parent_shas,
            author_name, author_email, committed_date, committer_date,
            message, files_changed_count, insertions, deletions,
            modifies_csharp, is_bug_fix, bug_fix_confidence, bug_fix_evidence, analyzed_at
        ) VALUES (
            :repository_id, :commit_sha, :parent_sha, :parent_shas,
            :author_name, :author_email, :committed_date, :committer_date,
            :message, :files_changed_count, :insertions, :deletions,
            :modifies_csharp, :is_bug_fix, :bug_fix_confidence, :bug_fix_evidence, :analyzed_at
        )
        ON CONFLICT(repository_id, commit_sha) DO UPDATE SET
            parent_shas = COALESCE(excluded.parent_shas, commits.parent_shas),
            files_changed_count = excluded.files_changed_count,
            insertions = excluded.insertions,
            deletions = excluded.deletions,
            modifies_csharp = excluded.modifies_csharp
        RETURNING id;
        """
        file_sql = """
        INSERT INTO commit_files (commit_id, file_path, change_type, insertions, deletions, is_csharp)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(commit_id, file_path) DO UPDATE SET
            change_type = excluded.change_type,
            insertions = excluded.insertions,
            deletions = excluded.deletions,
            is_csharp = excluded.is_csharp;
        """
        inserted = 0
        with self.db.session() as conn:
            for c_data, files in items:
                row = conn.execute(commit_sql, self._build_commit_payload(c_data)).fetchone()
                if row and files:
                    cid = row["id"]
                    records = [
                        (
                            cid,
                            f["file_path"],
                            f.get("change_type", "M"),
                            f.get("insertions", 0),
                            f.get("deletions", 0),
                            1 if f.get("is_csharp", False) else 0,
                        )
                        for f in files
                    ]
                    conn.executemany(file_sql, records)
                inserted += 1
        return inserted

    def batch_insert_commits(self, commits_list: List[Dict[str, Any]]) -> int:
        """Insert a batch of commits efficiently."""
        return self.batch_insert_commits_with_files([(c, []) for c in commits_list])

    def batch_update_commit_classifications(self, updates: List[Dict[str, Any]]) -> None:
        """Update bug-fix classification columns in a single SQLite transaction."""
        if not updates:
            return
        sql = """
        UPDATE commits
        SET is_bug_fix = :is_bug_fix,
            bug_fix_confidence = :bug_fix_confidence,
            bug_fix_evidence = :bug_fix_evidence,
            analyzed_at = CURRENT_TIMESTAMP
        WHERE id = :id;
        """
        with self.db.session() as conn:
            conn.executemany(sql, updates)

    def insert_commit_files(self, commit_id: int, files: List[Dict[str, Any]]) -> None:
        """Insert modified files for a commit."""
        sql = """
        INSERT INTO commit_files (commit_id, file_path, change_type, insertions, deletions, is_csharp)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(commit_id, file_path) DO UPDATE SET
            change_type = excluded.change_type,
            insertions = excluded.insertions,
            deletions = excluded.deletions,
            is_csharp = excluded.is_csharp;
        """
        records = [
            (
                commit_id,
                f["file_path"],
                f.get("change_type", "M"),
                f.get("insertions", 0),
                f.get("deletions", 0),
                1 if f.get("is_csharp", False) else 0,
            )
            for f in files
        ]
        with self.db.session() as conn:
            conn.executemany(sql, records)

    def get_commit_shas_for_repository(self, repository_id: int) -> Set[str]:
        """Get set of commit SHAs already recorded for a repository to support incremental sync."""
        with self.db.session() as conn:
            rows = conn.execute("SELECT commit_sha FROM commits WHERE repository_id = ?", (repository_id,)).fetchall()
            return {r["commit_sha"] for r in rows}

    def get_commits_count(self, repository_id: int) -> int:
        with self.db.session() as conn:
            row = conn.execute("SELECT COUNT(*) as cnt FROM commits WHERE repository_id = ?", (repository_id,)).fetchone()
            return row["cnt"] if row else 0

    def list_commits(self, repository_id: Optional[int] = None, bug_fix_only: bool = False, limit: int = 500) -> List[Dict[str, Any]]:
        query = "SELECT * FROM commits WHERE 1=1"
        params: List[Any] = []
        if repository_id is not None:
            query += " AND repository_id = ?"
            params.append(repository_id)
        if bug_fix_only:
            query += " AND is_bug_fix = 1"
        query += " ORDER BY committed_date DESC LIMIT ?"
        params.append(limit)
        with self.db.session() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def get_bug_fix_touched_files(self, repository_id: int) -> Set[str]:
        """Return set of file paths modified in any bug-fixing commit or SZZ trace for a repository."""
        paths: Set[str] = set()
        with self.db.session() as conn:
            rows1 = conn.execute(
                """
                SELECT DISTINCT cf.file_path
                FROM commit_files cf
                JOIN commits c ON cf.commit_id = c.id
                WHERE c.repository_id = ? AND c.is_bug_fix = 1
                """,
                (repository_id,),
            ).fetchall()
            rows2 = conn.execute(
                "SELECT DISTINCT file_path FROM szz_results WHERE repository_id = ?",
                (repository_id,),
            ).fetchall()
            for r in rows1:
                paths.add(r["file_path"])
            for r in rows2:
                paths.add(r["file_path"])
        return paths

    def update_commit_review_status(self, commit_id: int, review_status: str, is_bug_fix: Optional[bool] = None) -> None:
        """Update manual review status of a commit (unreviewed, confirmed, rejected)."""
        updates = ["review_status = ?", "analyzed_at = CURRENT_TIMESTAMP"]
        params: List[Any] = [review_status]
        if is_bug_fix is not None:
            updates.append("is_bug_fix = ?")
            params.append(1 if is_bug_fix else 0)
        params.append(commit_id)
        sql = f"UPDATE commits SET {', '.join(updates)} WHERE id = ?"
        with self.db.session() as conn:
            conn.execute(sql, params)

    def insert_szz_result(self, szz_data: Dict[str, Any]) -> int:
        """Insert an SZZ line-to-BIC trace record."""
        sql = """
        INSERT INTO szz_results (
            repository_id, fixing_commit_sha, inducing_commit_sha, file_path,
            deleted_line_number, deleted_line_content, inducing_line_number,
            confidence, evidence
        ) VALUES (
            :repository_id, :fixing_commit_sha, :inducing_commit_sha, :file_path,
            :deleted_line_number, :deleted_line_content, :inducing_line_number,
            :confidence, :evidence
        )
        ON CONFLICT(repository_id, fixing_commit_sha, inducing_commit_sha, file_path, deleted_line_number)
        DO UPDATE SET
            confidence = excluded.confidence,
            evidence = excluded.evidence
        RETURNING id;
        """
        payload = {
            "repository_id": szz_data["repository_id"],
            "fixing_commit_sha": szz_data["fixing_commit_sha"],
            "inducing_commit_sha": szz_data["inducing_commit_sha"],
            "file_path": szz_data["file_path"],
            "deleted_line_number": szz_data.get("deleted_line_number"),
            "deleted_line_content": szz_data.get("deleted_line_content"),
            "inducing_line_number": szz_data.get("inducing_line_number"),
            "confidence": szz_data.get("confidence", 1.0),
            "evidence": szz_data.get("evidence"),
        }
        with self.db.session() as conn:
            cursor = conn.execute(sql, payload)
            row = cursor.fetchone()
            return row["id"] if row else -1

    def batch_insert_szz_results(self, records: List[Dict[str, Any]]) -> int:
        if not records:
            return 0
        sql = """
        INSERT INTO szz_results (
            repository_id, fixing_commit_sha, inducing_commit_sha, file_path,
            deleted_line_number, deleted_line_content, inducing_line_number,
            confidence, evidence
        ) VALUES (
            :repository_id, :fixing_commit_sha, :inducing_commit_sha, :file_path,
            :deleted_line_number, :deleted_line_content, :inducing_line_number,
            :confidence, :evidence
        )
        ON CONFLICT(repository_id, fixing_commit_sha, inducing_commit_sha, file_path, deleted_line_number)
        DO UPDATE SET
            confidence = excluded.confidence,
            evidence = excluded.evidence;
        """
        payloads = [
            {
                "repository_id": r["repository_id"],
                "fixing_commit_sha": r["fixing_commit_sha"],
                "inducing_commit_sha": r["inducing_commit_sha"],
                "file_path": r["file_path"],
                "deleted_line_number": r.get("deleted_line_number"),
                "deleted_line_content": r.get("deleted_line_content"),
                "inducing_line_number": r.get("inducing_line_number"),
                "confidence": r.get("confidence", 1.0),
                "evidence": r.get("evidence"),
            }
            for r in records
        ]
        with self.db.session() as conn:
            conn.executemany(sql, payloads)
        return len(payloads)

    def list_szz_results(self, repository_id: int, fixing_commit_sha: Optional[str] = None) -> List[Dict[str, Any]]:
        query = "SELECT * FROM szz_results WHERE repository_id = ?"
        params: List[Any] = [repository_id]
        if fixing_commit_sha:
            query += " AND fixing_commit_sha = ?"
            params.append(fixing_commit_sha)
        query += " ORDER BY created_at DESC"
        with self.db.session() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def get_commit_files(self, commit_id: int) -> List[Dict[str, Any]]:
        with self.db.session() as conn:
            rows = conn.execute("SELECT * FROM commit_files WHERE commit_id = ?", (commit_id,)).fetchall()
            return [dict(r) for r in rows]

    # ---------------------------------------------------------
    # Historical Method Observations (Preserved)
    # ---------------------------------------------------------
    def insert_observation(self, obs_data: Dict[str, Any]) -> int:
        """Insert a method observation with safe defaults for optional fields."""
        sql = """
        INSERT INTO observations (
            repository_id, commit_sha, parent_sha, bug_fix_commit_sha,
            file_path, class_name, method_name, method_signature,
            source_code, corrected_code, label, label_confidence,
            evidence_category, bug_fixing_commit_message, issue_or_pr_url
        ) VALUES (
            :repository_id, :commit_sha, :parent_sha, :bug_fix_commit_sha,
            :file_path, :class_name, :method_name, :method_signature,
            :source_code, :corrected_code, :label, :label_confidence,
            :evidence_category, :bug_fixing_commit_message, :issue_or_pr_url
        )
        ON CONFLICT(repository_id, commit_sha, file_path, method_signature, label)
        DO UPDATE SET
            source_code = excluded.source_code,
            corrected_code = excluded.corrected_code,
            label_confidence = excluded.label_confidence,
            evidence_category = excluded.evidence_category
        RETURNING id;
        """
        payload = {
            "repository_id": obs_data["repository_id"],
            "commit_sha": obs_data["commit_sha"],
            "parent_sha": obs_data.get("parent_sha"),
            "bug_fix_commit_sha": obs_data.get("bug_fix_commit_sha"),
            "file_path": obs_data["file_path"],
            "class_name": obs_data["class_name"],
            "method_name": obs_data["method_name"],
            "method_signature": obs_data["method_signature"],
            "source_code": obs_data["source_code"],
            "corrected_code": obs_data.get("corrected_code"),
            "label": obs_data["label"],
            "label_confidence": obs_data.get("label_confidence", 1.0),
            "evidence_category": obs_data.get("evidence_category", "unknown"),
            "bug_fixing_commit_message": obs_data.get("bug_fixing_commit_message"),
            "issue_or_pr_url": obs_data.get("issue_or_pr_url"),
        }
        with self.db.session() as conn:
            cursor = conn.execute(sql, payload)
            row = cursor.fetchone()
            return row["id"] if row else -1

    def list_observations(
        self,
        repository_id: Optional[int] = None,
        label: Optional[int] = None,
        exclude_uncertain: bool = False,
    ) -> List[Dict[str, Any]]:
        query = "SELECT * FROM observations WHERE 1=1"
        params: List[Any] = []
        if repository_id is not None:
            query += " AND repository_id = ?"
            params.append(repository_id)
        if label is not None:
            query += " AND label = ?"
            params.append(label)
        elif exclude_uncertain:
            query += " AND label != -1"
        query += " ORDER BY created_at DESC"
        with self.db.session() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def update_observation_label(self, observation_id: int, new_label: int, reason: str = "manual_correction") -> None:
        with self.db.session() as conn:
            conn.execute(
                "UPDATE observations SET label = ?, evidence_category = ? WHERE id = ?",
                (new_label, reason, observation_id),
            )

    def upsert_features(self, feat_data: Dict[str, Any]) -> int:
        """Insert or replace method features extracted for a method observation."""
        fields = [
            "observation_id", "loc", "logical_loc", "method_length", "statement_count", "parameter_count",
            "local_variable_count", "return_count", "assignment_count", "cyclomatic_complexity",
            "max_nesting_depth", "if_count", "switch_count", "loop_count", "try_catch_count", "throw_count",
            "break_continue_count", "boolean_operator_count", "logical_operator_count",
            "conditional_expression_count", "method_call_count", "field_access_count",
            "property_access_count", "object_creation_count", "is_static", "is_async", "is_generic",
            "num_statements", "num_parameters", "num_local_vars", "num_returns", "num_assignments",
            "num_conditionals", "num_boolean_expressions", "num_logical_operators", "num_loops",
            "num_try_catch", "num_throw", "num_method_calls", "num_field_references",
            "num_property_references", "num_comments", "num_lambdas", "num_linq_operations",
            "status", "error_message", "analyzer_version", "raw_metrics_json"
        ]
        data = dict(feat_data)
        data.setdefault("num_statements", data.get("statement_count", 0))
        data.setdefault("statement_count", data.get("num_statements", 0))
        data.setdefault("num_parameters", data.get("parameter_count", 0))
        data.setdefault("parameter_count", data.get("num_parameters", 0))
        data.setdefault("num_local_vars", data.get("local_variable_count", 0))
        data.setdefault("local_variable_count", data.get("num_local_vars", 0))
        data.setdefault("num_returns", data.get("return_count", 0))
        data.setdefault("return_count", data.get("num_returns", 0))
        data.setdefault("num_assignments", data.get("assignment_count", 0))
        data.setdefault("assignment_count", data.get("num_assignments", 0))
        data.setdefault("num_loops", data.get("loop_count", 0))
        data.setdefault("loop_count", data.get("num_loops", 0))
        data.setdefault("num_try_catch", data.get("try_catch_count", 0))
        data.setdefault("try_catch_count", data.get("num_try_catch", 0))
        data.setdefault("num_throw", data.get("throw_count", 0))
        data.setdefault("throw_count", data.get("num_throw", 0))
        data.setdefault("num_method_calls", data.get("method_call_count", 0))
        data.setdefault("method_call_count", data.get("num_method_calls", 0))
        data.setdefault("num_field_references", data.get("field_access_count", 0))
        data.setdefault("field_access_count", data.get("num_field_references", 0))
        data.setdefault("num_property_references", data.get("property_access_count", 0))
        data.setdefault("property_access_count", data.get("num_property_references", 0))
        data.setdefault("num_conditionals", data.get("conditional_expression_count", 0))
        data.setdefault("conditional_expression_count", data.get("num_conditionals", 0))
        data.setdefault("num_boolean_expressions", data.get("boolean_operator_count", 0))
        data.setdefault("boolean_operator_count", data.get("num_boolean_expressions", 0))
        data.setdefault("num_logical_operators", data.get("logical_operator_count", 0))
        data.setdefault("logical_operator_count", data.get("num_logical_operators", 0))
        data.setdefault("status", "success")
        data.setdefault("analyzer_version", "1.0.0")

        columns = ", ".join(fields)
        placeholders = ", ".join(f":{f}" for f in fields)
        updates = ", ".join(f"{f} = excluded.{f}" for f in fields if f != "observation_id")

        sql = f"""
        INSERT INTO features ({columns})
        VALUES ({placeholders})
        ON CONFLICT(observation_id) DO UPDATE SET
            {updates},
            extracted_at = CURRENT_TIMESTAMP
        RETURNING id;
        """
        full_data = {f: data.get(f) for f in fields}
        with self.db.session() as conn:
            cursor = conn.execute(sql, full_data)
            row = cursor.fetchone()
            return row["id"] if row else -1

    def get_observations_needing_features(self, repository_id: Optional[int] = None, include_failed: bool = False) -> List[Dict[str, Any]]:
        """Get method observations that have not had features successfully extracted yet."""
        query = """
        SELECT o.* FROM observations o
        LEFT JOIN features f ON o.id = f.observation_id
        WHERE f.id IS NULL
        """
        if include_failed:
            query = """
            SELECT o.* FROM observations o
            LEFT JOIN features f ON o.id = f.observation_id
            WHERE f.id IS NULL OR f.status = 'failed'
            """
        params: List[Any] = []
        if repository_id is not None:
            query += " AND o.repository_id = ?"
            params.append(repository_id)
        query += " ORDER BY o.id ASC"

        with self.db.session() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def get_features_by_observation_id(self, observation_id: int) -> Optional[Dict[str, Any]]:
        with self.db.session() as conn:
            row = conn.execute("SELECT * FROM features WHERE observation_id = ?", (observation_id,)).fetchone()
            return dict(row) if row else None

    def get_features(self, observation_id: int) -> Optional[Dict[str, Any]]:
        """Alias for get_features_by_observation_id."""
        return self.get_features_by_observation_id(observation_id)

    # ---------------------------------------------------------
    # File & Class-Level Observations and Features
    # ---------------------------------------------------------
    def insert_file_observation(self, file_data: Dict[str, Any]) -> int:
        sql = """
        INSERT INTO file_observations (
            repository_id, commit_sha, file_path, total_lines,
            namespace_count, class_count, method_count, file_fingerprint
        ) VALUES (
            :repository_id, :commit_sha, :file_path, :total_lines,
            :namespace_count, :class_count, :method_count, :file_fingerprint
        )
        ON CONFLICT(repository_id, commit_sha, file_path) DO UPDATE SET
            total_lines = excluded.total_lines,
            namespace_count = excluded.namespace_count,
            class_count = excluded.class_count,
            method_count = excluded.method_count,
            file_fingerprint = excluded.file_fingerprint
        RETURNING id;
        """
        payload = {
            "repository_id": file_data["repository_id"],
            "commit_sha": file_data["commit_sha"],
            "file_path": file_data["file_path"],
            "total_lines": file_data.get("total_lines", 0),
            "namespace_count": file_data.get("namespace_count", 0),
            "class_count": file_data.get("class_count", 0),
            "method_count": file_data.get("method_count", 0),
            "file_fingerprint": file_data.get("file_fingerprint"),
        }
        with self.db.session() as conn:
            row = conn.execute(sql, payload).fetchone()
            return row["id"] if row else -1

    def list_file_observations(self, repository_id: Optional[int] = None) -> List[Dict[str, Any]]:
        query = "SELECT * FROM file_observations"
        params: List[Any] = []
        if repository_id is not None:
            query += " WHERE repository_id = ?"
            params.append(repository_id)
        query += " ORDER BY created_at DESC"
        with self.db.session() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def insert_class_observation(self, obs_data: Dict[str, Any]) -> int:
        """Insert or update a class-level observation and return its ID."""
        sql = """
        INSERT INTO class_observations (
            file_observation_id, repository_id, commit_sha, parent_sha,
            bug_fix_commit_sha, bug_inducing_commit_sha, file_path,
            namespace_name, class_name, qualified_class_name, type_kind,
            start_line, end_line, is_nested, enclosing_type_name,
            source_code, corrected_code, source_fingerprint, structural_fingerprint,
            label, label_confidence, szz_trace_count, blamed_lines_json,
            evidence_category, bug_fixing_commit_message, issue_or_pr_url
        ) VALUES (
            :file_observation_id, :repository_id, :commit_sha, :parent_sha,
            :bug_fix_commit_sha, :bug_inducing_commit_sha, :file_path,
            :namespace_name, :class_name, :qualified_class_name, :type_kind,
            :start_line, :end_line, :is_nested, :enclosing_type_name,
            :source_code, :corrected_code, :source_fingerprint, :structural_fingerprint,
            :label, :label_confidence, :szz_trace_count, :blamed_lines_json,
            :evidence_category, :bug_fixing_commit_message, :issue_or_pr_url
        )
        ON CONFLICT(repository_id, commit_sha, file_path, qualified_class_name, label)
        DO UPDATE SET
            file_observation_id = COALESCE(excluded.file_observation_id, class_observations.file_observation_id),
            bug_inducing_commit_sha = COALESCE(excluded.bug_inducing_commit_sha, class_observations.bug_inducing_commit_sha),
            source_code = excluded.source_code,
            corrected_code = COALESCE(excluded.corrected_code, class_observations.corrected_code),
            source_fingerprint = excluded.source_fingerprint,
            structural_fingerprint = excluded.structural_fingerprint,
            label_confidence = excluded.label_confidence,
            szz_trace_count = MAX(class_observations.szz_trace_count, excluded.szz_trace_count),
            blamed_lines_json = COALESCE(excluded.blamed_lines_json, class_observations.blamed_lines_json),
            evidence_category = excluded.evidence_category
        RETURNING id;
        """
        payload = {
            "file_observation_id": obs_data.get("file_observation_id"),
            "repository_id": obs_data["repository_id"],
            "commit_sha": obs_data["commit_sha"],
            "parent_sha": obs_data.get("parent_sha"),
            "bug_fix_commit_sha": obs_data.get("bug_fix_commit_sha"),
            "bug_inducing_commit_sha": obs_data.get("bug_inducing_commit_sha"),
            "file_path": obs_data["file_path"],
            "namespace_name": obs_data.get("namespace_name", "Global"),
            "class_name": obs_data["class_name"],
            "qualified_class_name": obs_data.get("qualified_class_name", obs_data["class_name"]),
            "type_kind": obs_data.get("type_kind", "class"),
            "start_line": obs_data.get("start_line", 1),
            "end_line": obs_data.get("end_line", 1),
            "is_nested": 1 if obs_data.get("is_nested", False) else 0,
            "enclosing_type_name": obs_data.get("enclosing_type_name"),
            "source_code": obs_data["source_code"],
            "corrected_code": obs_data.get("corrected_code"),
            "source_fingerprint": obs_data["source_fingerprint"],
            "structural_fingerprint": obs_data["structural_fingerprint"],
            "label": obs_data["label"],
            "label_confidence": obs_data.get("label_confidence", 1.0),
            "szz_trace_count": obs_data.get("szz_trace_count", 0),
            "blamed_lines_json": obs_data.get("blamed_lines_json"),
            "evidence_category": obs_data.get("evidence_category", "unknown"),
            "bug_fixing_commit_message": obs_data.get("bug_fixing_commit_message"),
            "issue_or_pr_url": obs_data.get("issue_or_pr_url"),
        }
        with self.db.session() as conn:
            row = conn.execute(sql, payload).fetchone()
            return row["id"] if row else -1

    def list_class_observations(
        self,
        repository_id: Optional[int] = None,
        label: Optional[int] = None,
        exclude_uncertain: bool = False,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        query = "SELECT * FROM class_observations WHERE 1=1"
        params: List[Any] = []
        if repository_id is not None:
            query += " AND repository_id = ?"
            params.append(repository_id)
        if label is not None:
            query += " AND label = ?"
            params.append(label)
        elif exclude_uncertain:
            query += " AND label != -1"
        query += " ORDER BY id ASC"
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        with self.db.session() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def update_class_observation_label(self, class_observation_id: int, new_label: int, reason: str = "manual_correction") -> None:
        with self.db.session() as conn:
            conn.execute(
                "UPDATE class_observations SET label = ?, evidence_category = ? WHERE id = ?",
                (new_label, reason, class_observation_id),
            )

    def upsert_class_features(self, feat_data: Dict[str, Any]) -> int:
        """Insert or replace the 40 class-level static code features for a class observation."""
        fields = [
            "class_observation_id",
            *CLASS_FEATURE_NAMES,
            "feature_schema_version",
            "analyzer_version",
            "status",
            "error_message",
            "raw_metrics_json",
        ]
        data = dict(feat_data)
        data.setdefault("feature_schema_version", "3.0.0")
        data.setdefault("analyzer_version", "2.0.0")
        data.setdefault("status", "success")

        columns = ", ".join(fields)
        placeholders = ", ".join(f":{f}" for f in fields)
        updates = ", ".join(f"{f} = excluded.{f}" for f in fields if f != "class_observation_id")

        sql = f"""
        INSERT INTO class_features ({columns})
        VALUES ({placeholders})
        ON CONFLICT(class_observation_id) DO UPDATE SET
            {updates},
            extracted_at = CURRENT_TIMESTAMP
        RETURNING id;
        """
        full_data = {f: data.get(f, 0 if f in CLASS_FEATURE_NAMES else None) for f in fields}
        with self.db.session() as conn:
            row = conn.execute(sql, full_data).fetchone()
            return row["id"] if row else -1

    def get_class_features_by_observation_id(self, class_observation_id: int) -> Optional[Dict[str, Any]]:
        with self.db.session() as conn:
            row = conn.execute("SELECT * FROM class_features WHERE class_observation_id = ?", (class_observation_id,)).fetchone()
            return dict(row) if row else None

    def get_class_observations_needing_features(
        self,
        repository_id: Optional[int] = None,
        include_failed: bool = False,
    ) -> List[Dict[str, Any]]:
        query = """
        SELECT co.* FROM class_observations co
        LEFT JOIN class_features cf ON co.id = cf.class_observation_id
        WHERE cf.id IS NULL
        """
        if include_failed:
            query = """
            SELECT co.* FROM class_observations co
            LEFT JOIN class_features cf ON co.id = cf.class_observation_id
            WHERE cf.id IS NULL OR cf.status = 'failed'
            """
        params: List[Any] = []
        if repository_id is not None:
            query += " AND co.repository_id = ?"
            params.append(repository_id)
        query += " ORDER BY co.id ASC"
        with self.db.session() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def list_class_observations_with_features(
        self,
        repository_ids: Optional[List[int]] = None,
        exclude_uncertain: bool = True,
    ) -> List[Dict[str, Any]]:
        """Fetch class observations joined with repository names and class_features in one query."""
        feat_cols = ", ".join(f"cf.{c}" for c in CLASS_FEATURE_NAMES)
        sql = f"""
        SELECT
            co.id as class_observation_id,
            co.repository_id,
            r.full_name as repository_name,
            co.commit_sha,
            co.parent_sha,
            co.bug_fix_commit_sha,
            co.bug_inducing_commit_sha,
            co.file_path,
            co.namespace_name,
            co.class_name,
            co.qualified_class_name,
            co.type_kind,
            co.start_line,
            co.end_line,
            co.is_nested,
            co.source_fingerprint,
            co.structural_fingerprint,
            co.label,
            co.label_confidence,
            co.szz_trace_count,
            co.evidence_category,
            cf.status as feature_status,
            cf.feature_schema_version,
            {feat_cols}
        FROM class_observations co
        JOIN repositories r ON co.repository_id = r.id
        JOIN class_features cf ON co.id = cf.class_observation_id
        WHERE cf.status = 'success'
        """
        params: List[Any] = []
        if exclude_uncertain:
            sql += " AND co.label IN (0, 1)"
        if repository_ids:
            placeholders = ",".join("?" for _ in repository_ids)
            sql += f" AND co.repository_id IN ({placeholders})"
            params.extend(repository_ids)
        sql += " ORDER BY co.id ASC"
        with self.db.session() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]

    # ---------------------------------------------------------
    # Datasets (Method + Class)
    # ---------------------------------------------------------
    def create_dataset(
        self,
        name: str,
        version: str,
        description: str,
        observation_ids: List[int],
        feature_names: List[str],
        export_path: Optional[str] = None,
    ) -> int:
        with self.db.session() as conn:
            placeholders = ",".join("?" for _ in observation_ids) if observation_ids else "0"
            query_counts = f"""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN label = 1 THEN 1 ELSE 0 END) as buggy,
                SUM(CASE WHEN label = 0 THEN 1 ELSE 0 END) as non_buggy,
                SUM(CASE WHEN label = -1 THEN 1 ELSE 0 END) as uncertain,
                COUNT(DISTINCT repository_id) as repo_cnt
            FROM observations
            WHERE id IN ({placeholders});
            """
            counts = conn.execute(query_counts, observation_ids if observation_ids else [0]).fetchone()

            insert_sql = """
            INSERT INTO datasets (
                name, version, description, granularity, repository_count,
                total_count, buggy_count, non_buggy_count, uncertain_count,
                feature_names, feature_schema_version, export_path
            )
            VALUES (?, ?, ?, 'method', ?, ?, ?, ?, ?, ?, '1.0.0', ?)
            RETURNING id;
            """
            cursor = conn.execute(
                insert_sql,
                (
                    name,
                    version,
                    description,
                    counts["repo_cnt"] if counts else 0,
                    counts["total"] if counts else 0,
                    counts["buggy"] if counts and counts["buggy"] else 0,
                    counts["non_buggy"] if counts and counts["non_buggy"] else 0,
                    counts["uncertain"] if counts and counts["uncertain"] else 0,
                    json.dumps(feature_names),
                    export_path,
                ),
            )
            dataset_id = cursor.fetchone()["id"]

            link_sql = "INSERT OR IGNORE INTO dataset_observations (dataset_id, observation_id) VALUES (?, ?)"
            conn.executemany(link_sql, [(dataset_id, oid) for oid in observation_ids])

            return dataset_id

    def create_class_dataset(
        self,
        name: str,
        version: str,
        description: str,
        class_observation_ids: List[int],
        feature_names: List[str],
        feature_schema_version: str = "3.0.0",
        export_path: Optional[str] = None,
        manifest_path: Optional[str] = None,
        sha256_checksum: Optional[str] = None,
        overwrite: bool = False,
    ) -> int:
        """Create or replace a versioned class-level dataset snapshot."""
        with self.db.session() as conn:
            if overwrite:
                existing = conn.execute("SELECT id FROM datasets WHERE name = ?", (name,)).fetchone()
                if existing:
                    conn.execute("DELETE FROM dataset_class_observations WHERE dataset_id = ?", (existing["id"],))
                    conn.execute("DELETE FROM datasets WHERE id = ?", (existing["id"],))

            placeholders = ",".join("?" for _ in class_observation_ids) if class_observation_ids else "0"
            query_counts = f"""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN label = 1 THEN 1 ELSE 0 END) as buggy,
                SUM(CASE WHEN label = 0 THEN 1 ELSE 0 END) as non_buggy,
                SUM(CASE WHEN label = -1 THEN 1 ELSE 0 END) as uncertain,
                COUNT(DISTINCT repository_id) as repo_cnt
            FROM class_observations
            WHERE id IN ({placeholders});
            """
            counts = conn.execute(query_counts, class_observation_ids if class_observation_ids else [0]).fetchone()

            insert_sql = """
            INSERT INTO datasets (
                name, version, description, granularity, repository_count,
                total_count, buggy_count, non_buggy_count, uncertain_count,
                feature_names, feature_schema_version, export_path, manifest_path, sha256_checksum
            )
            VALUES (?, ?, ?, 'class', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id;
            """
            cursor = conn.execute(
                insert_sql,
                (
                    name,
                    version,
                    description,
                    counts["repo_cnt"] if counts else 0,
                    counts["total"] if counts else 0,
                    counts["buggy"] if counts and counts["buggy"] else 0,
                    counts["non_buggy"] if counts and counts["non_buggy"] else 0,
                    counts["uncertain"] if counts and counts["uncertain"] else 0,
                    json.dumps(feature_names),
                    feature_schema_version,
                    export_path,
                    manifest_path,
                    sha256_checksum,
                ),
            )
            dataset_id = cursor.fetchone()["id"]
            link_sql = "INSERT OR IGNORE INTO dataset_class_observations (dataset_id, class_observation_id) VALUES (?, ?)"
            conn.executemany(link_sql, [(dataset_id, oid) for oid in class_observation_ids])
            return dataset_id

    def update_dataset_export_metadata(
        self,
        dataset_id: int,
        export_path: str,
        manifest_path: Optional[str] = None,
        sha256_checksum: Optional[str] = None,
    ) -> None:
        with self.db.session() as conn:
            conn.execute(
                "UPDATE datasets SET export_path = ?, manifest_path = COALESCE(?, manifest_path), sha256_checksum = COALESCE(?, sha256_checksum) WHERE id = ?",
                (export_path, manifest_path, sha256_checksum, dataset_id),
            )

    def list_datasets(self) -> List[Dict[str, Any]]:
        with self.db.session() as conn:
            rows = conn.execute("SELECT * FROM datasets ORDER BY created_at DESC, id DESC").fetchall()
            return [dict(r) for r in rows]

    def get_dataset(self, dataset_id: int) -> Optional[Dict[str, Any]]:
        with self.db.session() as conn:
            row = conn.execute("SELECT * FROM datasets WHERE id = ?", (dataset_id,)).fetchone()
            return dict(row) if row else None

    def get_dataset_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        with self.db.session() as conn:
            row = conn.execute("SELECT * FROM datasets WHERE name = ?", (name,)).fetchone()
            return dict(row) if row else None

    def get_dataset_dataframe_records(self, dataset_id: int) -> List[Dict[str, Any]]:
        ds = self.get_dataset(dataset_id)
        if ds and ds.get("granularity") == "class":
            return self.get_class_dataset_dataframe_records(dataset_id)

        sql = """
        SELECT
            o.id as observation_id,
            o.repository_id,
            r.full_name as repository_name,
            o.commit_sha,
            o.file_path,
            o.class_name,
            o.method_name,
            o.method_signature,
            o.label,
            o.label_confidence,
            o.evidence_category,
            f.loc,
            f.logical_loc,
            f.method_length,
            f.parameter_count,
            f.local_variable_count,
            f.statement_count,
            f.return_count,
            f.cyclomatic_complexity,
            f.max_nesting_depth,
            f.boolean_operator_count,
            f.logical_operator_count,
            f.conditional_expression_count,
            f.if_count,
            f.switch_count,
            f.loop_count,
            f.try_catch_count,
            f.throw_count,
            f.break_continue_count,
            f.method_call_count,
            f.field_access_count,
            f.property_access_count,
            f.assignment_count,
            f.object_creation_count,
            f.is_static,
            f.is_async,
            f.is_generic,
            f.num_statements,
            f.num_parameters,
            f.num_local_vars,
            f.num_returns,
            f.num_assignments,
            f.num_conditionals,
            f.num_boolean_expressions,
            f.num_logical_operators,
            f.num_loops,
            f.num_try_catch,
            f.num_throw,
            f.num_method_calls,
            f.num_field_references,
            f.num_property_references
        FROM dataset_observations do
        JOIN observations o ON do.observation_id = o.id
        JOIN repositories r ON o.repository_id = r.id
        LEFT JOIN features f ON o.id = f.observation_id
        WHERE do.dataset_id = ?
        """
        with self.db.session() as conn:
            rows = conn.execute(sql, (dataset_id,)).fetchall()
            return [dict(r) for r in rows]

    def get_class_dataset_dataframe_records(self, dataset_id: int) -> List[Dict[str, Any]]:
        feat_cols = ", ".join(f"cf.{c}" for c in CLASS_FEATURE_NAMES)
        sql = f"""
        SELECT
            co.id as class_observation_id,
            co.id as observation_id,
            co.repository_id,
            r.full_name as repository_name,
            co.commit_sha,
            co.parent_sha,
            co.bug_fix_commit_sha,
            co.bug_inducing_commit_sha,
            co.file_path,
            co.namespace_name,
            co.class_name,
            co.qualified_class_name,
            co.type_kind,
            co.start_line,
            co.end_line,
            co.is_nested,
            co.source_fingerprint,
            co.structural_fingerprint,
            co.label,
            co.label_confidence,
            co.szz_trace_count,
            co.evidence_category,
            {feat_cols}
        FROM dataset_class_observations dco
        JOIN class_observations co ON dco.class_observation_id = co.id
        JOIN repositories r ON co.repository_id = r.id
        LEFT JOIN class_features cf ON co.id = cf.class_observation_id
        WHERE dco.dataset_id = ?
        ORDER BY co.id ASC
        """
        with self.db.session() as conn:
            rows = conn.execute(sql, (dataset_id,)).fetchall()
            return [dict(r) for r in rows]

    # ---------------------------------------------------------
    # Models
    # ---------------------------------------------------------
    def save_model_record(
        self,
        name: str,
        algorithm: str,
        dataset_id: Optional[int],
        parameters: Dict[str, Any],
        metrics: Dict[str, Any],
        feature_names: List[str],
        model_file_path: str,
        version: str = "1.0.0",
        granularity: str = "method",
        dataset_version: Optional[str] = None,
        decision_threshold: float = 0.50,
        threshold_selection_criterion: Optional[str] = None,
    ) -> int:
        sql = """
        INSERT INTO models (
            name, algorithm, version, granularity, dataset_id, dataset_version,
            decision_threshold, threshold_selection_criterion,
            parameters_json, metrics_json, feature_names_json, model_file_path
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            algorithm = excluded.algorithm,
            version = excluded.version,
            granularity = excluded.granularity,
            dataset_id = COALESCE(excluded.dataset_id, models.dataset_id),
            dataset_version = COALESCE(excluded.dataset_version, models.dataset_version),
            decision_threshold = excluded.decision_threshold,
            threshold_selection_criterion = COALESCE(excluded.threshold_selection_criterion, models.threshold_selection_criterion),
            parameters_json = excluded.parameters_json,
            metrics_json = excluded.metrics_json,
            feature_names_json = excluded.feature_names_json,
            model_file_path = excluded.model_file_path
        RETURNING id;
        """
        with self.db.session() as conn:
            cursor = conn.execute(
                sql,
                (
                    name,
                    algorithm,
                    version,
                    granularity,
                    dataset_id,
                    dataset_version,
                    decision_threshold,
                    threshold_selection_criterion,
                    json.dumps(parameters),
                    json.dumps(metrics),
                    json.dumps(feature_names),
                    model_file_path,
                ),
            )
            return cursor.fetchone()["id"]

    def list_models(self) -> List[Dict[str, Any]]:
        with self.db.session() as conn:
            rows = conn.execute("SELECT * FROM models ORDER BY created_at DESC, id DESC").fetchall()
            return [dict(r) for r in rows]

    def get_model(self, model_id: int) -> Optional[Dict[str, Any]]:
        with self.db.session() as conn:
            row = conn.execute("SELECT * FROM models WHERE id = ?", (model_id,)).fetchone()
            return dict(row) if row else None

    def get_model_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        with self.db.session() as conn:
            row = conn.execute("SELECT * FROM models WHERE name = ?", (name,)).fetchone()
            return dict(row) if row else None

    # ---------------------------------------------------------
    # Predictions History
    # ---------------------------------------------------------
    def save_prediction(
        self,
        model_name: str,
        method_name: str,
        metrics: Dict[str, Any],
        predicted_label: int,
        risk_score: float,
        risk_category: str,
        model_id: Optional[int] = None,
        class_name: Optional[str] = None,
        file_name: Optional[str] = None,
        source_code: Optional[str] = None,
        granularity: str = "method",
        dataset_version: Optional[str] = None,
        decision_threshold: float = 0.50,
        namespace_name: Optional[str] = None,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
        method_count: Optional[int] = None,
        loc: Optional[int] = None,
        cyclomatic_complexity: Optional[int] = None,
        file_summary_json: Optional[str] = None,
    ) -> int:
        sql = """
        INSERT INTO predictions (
            model_id, model_name, granularity, dataset_version, decision_threshold,
            method_name, class_name, namespace_name, file_name,
            start_line, end_line, method_count, loc, cyclomatic_complexity,
            source_code, metrics_json, file_summary_json,
            predicted_label, risk_score, risk_category
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING id;
        """
        with self.db.session() as conn:
            if model_id is not None:
                exists = conn.execute("SELECT 1 FROM models WHERE id = ?", (model_id,)).fetchone()
                if not exists:
                    model_id = None

            cursor = conn.execute(
                sql,
                (
                    model_id,
                    model_name,
                    granularity,
                    dataset_version,
                    decision_threshold,
                    method_name,
                    class_name,
                    namespace_name,
                    file_name,
                    start_line,
                    end_line,
                    method_count,
                    loc,
                    cyclomatic_complexity,
                    source_code,
                    json.dumps(metrics),
                    file_summary_json,
                    predicted_label,
                    risk_score,
                    risk_category,
                ),
            )
            return cursor.fetchone()["id"]

    def list_predictions(
        self,
        limit: int = 100,
        offset: int = 0,
        model_id: Optional[int] = None,
        granularity: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM predictions WHERE 1=1"
        params: List[Any] = []
        if model_id is not None:
            sql += " AND model_id = ?"
            params.append(model_id)
        if granularity is not None:
            sql += " AND granularity = ?"
            params.append(granularity)
        sql += " ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self.db.session() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]

    def clear_predictions(self) -> int:
        with self.db.session() as conn:
            cursor = conn.execute("DELETE FROM predictions;")
            return cursor.rowcount

    # ---------------------------------------------------------
    # Global Statistics
    # ---------------------------------------------------------
    def get_summary_statistics(self) -> Dict[str, Any]:
        with self.db.session() as conn:
            repo_count = conn.execute("SELECT COUNT(*) as cnt FROM repositories").fetchone()["cnt"]
            repo_selected = conn.execute("SELECT COUNT(*) as cnt FROM repositories WHERE is_selected = 1").fetchone()["cnt"]
            repo_processed = conn.execute(
                "SELECT COUNT(*) as cnt FROM repositories WHERE class_observations_count > 0"
            ).fetchone()["cnt"]
            cloned_count = conn.execute("SELECT COUNT(*) as cnt FROM repositories WHERE is_cloned = 1").fetchone()["cnt"]
            commits_count = conn.execute("SELECT COUNT(*) as cnt FROM commits").fetchone()["cnt"]
            bug_commits_count = conn.execute("SELECT COUNT(*) as cnt FROM commits WHERE is_bug_fix = 1").fetchone()["cnt"]
            szz_count = conn.execute("SELECT COUNT(*) as cnt FROM szz_results").fetchone()["cnt"]
            obs_count = conn.execute("SELECT COUNT(*) as cnt FROM observations").fetchone()["cnt"]
            buggy_count = conn.execute("SELECT COUNT(*) as cnt FROM observations WHERE label = 1").fetchone()["cnt"]
            non_buggy_count = conn.execute("SELECT COUNT(*) as cnt FROM observations WHERE label = 0").fetchone()["cnt"]
            uncertain_count = conn.execute("SELECT COUNT(*) as cnt FROM observations WHERE label = -1").fetchone()["cnt"]
            features_count = conn.execute("SELECT COUNT(*) as cnt FROM features").fetchone()["cnt"]

            file_obs_count = conn.execute("SELECT COUNT(*) as cnt FROM file_observations").fetchone()["cnt"]
            class_obs_count = conn.execute("SELECT COUNT(*) as cnt FROM class_observations").fetchone()["cnt"]
            class_buggy_count = conn.execute("SELECT COUNT(*) as cnt FROM class_observations WHERE label = 1").fetchone()["cnt"]
            class_non_buggy_count = conn.execute("SELECT COUNT(*) as cnt FROM class_observations WHERE label = 0").fetchone()["cnt"]
            class_uncertain_count = conn.execute("SELECT COUNT(*) as cnt FROM class_observations WHERE label = -1").fetchone()["cnt"]
            class_features_count = conn.execute("SELECT COUNT(*) as cnt FROM class_features WHERE status = 'success'").fetchone()["cnt"]

            datasets_count = conn.execute("SELECT COUNT(*) as cnt FROM datasets").fetchone()["cnt"]
            models_count = conn.execute("SELECT COUNT(*) as cnt FROM models").fetchone()["cnt"]
            predictions_count = conn.execute("SELECT COUNT(*) as cnt FROM predictions").fetchone()["cnt"]

            return {
                "repositories_total": repo_count,
                "repositories_selected": repo_selected,
                "repositories_processed": repo_processed,
                "repositories_cloned": cloned_count,
                "commits_total": commits_count,
                "commits_bug_fix": bug_commits_count,
                "szz_bics_total": szz_count,
                "observations_total": obs_count,
                "observations_buggy": buggy_count,
                "observations_non_buggy": non_buggy_count,
                "observations_uncertain": uncertain_count,
                "features_extracted": features_count,
                "file_observations_total": file_obs_count,
                "class_observations_total": class_obs_count,
                "class_observations_buggy": class_buggy_count,
                "class_observations_non_buggy": class_non_buggy_count,
                "class_observations_uncertain": class_uncertain_count,
                "class_features_extracted": class_features_count,
                "datasets_count": datasets_count,
                "models_count": models_count,
                "predictions_count": predictions_count,
            }

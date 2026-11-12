"""Database repository providing typed CRUD operations."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Set
from src.database.connection import Database


class RepositoryDB:
    """Data Access Object for all bug detection domain entities."""

    def __init__(self, db: Database) -> None:
        self.db = db

    # ---------------------------------------------------------
    # Repositories
    # ---------------------------------------------------------
    def upsert_repository(self, repo_data: Dict[str, Any]) -> int:
        """Insert or update a repository record and return its ID."""
        sql = """
        INSERT INTO repositories (
            full_name, name, owner, url, description, license,
            default_branch, stars, forks, size_kb, is_cloned,
            local_path, status, last_sync_at, updated_at
        ) VALUES (
            :full_name, :name, :owner, :url, :description, :license,
            :default_branch, :stars, :forks, :size_kb, :is_cloned,
            :local_path, :status, :last_sync_at, CURRENT_TIMESTAMP
        )
        ON CONFLICT(full_name) DO UPDATE SET
            description = COALESCE(excluded.description, repositories.description),
            license = COALESCE(excluded.license, repositories.license),
            stars = COALESCE(excluded.stars, repositories.stars),
            forks = COALESCE(excluded.forks, repositories.forks),
            size_kb = COALESCE(excluded.size_kb, repositories.size_kb),
            is_cloned = COALESCE(excluded.is_cloned, repositories.is_cloned),
            local_path = COALESCE(excluded.local_path, repositories.local_path),
            status = COALESCE(excluded.status, repositories.status),
            last_sync_at = COALESCE(excluded.last_sync_at, repositories.last_sync_at),
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

    def list_repositories(self) -> List[Dict[str, Any]]:
        with self.db.session() as conn:
            rows = conn.execute("SELECT * FROM repositories ORDER BY stars DESC, collected_at DESC").fetchall()
            return [dict(r) for r in rows]

    def update_repository_status(
        self,
        repo_id: int,
        status: str,
        is_cloned: Optional[bool] = None,
        local_path: Optional[str] = None,
        last_sync_at: Optional[str] = None,
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

    # ---------------------------------------------------------
    # Commits
    # ---------------------------------------------------------
    def upsert_commit(self, commit_data: Dict[str, Any]) -> int:
        """Insert or ignore a commit record and return its ID."""
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
        payload = {
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
        with self.db.session() as conn:
            cursor = conn.execute(sql, payload)
            row = cursor.fetchone()
            return row["id"] if row else -1

    def batch_insert_commits(self, commits_list: List[Dict[str, Any]]) -> int:
        """Insert a batch of commits efficiently."""
        inserted = 0
        for c in commits_list:
            cid = self.upsert_commit(c)
            if cid > 0:
                inserted += 1
        return inserted

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
    # Observations
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

    # ---------------------------------------------------------
    # Features
    # ---------------------------------------------------------
    def upsert_features(self, feat_data: Dict[str, Any]) -> int:
        """Insert or replace features extracted for an observation."""
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
        # Map aliases between metric naming conventions so both legacy and modern columns stay populated
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
        """Get observations that have not had features successfully extracted yet."""
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

    # ---------------------------------------------------------
    # Datasets
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
                SUM(CASE WHEN label = -1 THEN 1 ELSE 0 END) as uncertain
            FROM observations
            WHERE id IN ({placeholders});
            """
            counts = conn.execute(query_counts, observation_ids if observation_ids else [0]).fetchone()

            insert_sql = """
            INSERT INTO datasets (name, version, description, total_count, buggy_count, non_buggy_count, uncertain_count, feature_names, export_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id;
            """
            cursor = conn.execute(
                insert_sql,
                (
                    name,
                    version,
                    description,
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

    def list_datasets(self) -> List[Dict[str, Any]]:
        with self.db.session() as conn:
            rows = conn.execute("SELECT * FROM datasets ORDER BY created_at DESC").fetchall()
            return [dict(r) for r in rows]

    def get_dataset(self, dataset_id: int) -> Optional[Dict[str, Any]]:
        with self.db.session() as conn:
            row = conn.execute("SELECT * FROM datasets WHERE id = ?", (dataset_id,)).fetchone()
            return dict(row) if row else None

    def get_dataset_dataframe_records(self, dataset_id: int) -> List[Dict[str, Any]]:
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
    ) -> int:
        sql = """
        INSERT INTO models (name, algorithm, dataset_id, parameters_json, metrics_json, feature_names_json, model_file_path)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        RETURNING id;
        """
        with self.db.session() as conn:
            cursor = conn.execute(
                sql,
                (
                    name,
                    algorithm,
                    dataset_id,
                    json.dumps(parameters),
                    json.dumps(metrics),
                    json.dumps(feature_names),
                    model_file_path,
                ),
            )
            return cursor.fetchone()["id"]

    def list_models(self) -> List[Dict[str, Any]]:
        with self.db.session() as conn:
            rows = conn.execute("SELECT * FROM models ORDER BY created_at DESC").fetchall()
            return [dict(r) for r in rows]

    def get_model(self, model_id: int) -> Optional[Dict[str, Any]]:
        with self.db.session() as conn:
            row = conn.execute("SELECT * FROM models WHERE id = ?", (model_id,)).fetchone()
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
    ) -> int:
        sql = """
        INSERT INTO predictions (
            model_id, model_name, method_name, class_name, file_name,
            source_code, metrics_json, predicted_label, risk_score, risk_category
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING id;
        """
        with self.db.session() as conn:
            # If model_id does not exist in models table, set to None to satisfy FK
            if model_id is not None:
                exists = conn.execute("SELECT 1 FROM models WHERE id = ?", (model_id,)).fetchone()
                if not exists:
                    model_id = None

            cursor = conn.execute(
                sql,
                (
                    model_id,
                    model_name,
                    method_name,
                    class_name,
                    file_name,
                    source_code,
                    json.dumps(metrics),
                    predicted_label,
                    risk_score,
                    risk_category,
                ),
            )
            return cursor.fetchone()["id"]

    def list_predictions(self, limit: int = 100, offset: int = 0, model_id: Optional[int] = None) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM predictions"
        params: List[Any] = []
        if model_id is not None:
            sql += " WHERE model_id = ?"
            params.append(model_id)
        sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
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
            cloned_count = conn.execute("SELECT COUNT(*) as cnt FROM repositories WHERE is_cloned = 1").fetchone()["cnt"]
            commits_count = conn.execute("SELECT COUNT(*) as cnt FROM commits").fetchone()["cnt"]
            bug_commits_count = conn.execute("SELECT COUNT(*) as cnt FROM commits WHERE is_bug_fix = 1").fetchone()["cnt"]
            szz_count = conn.execute("SELECT COUNT(*) as cnt FROM szz_results").fetchone()["cnt"]
            obs_count = conn.execute("SELECT COUNT(*) as cnt FROM observations").fetchone()["cnt"]
            buggy_count = conn.execute("SELECT COUNT(*) as cnt FROM observations WHERE label = 1").fetchone()["cnt"]
            non_buggy_count = conn.execute("SELECT COUNT(*) as cnt FROM observations WHERE label = 0").fetchone()["cnt"]
            uncertain_count = conn.execute("SELECT COUNT(*) as cnt FROM observations WHERE label = -1").fetchone()["cnt"]
            features_count = conn.execute("SELECT COUNT(*) as cnt FROM features").fetchone()["cnt"]
            datasets_count = conn.execute("SELECT COUNT(*) as cnt FROM datasets").fetchone()["cnt"]
            models_count = conn.execute("SELECT COUNT(*) as cnt FROM models").fetchone()["cnt"]
            predictions_count = conn.execute("SELECT COUNT(*) as cnt FROM predictions").fetchone()["cnt"]

            return {
                "repositories_total": repo_count,
                "repositories_cloned": cloned_count,
                "commits_total": commits_count,
                "commits_bug_fix": bug_commits_count,
                "szz_bics_total": szz_count,
                "observations_total": obs_count,
                "observations_buggy": buggy_count,
                "observations_non_buggy": non_buggy_count,
                "observations_uncertain": uncertain_count,
                "features_extracted": features_count,
                "datasets_count": datasets_count,
                "models_count": models_count,
                "predictions_count": predictions_count,
            }

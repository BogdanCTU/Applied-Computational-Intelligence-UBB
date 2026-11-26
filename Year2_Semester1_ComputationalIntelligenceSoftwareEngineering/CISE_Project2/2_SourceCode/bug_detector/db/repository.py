"""Transactional CRUD and query operations for CISE Bug Detector v5.0.0."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from bug_detector.db.connection import DatabaseManager, run_migrations


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


class BugDetectorRepository:
    """High-level SQLite repository encapsulating all v5 persistence operations."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db = db_manager
        run_migrations(self.db.db_path)

    @staticmethod
    def ensure_source_blob(
        conn: Any,
        raw_source: str,
        normalized_source: str | None = None,
        source_hash: str | None = None,
    ) -> str:
        digest = source_hash or sha256_text(raw_source)
        conn.execute(
            """
            INSERT OR IGNORE INTO source_blobs
                (source_hash, raw_source, normalized_source, byte_length, line_count)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                digest,
                raw_source,
                normalized_source,
                len(raw_source.encode("utf-8", errors="replace")),
                raw_source.count("\n") + 1,
            ),
        )
        if normalized_source is not None:
            conn.execute(
                "UPDATE source_blobs SET normalized_source = COALESCE(normalized_source, ?) WHERE source_hash = ?",
                (normalized_source, digest),
            )
        return digest

    def upsert_repository(
        self,
        repository_id: str,
        full_name: str,
        repository_url: str,
        source_origin: str,
        default_branch: str | None = None,
        stars: int = 0,
        local_path: str | None = None,
    ) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO repositories
                    (repository_id, full_name, repository_url, source_origin, default_branch, stars, local_path)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(repository_id) DO UPDATE SET
                    full_name = excluded.full_name,
                    repository_url = excluded.repository_url,
                    stars = MAX(repositories.stars, excluded.stars),
                    local_path = COALESCE(excluded.local_path, repositories.local_path)
                """,
                (repository_id, full_name, repository_url, source_origin, default_branch, stars, local_path),
            )

    def register_dataset_version(
        self,
        dataset_version: str,
        description: str,
        stats: dict[str, Any],
        dataset_sha256: str | None = None,
        parquet_path: str | None = None,
        csv_path: str | None = None,
        audit_report_path: str | None = None,
    ) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO dataset_versions (
                    dataset_version, description, total_records_collected, valid_records,
                    invalid_records, bug_count, clean_count, repository_count,
                    dataset_sha256, parquet_path, csv_path, audit_report_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(dataset_version) DO UPDATE SET
                    description = excluded.description,
                    total_records_collected = excluded.total_records_collected,
                    valid_records = excluded.valid_records,
                    invalid_records = excluded.invalid_records,
                    bug_count = excluded.bug_count,
                    clean_count = excluded.clean_count,
                    repository_count = excluded.repository_count,
                    dataset_sha256 = excluded.dataset_sha256,
                    parquet_path = excluded.parquet_path,
                    csv_path = excluded.csv_path,
                    audit_report_path = excluded.audit_report_path
                """,
                (
                    dataset_version,
                    description,
                    int(stats.get("total_records_collected", 0)),
                    int(stats.get("valid_records", 0)),
                    int(stats.get("invalid_records", 0)),
                    int(stats.get("bug_count", 0)),
                    int(stats.get("clean_count", 0)),
                    int(stats.get("repository_count", 0)),
                    dataset_sha256,
                    parquet_path,
                    csv_path,
                    audit_report_path,
                ),
            )

    def replace_dataset_contents(
        self,
        dataset_version: str,
        description: str,
        repositories: list[dict[str, Any]],
        samples: list[dict[str, Any]],
        exclusions: list[dict[str, Any]],
        stats: dict[str, Any],
        dataset_sha256: str | None = None,
        parquet_path: str | None = None,
        csv_path: str | None = None,
        audit_report_path: str | None = None,
    ) -> None:
        """Persist an entire dataset version, samples, features, and exclusions atomically."""
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO dataset_versions (
                    dataset_version, description, total_records_collected, valid_records,
                    invalid_records, bug_count, clean_count, repository_count,
                    dataset_sha256, parquet_path, csv_path, audit_report_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(dataset_version) DO UPDATE SET
                    description = excluded.description,
                    total_records_collected = excluded.total_records_collected,
                    valid_records = excluded.valid_records,
                    invalid_records = excluded.invalid_records,
                    bug_count = excluded.bug_count,
                    clean_count = excluded.clean_count,
                    repository_count = excluded.repository_count,
                    dataset_sha256 = excluded.dataset_sha256,
                    parquet_path = excluded.parquet_path,
                    csv_path = excluded.csv_path,
                    audit_report_path = excluded.audit_report_path
                """,
                (
                    dataset_version,
                    description,
                    int(stats.get("total_records_collected", 0)),
                    int(stats.get("valid_records", 0)),
                    int(stats.get("invalid_records", 0)),
                    int(stats.get("bug_count", 0)),
                    int(stats.get("clean_count", 0)),
                    int(stats.get("repository_count", 0)),
                    dataset_sha256,
                    parquet_path,
                    csv_path,
                    audit_report_path,
                ),
            )

            conn.execute("DELETE FROM dataset_samples WHERE dataset_version = ?", (dataset_version,))
            conn.execute("DELETE FROM dataset_exclusions WHERE dataset_version = ?", (dataset_version,))

            for repo in repositories:
                conn.execute(
                    """
                    INSERT INTO repositories
                        (repository_id, full_name, repository_url, source_origin, default_branch, stars, local_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(repository_id) DO UPDATE SET
                        full_name = excluded.full_name,
                        repository_url = excluded.repository_url,
                        stars = MAX(repositories.stars, excluded.stars),
                        local_path = COALESCE(excluded.local_path, repositories.local_path)
                    """,
                    (
                        repo["repository_id"],
                        repo.get("full_name") or repo["repository_id"],
                        repo.get("repository_url") or "",
                        repo.get("source_origin") or "unknown",
                        repo.get("default_branch"),
                        int(repo.get("stars", 0)),
                        repo.get("local_path"),
                    ),
                )

            for s in samples:
                source_hash = self.ensure_source_blob(
                    conn,
                    raw_source=s["source_code"],
                    normalized_source=s.get("normalized_source"),
                    source_hash=s.get("source_hash"),
                )
                conn.execute(
                    """
                    INSERT OR IGNORE INTO commits
                        (repository_id, commit_sha, parent_commit_sha, commit_message, author_date, is_bug_fix, issue_or_pr_ref)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        s["repository_id"],
                        s["commit_sha"],
                        s.get("parent_commit_sha"),
                        s.get("commit_message"),
                        s.get("commit_timestamp"),
                        1 if s["label"] == 1 else 0,
                        s.get("bug_fix_reference"),
                    ),
                )
                cur_bf = conn.execute(
                    """
                    INSERT INTO bug_fix_records
                        (repository_id, commit_sha, parent_commit_sha, file_path, bug_type, severity, bug_fix_reference, source_origin)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        s["repository_id"],
                        s["commit_sha"],
                        s.get("parent_commit_sha"),
                        s["file_path"],
                        s["bug_type"],
                        s.get("severity"),
                        s.get("bug_fix_reference"),
                        s["label_source"],
                    ),
                )
                bug_fix_id = cur_bf.lastrowid
                cur_m = conn.execute(
                    """
                    INSERT INTO methods
                        (repository_id, file_path, class_name, type_kind, method_name, method_signature,
                         start_line, end_line, is_constructor, is_static, is_async, is_generic,
                         is_expression_bodied, source_hash, structural_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        s["repository_id"],
                        s["file_path"],
                        s["class_name"],
                        s.get("type_kind", "class"),
                        s["method_name"],
                        s["method_signature"],
                        int(s.get("start_line", 1)),
                        int(s.get("end_line", 1)),
                        int(bool(s.get("is_constructor", False))),
                        int(bool(s.get("is_static", False))),
                        int(bool(s.get("is_async", False))),
                        int(bool(s.get("is_generic", False))),
                        int(bool(s.get("is_expression_bodied", False))),
                        source_hash,
                        s["structural_hash"],
                    ),
                )
                method_id = cur_m.lastrowid
                conn.execute(
                    """
                    INSERT INTO dataset_samples (
                        sample_id, dataset_version, repository_id, method_id, bug_fix_id,
                        pair_id, commit_sha, parent_commit_sha, commit_timestamp, file_path,
                        class_name, method_name, method_signature, source_hash, structural_hash,
                        label, label_source, verification_status, bug_type, bug_fix_reference,
                        extraction_mode, split_partition, collection_timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        s["sample_id"],
                        dataset_version,
                        s["repository_id"],
                        method_id,
                        bug_fix_id,
                        s.get("pair_id"),
                        s["commit_sha"],
                        s.get("parent_commit_sha"),
                        s.get("commit_timestamp"),
                        s["file_path"],
                        s["class_name"],
                        s["method_name"],
                        s["method_signature"],
                        source_hash,
                        s["structural_hash"],
                        int(s["label"]),
                        s["label_source"],
                        s["verification_status"],
                        s["bug_type"],
                        s.get("bug_fix_reference"),
                        s.get("extraction_mode", "file"),
                        s.get("split_partition", "unassigned"),
                        s["collection_timestamp"],
                    ),
                )
                if "features_payload" in s and s["features_payload"] is not None:
                    fp = s["features_payload"]
                    conn.execute(
                        """
                        INSERT INTO feature_extractions (
                            sample_id, extractor_version, semantic_model_available, cfg_available,
                            dfg_available, extraction_failed, tokens_json, api_calls_json,
                            lexical_json, ast_json, cfg_json, dfg_json, structural_json, warnings_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            s["sample_id"],
                            fp.get("extractor_version", "1.0.0"),
                            int(bool(fp.get("semantic_model_available", False))),
                            int(bool(fp.get("cfg_available", False))),
                            int(bool(fp.get("dfg_available", False))),
                            int(bool(fp.get("extraction_failed", False))),
                            json.dumps(fp.get("tokens_normalized", [])),
                            json.dumps(fp.get("api_calls", [])),
                            json.dumps(fp.get("lexical_metrics", {})),
                            json.dumps(fp.get("ast_metrics", {})),
                            json.dumps(fp.get("cfg_metrics", {})),
                            json.dumps(fp.get("dfg_metrics", {})),
                            json.dumps(fp.get("structural_metrics", {})),
                            json.dumps(fp.get("extraction_warnings", [])),
                        ),
                    )

            for ex in exclusions:
                conn.execute(
                    """
                    INSERT INTO dataset_exclusions
                        (dataset_version, source_origin, repository_id, external_ref, file_path, method_name, exclusion_reason, details)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        dataset_version,
                        ex.get("source_origin", "unknown"),
                        ex.get("repository_id"),
                        ex.get("external_ref"),
                        ex.get("file_path"),
                        ex.get("method_name"),
                        ex["exclusion_reason"],
                        ex.get("details"),
                    ),
                )

    def update_sample_partitions(self, dataset_version: str, sample_partitions: dict[str, str]) -> None:
        with self.db.transaction() as conn:
            conn.executemany(
                "UPDATE dataset_samples SET split_partition = ? WHERE dataset_version = ? AND sample_id = ?",
                [(part, dataset_version, sid) for sid, part in sample_partitions.items()],
            )

    def save_experiment(self, record: dict[str, Any]) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO training_experiments (
                    experiment_id, dataset_version, experiment_code, algorithm,
                    feature_groups_json, hyperparameters_json, cv_metrics_json,
                    test_metrics_json, hard_negative_metrics_json, temporal_metrics_json,
                    duration_seconds, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(experiment_id) DO UPDATE SET
                    cv_metrics_json = excluded.cv_metrics_json,
                    test_metrics_json = excluded.test_metrics_json,
                    hard_negative_metrics_json = excluded.hard_negative_metrics_json,
                    temporal_metrics_json = excluded.temporal_metrics_json,
                    duration_seconds = excluded.duration_seconds,
                    status = excluded.status
                """,
                (
                    record["experiment_id"],
                    record["dataset_version"],
                    record["experiment_code"],
                    record["algorithm"],
                    json.dumps(record["feature_groups"]),
                    json.dumps(record["hyperparameters"]),
                    json.dumps(record["cv_metrics"]),
                    json.dumps(record["test_metrics"]),
                    json.dumps(record.get("hard_negative_metrics")) if record.get("hard_negative_metrics") else None,
                    json.dumps(record.get("temporal_metrics")) if record.get("temporal_metrics") else None,
                    float(record["duration_seconds"]),
                    record.get("status", "COMPLETED"),
                ),
            )

    def register_model_version(self, record: dict[str, Any], activate: bool = False) -> None:
        with self.db.transaction() as conn:
            if activate:
                conn.execute("UPDATE model_versions SET is_active = 0")
            conn.execute(
                """
                INSERT INTO model_versions (
                    model_version, experiment_id, dataset_version, dataset_sha256,
                    algorithm, experiment_code, feature_groups_json, feature_schema_json,
                    hyperparameters_json, threshold_low, threshold_center, threshold_high,
                    calibration_method, artifact_path, manifest_path, dependency_versions_json, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(model_version) DO UPDATE SET
                    experiment_id = excluded.experiment_id,
                    threshold_low = excluded.threshold_low,
                    threshold_center = excluded.threshold_center,
                    threshold_high = excluded.threshold_high,
                    artifact_path = excluded.artifact_path,
                    manifest_path = excluded.manifest_path,
                    is_active = excluded.is_active
                """,
                (
                    record["model_version"],
                    record.get("experiment_id"),
                    record["dataset_version"],
                    record.get("dataset_sha256"),
                    record["algorithm"],
                    record["experiment_code"],
                    json.dumps(record["feature_groups"]),
                    json.dumps(record["feature_schema"]),
                    json.dumps(record["hyperparameters"]),
                    float(record["threshold_low"]),
                    float(record["threshold_center"]),
                    float(record["threshold_high"]),
                    record["calibration_method"],
                    record["artifact_path"],
                    record["manifest_path"],
                    json.dumps(record["dependency_versions"]),
                    1 if activate else 0,
                ),
            )

    def set_active_model(self, model_version: str) -> None:
        with self.db.transaction() as conn:
            exists = conn.execute(
                "SELECT 1 FROM model_versions WHERE model_version = ?", (model_version,)
            ).fetchone()
            if not exists:
                raise ValueError(f"Unknown model_version: {model_version}")
            conn.execute("UPDATE model_versions SET is_active = 0")
            conn.execute(
                "UPDATE model_versions SET is_active = 1 WHERE model_version = ?",
                (model_version,),
            )

    def save_evaluation_result(self, model_version: str, split_name: str, metrics: dict[str, Any]) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO evaluation_results (
                    model_version, evaluation_split, sample_count, bug_count, clean_count,
                    repository_count, accuracy, precision_score, recall_score, f1_score,
                    specificity, fpr, fnr, roc_auc, pr_auc, brier_score,
                    uncertain_count, uncertain_rate, selective_precision, selective_recall,
                    selective_f1, selective_fpr, confusion_matrix_json, metrics_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    model_version,
                    split_name,
                    int(metrics.get("sample_count", 0)),
                    int(metrics.get("bug_count", 0)),
                    int(metrics.get("clean_count", 0)),
                    int(metrics.get("repository_count", 0)),
                    metrics.get("accuracy"),
                    metrics.get("precision"),
                    metrics.get("recall"),
                    metrics.get("f1"),
                    metrics.get("specificity"),
                    metrics.get("fpr"),
                    metrics.get("fnr"),
                    metrics.get("roc_auc"),
                    metrics.get("pr_auc"),
                    metrics.get("brier_score"),
                    int(metrics.get("uncertain_count", 0)),
                    float(metrics.get("uncertain_rate", 0.0)),
                    metrics.get("selective_precision"),
                    metrics.get("selective_recall"),
                    metrics.get("selective_f1"),
                    metrics.get("selective_fpr"),
                    json.dumps(metrics.get("confusion_matrix", [])),
                    json.dumps(metrics),
                ),
            )

    def save_detection_run(
        self,
        run_id: str,
        model_version: str,
        input_mode: str,
        file_name: str,
        source_code: str,
        analysis_status: str,
        syntax_error_count: int,
        predictions: list[dict[str, Any]],
        error_message: str | None = None,
    ) -> None:
        with self.db.transaction() as conn:
            blob_hash = self.ensure_source_blob(conn, raw_source=source_code)
            bug_count = sum(1 for p in predictions if p["classification"] == "BUG")
            clean_count = sum(1 for p in predictions if p["classification"] == "CLEAN")
            uncertain_count = sum(1 for p in predictions if p["classification"] == "UNCERTAIN")
            conn.execute(
                """
                INSERT INTO detection_runs (
                    run_id, model_version, input_mode, file_name, source_hash,
                    analysis_status, syntax_error_count, method_count,
                    bug_count, clean_count, uncertain_count, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    model_version,
                    input_mode,
                    file_name,
                    blob_hash,
                    analysis_status,
                    int(syntax_error_count),
                    len(predictions),
                    bug_count,
                    clean_count,
                    uncertain_count,
                    error_message,
                ),
            )
            for p in predictions:
                conn.execute(
                    """
                    INSERT INTO prediction_results (
                        run_id, file_name, class_name, method_name, method_signature,
                        start_line, end_line, classification, probability,
                        threshold_low, threshold_center, threshold_high,
                        uncertainty_status, feature_extraction_status, suspicious_rank,
                        historical_match_sample_id, historical_provenance_json,
                        local_evidence_json, method_source_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        p["file_name"],
                        p["class_name"],
                        p["method_name"],
                        p["method_signature"],
                        int(p["start_line"]),
                        int(p["end_line"]),
                        p["classification"],
                        p.get("probability"),
                        float(p["threshold_low"]),
                        float(p["threshold_center"]),
                        float(p["threshold_high"]),
                        p["uncertainty_status"],
                        p["feature_extraction_status"],
                        p.get("suspicious_rank"),
                        p.get("historical_match_sample_id"),
                        json.dumps(p["historical_provenance"]) if p.get("historical_provenance") else None,
                        json.dumps(p["local_evidence"]) if p.get("local_evidence") else None,
                        p["method_source_hash"],
                    ),
                )

    def lookup_historical_provenance(self, source_hash: str) -> list[dict[str, Any]]:
        with self.db.connect() as conn:
            rows = conn.execute(
                """
                SELECT s.sample_id, s.dataset_version, s.repository_id, r.repository_url,
                       s.commit_sha, s.file_path, s.class_name, s.method_name,
                       s.label, s.label_source, s.verification_status, s.bug_type, s.bug_fix_reference
                FROM dataset_samples s
                JOIN repositories r ON r.repository_id = s.repository_id
                WHERE s.source_hash = ?
                LIMIT 10
                """,
                (source_hash,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_active_model(self) -> dict[str, Any] | None:
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT * FROM model_versions WHERE is_active = 1 ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
            return dict(row) if row else None

    def list_dataset_versions(self) -> list[dict[str, Any]]:
        with self.db.connect() as conn:
            return [
                dict(r)
                for r in conn.execute("SELECT * FROM dataset_versions ORDER BY created_at DESC").fetchall()
            ]

    def list_experiments(self, dataset_version: str | None = None) -> list[dict[str, Any]]:
        with self.db.connect() as conn:
            if dataset_version:
                rows = conn.execute(
                    "SELECT * FROM training_experiments WHERE dataset_version = ? ORDER BY created_at DESC",
                    (dataset_version,),
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM training_experiments ORDER BY created_at DESC").fetchall()
            return [dict(r) for r in rows]

    def list_models(self) -> list[dict[str, Any]]:
        with self.db.connect() as conn:
            return [
                dict(r)
                for r in conn.execute("SELECT * FROM model_versions ORDER BY created_at DESC").fetchall()
            ]

    def list_detection_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        with self.db.connect() as conn:
            return [
                dict(r)
                for r in conn.execute(
                    "SELECT * FROM detection_runs ORDER BY created_at DESC LIMIT ?", (limit,)
                ).fetchall()
            ]

    def query_predictions(
        self,
        classification: str | None = None,
        run_id: str | None = None,
        file_like: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        clauses = ["1=1"]
        params: list[Any] = []
        if classification and classification != "ALL":
            clauses.append("p.classification = ?")
            params.append(classification)
        if run_id and run_id != "ALL":
            clauses.append("p.run_id = ?")
            params.append(run_id)
        if file_like:
            clauses.append("p.file_name LIKE ?")
            params.append(f"%{file_like}%")
        params.append(limit)
        sql = f"""
            SELECT p.*, d.created_at, d.model_version, d.input_mode
            FROM prediction_results p
            JOIN detection_runs d ON d.run_id = p.run_id
            WHERE {' AND '.join(clauses)}
            ORDER BY p.prediction_id DESC
            LIMIT ?
        """
        with self.db.connect() as conn:
            return [dict(r) for r in conn.execute(sql, params).fetchall()]

    def query_dataset_samples(
        self,
        dataset_version: str,
        label: int | None = None,
        label_source: str | None = None,
        verification_status: str | None = None,
        bug_type: str | None = None,
        repository_id: str | None = None,
        split_partition: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[dict[str, Any]], int]:
        clauses = ["s.dataset_version = ?"]
        params: list[Any] = [dataset_version]
        if label is not None:
            clauses.append("s.label = ?")
            params.append(label)
        if label_source and label_source != "ALL":
            clauses.append("s.label_source = ?")
            params.append(label_source)
        if verification_status and verification_status != "ALL":
            clauses.append("s.verification_status = ?")
            params.append(verification_status)
        if bug_type and bug_type != "ALL":
            clauses.append("s.bug_type = ?")
            params.append(bug_type)
        if repository_id and repository_id != "ALL":
            clauses.append("s.repository_id LIKE ?")
            params.append(f"%{repository_id}%")
        if split_partition and split_partition != "ALL":
            clauses.append("s.split_partition = ?")
            params.append(split_partition)

        where_sql = " AND ".join(clauses)
        with self.db.connect() as conn:
            total = conn.execute(
                f"SELECT COUNT(*) AS c FROM dataset_samples s WHERE {where_sql}", params
            ).fetchone()["c"]
            rows = conn.execute(
                f"""
                SELECT s.*, r.repository_url, b.raw_source
                FROM dataset_samples s
                JOIN repositories r ON r.repository_id = s.repository_id
                JOIN source_blobs b ON b.source_hash = s.source_hash
                WHERE {where_sql}
                ORDER BY s.sample_id
                LIMIT ? OFFSET ?
                """,
                [*params, limit, offset],
            ).fetchall()
            return [dict(r) for r in rows], int(total)

    def get_dataset_breakdown(self, dataset_version: str) -> dict[str, Any]:
        with self.db.connect() as conn:
            by_label = [
                dict(r)
                for r in conn.execute(
                    "SELECT label, COUNT(*) AS cnt FROM dataset_samples WHERE dataset_version = ? GROUP BY label",
                    (dataset_version,),
                ).fetchall()
            ]
            by_source = [
                dict(r)
                for r in conn.execute(
                    "SELECT label_source, label, COUNT(*) AS cnt FROM dataset_samples WHERE dataset_version = ? GROUP BY label_source, label ORDER BY cnt DESC",
                    (dataset_version,),
                ).fetchall()
            ]
            by_verif = [
                dict(r)
                for r in conn.execute(
                    "SELECT verification_status, COUNT(*) AS cnt FROM dataset_samples WHERE dataset_version = ? GROUP BY verification_status ORDER BY cnt DESC",
                    (dataset_version,),
                ).fetchall()
            ]
            by_bug_type = [
                dict(r)
                for r in conn.execute(
                    "SELECT bug_type, COUNT(*) AS cnt FROM dataset_samples WHERE dataset_version = ? GROUP BY bug_type ORDER BY cnt DESC LIMIT 25",
                    (dataset_version,),
                ).fetchall()
            ]
            by_repo = [
                dict(r)
                for r in conn.execute(
                    "SELECT repository_id, COUNT(*) AS cnt, SUM(label) AS bugs FROM dataset_samples WHERE dataset_version = ? GROUP BY repository_id ORDER BY cnt DESC LIMIT 30",
                    (dataset_version,),
                ).fetchall()
            ]
            exclusions = [
                dict(r)
                for r in conn.execute(
                    "SELECT source_origin, exclusion_reason, COUNT(*) AS cnt FROM dataset_exclusions WHERE dataset_version = ? GROUP BY source_origin, exclusion_reason ORDER BY cnt DESC",
                    (dataset_version,),
                ).fetchall()
            ]
            return {
                "by_label": by_label,
                "by_source": by_source,
                "by_verification_status": by_verif,
                "by_bug_type": by_bug_type,
                "by_repository": by_repo,
                "exclusions": exclusions,
            }

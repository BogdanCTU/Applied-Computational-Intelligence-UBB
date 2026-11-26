"""Comprehensive verification tests for BUG/CLEAN classification, localization, partial analysis, Top-200 discovery, and GUI helpers."""
from __future__ import annotations

import ast
import json
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from application.pages.bug_prediction import (
    _highlight_class_rows,
    format_class_verdict,
    format_file_verdict,
)
from database.connection import Database
from database.repository import CLASS_FEATURE_NAMES, RepositoryDB
from ml.cross_validation import (
    RepositoryGroupKFoldValidator,
    compute_binary_classification_metrics,
    select_classifier_threshold,
)
from ml.experiment_runner import build_estimator
from ml.model_manager import ModelManager
from ml.predictor import BugPredictor, NoClassesFoundError
from ml.preprocessing import DataPreprocessor, split_by_repository
from repositories.github_client import GitHubClient
from services.dataset.dataset_builder import DEFAULT_NUMERICAL_FEATURES
from services.labeling.label_manager import compute_source_fingerprints, compress_line_ranges


def _build_dummy_class_and_localizer_bundles(tmp_path: Path, threshold: float = 0.65):
    np.random.seed(11)
    n = 120
    repos = np.repeat(np.arange(1, 7), 20)
    X_c = pd.DataFrame({f: np.random.randint(0, 6, size=n).astype(float) for f in CLASS_FEATURE_NAMES})
    X_c["class_loc"] = np.random.randint(10, 260, size=n).astype(float)
    X_c["total_cyclomatic_complexity"] = np.random.randint(2, 60, size=n).astype(float)
    y_c = pd.Series(((X_c["class_loc"] > 110) | (X_c["total_cyclomatic_complexity"] > 28)).astype(int))
    y_c.iloc[0] = 0
    y_c.iloc[1] = 1

    prep_c = DataPreprocessor(impute_missing=True, remove_constant=False).fit(X_c)
    est_c, _ = build_estimator("random_forest", {"n_estimators": 25, "max_depth": 6, "random_state": 42}, allow_extended=True)
    est_c.fit(prep_c.transform(X_c), y_c)

    # Separately trained method localizer on 26 method metrics
    X_m = pd.DataFrame({f: np.random.randint(0, 5, size=n).astype(float) for f in DEFAULT_NUMERICAL_FEATURES})
    X_m["cyclomatic_complexity"] = np.random.randint(1, 18, size=n).astype(float)
    X_m["loc"] = np.random.randint(4, 70, size=n).astype(float)
    y_m = pd.Series(((X_m["cyclomatic_complexity"] >= 6) | (X_m["loc"] >= 35)).astype(int))
    prep_m = DataPreprocessor(impute_missing=True, remove_constant=False).fit(X_m)
    est_m, _ = build_estimator("random_forest", {"n_estimators": 20, "max_depth": 5, "random_state": 42}, allow_extended=True)
    est_m.fit(prep_m.transform(X_m), y_m)

    db = Database(tmp_path / "cls_test.db")
    repo_db = RepositoryDB(db)
    mgr = ModelManager(tmp_path / "models", db=repo_db)

    mgr.save_model(
        model_name="class_bug_classifier_top200_v4",
        model=est_c,
        preprocessor=prep_c,
        feature_names=prep_c.feature_names_out_,
        parameters={"n_estimators": 25},
        metrics={"precision": 0.80, "recall": 0.72, "f1": 0.76},
        granularity="class",
        version="4.0.0",
        dataset_version="4.0.0",
        decision_threshold=threshold,
    )
    mgr.save_model(
        model_name="method_localizer_top200_v4",
        model=est_m,
        preprocessor=prep_m,
        feature_names=prep_m.feature_names_out_,
        parameters={"n_estimators": 20},
        metrics={"precision": 0.74, "recall": 0.68},
        granularity="method_localizer",
        version="4.0.0",
        dataset_version="4.0.0",
        decision_threshold=0.50,
    )
    return db, repo_db, mgr, X_c, y_c, pd.DataFrame({"repository_id": repos, "repository_name": [f"o/r{i}" for i in repos]})


def test_bug_and_clean_single_class_and_threshold_consistency(tmp_path):
    _, repo_db, _, _, _, _ = _build_dummy_class_and_localizer_bundles(tmp_path, threshold=0.65)
    predictor = BugPredictor.from_model_identifier(
        model_identifier="class_bug_classifier_top200_v4",
        models_dir=tmp_path / "models",
        db=repo_db,
        persist_history=True,
    )

    clean_cs = "namespace Demo { public class SmallDto { public int Id { get; set; } public int GetId() => Id; } }"
    res_clean = predictor.predict_class_code(clean_cs, file_name="SmallDto.cs")
    assert len(res_clean) == 1
    c0 = res_clean[0]
    assert c0.classification in ("BUG", "CLEAN")
    assert c0.classification == ("BUG" if c0.defect_probability >= predictor.decision_threshold else "CLEAN")
    assert c0.confidence == pytest.approx(
        c0.defect_probability if c0.classification == "BUG" else (1.0 - c0.defect_probability),
        abs=1e-4,
    )
    if c0.classification == "CLEAN":
        assert c0.localization is not None
        assert c0.localization.status == "not_applicable"

    # Force a low threshold (0.01) to guarantee BUG verdict + unavailable exact line localization on unseen code
    predictor.decision_threshold = 0.01
    bug_cs = """namespace Demo
{
    public class PaymentEngine
    {
        public int Process(int x, bool flag)
        {
            int acc = 0;
            if (x > 0 && flag)
            {
                for (int i = 0; i < x; i++)
                {
                    if (i % 2 == 0) acc += i;
                }
            }
            return acc;
        }
        public int Helper(int v) => v + 1;
    }
}"""
    res_bug = predictor.predict_class_code(bug_cs, file_name="PaymentEngine.cs")
    assert len(res_bug) == 1
    b0 = res_bug[0]
    assert b0.classification == "BUG"
    assert b0.predicted_label == 1
    assert b0.localization is not None
    assert b0.localization.exact_line_localization_status == "unavailable"
    assert b0.localization.status == "ml_method_only"
    assert len(b0.localization.ml_suspicious_methods) == 2
    assert b0.localization.verified_historical_locations == []


def test_historical_szz_localization_verified_distinct_from_ml(tmp_path):
    assert compress_line_ranges([10, 11, 12, 20, 25, 26]) == [
        {"start": 10, "end": 12},
        {"start": 20, "end": 20},
        {"start": 25, "end": 26},
    ]
    _, repo_db, _, _, _, _ = _build_dummy_class_and_localizer_bundles(tmp_path, threshold=0.01)

    class_body = """public class HistoricalClass
{
    public int Run(int x)
    {
        if (x < 0) return -1;
        return x * 2;
    }
}"""
    src_fp, struct_fp = compute_source_fingerprints(class_body)
    rid = repo_db.upsert_repository({
        "full_name": "Org/HistRepo",
        "name": "HistRepo",
        "owner": "Org",
        "url": "https://github.com/Org/HistRepo",
    })
    obs_id = repo_db.insert_class_observation({
        "repository_id": rid,
        "commit_sha": "abc123parent",
        "bug_fix_commit_sha": "fix999sha",
        "bug_inducing_commit_sha": "bic111sha",
        "file_path": "src/HistoricalClass.cs",
        "class_name": "HistoricalClass",
        "qualified_class_name": "Demo.HistoricalClass",
        "source_code": class_body,
        "source_fingerprint": src_fp,
        "structural_fingerprint": struct_fp,
        "label": 1,
        "szz_trace_count": 2,
        "blamed_lines_json": "[5, 6]",
        "localization_status": "verified_historical",
        "affected_methods_json": "[]",
        "affected_line_ranges_json": json.dumps([{"start": 5, "end": 6}]),
        "evidence_category": "szz_class_bic",
    })
    repo_db.insert_class_bug_localization({
        "class_observation_id": obs_id,
        "repository_id": rid,
        "commit_sha": "abc123parent",
        "bug_fix_commit_sha": "fix999sha",
        "bug_inducing_commit_sha": "bic111sha",
        "file_path": "src/HistoricalClass.cs",
        "qualified_class_name": "Demo.HistoricalClass",
        "method_name": "Run",
        "method_signature": "int Run(int x)",
        "method_start_line": 3,
        "method_end_line": 7,
        "affected_lines_json": "[5, 6]",
        "affected_line_ranges_json": json.dumps([{"start": 5, "end": 6}]),
        "localization_status": "verified_historical",
        "szz_confidence": 0.90,
    })

    predictor = BugPredictor.from_model_identifier(
        model_identifier="class_bug_classifier_top200_v4",
        models_dir=tmp_path / "models",
        db=repo_db,
        persist_history=False,
    )
    fres = predictor.predict_csharp_file(code=f"namespace Demo {{\n{class_body}\n}}", file_name="HistoricalClass.cs")
    cp = fres.class_predictions[0]
    assert cp.classification == "BUG"
    assert cp.localization is not None
    assert cp.localization.status == "verified_historical"
    assert cp.localization.exact_line_localization_status == "verified_historical"
    assert len(cp.localization.verified_historical_locations) == 1
    assert cp.localization.verified_historical_locations[0].affected_lines == [5, 6]
    assert cp.localization.verified_historical_locations[0].method_name == "Run"


def test_multiclass_file_and_incomplete_syntax_never_clean(tmp_path):
    _, repo_db, _, _, _, _ = _build_dummy_class_and_localizer_bundles(tmp_path, threshold=0.99)
    predictor = BugPredictor.from_model_identifier(
        model_identifier="class_bug_classifier_top200_v4",
        models_dir=tmp_path / "models",
        db=repo_db,
        persist_history=False,
    )

    # Empty / malformed with zero classes must raise NoClassesFoundError
    with pytest.raises(NoClassesFoundError):
        predictor.predict_csharp_file(code="just broken garbage {{{ without any class")

    # File with one CLEAN class AND syntax errors in file -> must NEVER report CLEAN
    broken_cs = """namespace BrokenDemo {
        public class HealthyDto { public int Value { get; set; } = 1; }
        public class BrokenSyntax { public void Bad(
    }"""
    fres = predictor.predict_csharp_file(code=broken_cs, file_name="Broken.cs")
    assert fres.syntax_error_count > 0 or fres.classes_failed_count > 0
    assert not fres.analysis_complete
    assert fres.file_classification != "CLEAN"
    assert fres.file_classification == "ANALYSIS INCOMPLETE"
    gui_payload = format_file_verdict(fres)
    assert gui_payload["severity"] == "warning"
    assert "CANNOT CLASSIFY AS CLEAN" in gui_payload["verdict"]

    # Clean multi-class file with 2 classes at normal threshold -> CLEAN
    clean_multi = """namespace CleanDemo {
        public class First { public int A() => 1; }
        public class Second { public int B() => 2; }
    }"""
    fres_ok = predictor.predict_csharp_file(code=clean_multi, file_name="Clean.cs")
    assert fres_ok.classes_analyzed_count == 2
    assert fres_ok.analysis_complete
    assert fres_ok.classes_clean_count == 2
    assert fres_ok.file_classification == "CLEAN"
    assert format_file_verdict(fres_ok)["verdict"] == "CLEAN"


def test_top200_star_ranked_discovery_and_exclusions():
    client = GitHubClient(token="dummy")
    page_items = [
        {"full_name": "Org/Forked", "name": "Forked", "owner": {"login": "Org"}, "stargazers_count": 50000, "size": 500, "language": "C#", "fork": True, "archived": False},
        {"full_name": "Org/MidStars", "name": "MidStars", "owner": {"login": "Org"}, "stargazers_count": 5000, "size": 800, "language": "C#", "fork": False, "archived": False},
        {"full_name": "Org/TopStars", "name": "TopStars", "owner": {"login": "Org"}, "stargazers_count": 30000, "size": 900, "language": "C#", "fork": False, "archived": False},
        {"full_name": "Org/EmptyRepo", "name": "EmptyRepo", "owner": {"login": "Org"}, "stargazers_count": 20000, "size": 0, "language": "C#", "fork": False, "archived": False},
        {"full_name": "Org/PythonRepo", "name": "PythonRepo", "owner": {"login": "Org"}, "stargazers_count": 25000, "size": 500, "language": "Python", "fork": False, "archived": False},
    ]
    client._request = MagicMock(return_value={"total_count": 5, "incomplete_results": False, "items": page_items})
    res = client.discover_top_csharp_repositories_by_stars(target_discovery=10, min_stars=100)
    assert res["selected_total"] == 2
    assert res["excluded_total"] == 3
    assert res["selected"][0]["full_name"] == "Org/TopStars"
    assert res["selected"][1]["full_name"] == "Org/MidStars"
    assert res["selected"][0]["selection_rank"] == 1


def test_repository_separation_fpr_fnr_and_threshold_calibration(tmp_path):
    _, _, mgr, X_c, y_c, meta = _build_dummy_class_and_localizer_bundles(tmp_path)
    # Registry hides method_localizer from primary list by default
    listed = mgr.list_saved_models()
    assert listed[0]["name"] == "class_bug_classifier_top200_v4"
    assert all(m["granularity"] != "method_localizer" for m in listed)

    X_tr, X_te, y_tr, y_te, m_tr, m_te, split_sum = split_by_repository(X_c, y_c, meta, test_size=0.33, random_state=42)
    assert set(m_tr["repository_id"]).isdisjoint(set(m_te["repository_id"]))

    y_t = np.array([0, 0, 0, 0, 1, 1, 1, 1] * 4)
    y_p = np.array([0.1, 0.2, 0.35, 0.70, 0.55, 0.78, 0.85, 0.92] * 4)
    t_res = select_classifier_threshold(y_t, y_p, min_precision_target=0.77, min_precision_floor=0.75, min_recall=0.50)
    assert t_res["inner_metrics"]["precision"] >= 0.75
    assert t_res["inner_metrics"]["recall"] >= 0.50
    m = compute_binary_classification_metrics(y_t, y_p, threshold=t_res["selected_threshold"])
    assert "fpr" in m and "fnr" in m
    assert 0.0 <= m["fpr"] <= 1.0
    assert 0.0 <= m["fnr"] <= 1.0


def test_gui_verdict_formatting_and_no_undefined_names(tmp_path):
    _, repo_db, _, _, _, _ = _build_dummy_class_and_localizer_bundles(tmp_path, threshold=0.01)
    predictor = BugPredictor.from_model_identifier(
        model_identifier="class_bug_classifier_top200_v4",
        models_dir=tmp_path / "models",
        db=repo_db,
        persist_history=False,
    )
    preds = predictor.predict_class_code("namespace UI { public class Box { public int Compute(int n) { int s=0; for(int i=0;i<n;i++) s+=i; return s; } } }")
    verdict = format_class_verdict(preds[0])
    assert verdict["verdict"] == "BUG DETECTED"
    assert verdict["severity"] == "error"

    bug_row = pd.Series({"Classification": "BUG"})
    clean_row = pd.Series({"Classification": "CLEAN"})
    assert all("rgba" in s for s in _highlight_class_rows(bug_row))
    assert all(s == "" for s in _highlight_class_rows(clean_row))

    # Static AST check that bug_prediction.py has no undefined tab3/tab4 names
    bp_path = Path("2_SourceCode/Python/application/pages/bug_prediction.py")
    src = bp_path.read_text(encoding="utf-8")
    tree = ast.parse(src)
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert "tab3" not in names and "tab4" not in names


def test_trained_v4_champion_and_method_localizer_smoke():
    champ_path = Path("4_AppBuild/Assets/Models/class_bug_classifier_top200_v4.joblib")
    loc_path = Path("4_AppBuild/Assets/Models/method_localizer_top200_v4.joblib")
    assert champ_path.exists(), f"Missing trained v4 champion model: {champ_path}"
    assert loc_path.exists(), f"Missing trained v4 method localizer: {loc_path}"

    predictor = BugPredictor.from_model_identifier(
        model_identifier="class_bug_classifier_top200_v4",
        models_dir="4_AppBuild/Assets/Models",
        persist_history=False,
    )
    assert predictor.granularity == "class"
    assert predictor.method_localizer_bundle is not None

    clean_res = predictor.predict_class_code(
        "namespace Smoke { public class TinyDto { public int Id { get; set; } } }",
        file_name="TinyDto.cs",
    )
    assert len(clean_res) == 1
    assert clean_res[0].classification == "CLEAN"

    complex_methods = "\n".join(
        f"""        public async System.Threading.Tasks.Task<string> SyncBatch{i}Async(System.Collections.Generic.List<OrderItem> items, string mode, bool forceRetry)
        {{
            if (!_isInitialized || items == null) throw new System.InvalidOperationException("Not ready");
            var result = new System.Text.StringBuilder();
            int processed = 0;
            try
            {{
                foreach (var item in items)
                {{
                    if (item == null || item.Id <= 0 || string.IsNullOrEmpty(item.Code)) continue;
                    var status = item.Status ?? "pending";
                    if ((mode == "strict" && item.Amount > {i} && status != "closed") || forceRetry)
                    {{
                        var payload = _client.BuildPayload(item.Id, item.Code, ServiceEndpoint, TimeoutSeconds);
                        var response = await _client.SendAsync(payload);
                        if (response != null && response.IsSuccess && response.Code == 200)
                        {{
                            _cache[item.Code] = response.Version;
                            result.Append(item.Code).Append(':').Append(response.Message);
                            processed++;
                        }}
                        else if (_retryCount < 3)
                        {{
                            _retryCount++;
                            _logger.Warn("Retry batch " + item.Code);
                        }}
                    }}
                    else if (mode == "fast")
                    {{
                        switch (status)
                        {{
                            case "queued": _logger.Info(item.Code); break;
                            case "failed": throw new System.Exception("Failed item " + item.Id);
                            default: processed++; break;
                        }}
                    }}
                }}
            }}
            catch (System.Exception ex)
            {{
                _logger.Error(ex.Message);
                if (forceRetry) throw;
            }}
            return processed > 0 ? result.ToString() : string.Empty;
        }}"""
        for i in range(6)
    )
    complex_cs = f"""namespace App.Core
{{
    public class LegacyOrderSyncManager
    {{
        private readonly IOrderClient _client;
        private readonly ILogger _logger;
        private readonly System.Collections.Generic.Dictionary<string, int> _cache = new();
        private int _retryCount;
        private bool _isInitialized;
        public string ServiceEndpoint {{ get; set; }}
        public int TimeoutSeconds {{ get; set; }}
        public LegacyOrderSyncManager(IOrderClient client, ILogger logger, string endpoint)
        {{
            _client = client;
            _logger = logger;
            ServiceEndpoint = endpoint;
            TimeoutSeconds = 30;
            _isInitialized = endpoint != null && client != null;
        }}
{complex_methods}
    }}
}}"""
    bug_res = predictor.predict_class_code(complex_cs, file_name="ComplexEngine.cs")
    assert len(bug_res) == 1
    assert bug_res[0].classification == "BUG"
    assert bug_res[0].localization is not None
    assert bug_res[0].localization.exact_line_localization_status == "unavailable"
    assert bug_res[0].localization.status == "ml_method_only"
    assert len(bug_res[0].localization.ml_suspicious_methods) > 0

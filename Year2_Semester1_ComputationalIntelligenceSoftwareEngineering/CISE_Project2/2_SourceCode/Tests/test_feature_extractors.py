"""Tests for all 5 independent feature extractors, determinism, and schema consistency."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from bug_detector.config import EXPERIMENT_DEFINITIONS, FeatureConfig
from bug_detector.features import (
    AstFeatureExtractor,
    ControlFlowFeatureExtractor,
    DataFlowFeatureExtractor,
    FeaturePipeline,
    LexicalFeatureExtractor,
    StructuralFeatureExtractor,
)
from bug_detector.ml.predictor import _method_to_feature_record
from bug_detector.preprocessing import RoslynPreprocessorClient


def test_all_five_extractors_deterministic_and_handle_empty_missing(fixtures_dir: Path) -> None:
    with RoslynPreprocessorClient() as client:
        buggy = client.analyze_file_path(fixtures_dir / "verified_buggy.cs")
        fixed = client.analyze_file_path(fixtures_dir / "verified_fixed.cs")

    recs = [_method_to_feature_record(m) for m in (buggy.methods + fixed.methods)]
    empty_rec = {
        "extraction_failed": True,
        "semantic_model_available": False,
        "tokens_normalized": [],
        "api_calls": [],
        "lexical_metrics": {},
        "ast_metrics": {},
        "cfg_metrics": {},
        "dfg_metrics": {},
        "structural_metrics": {},
    }

    for ext in [
        LexicalFeatureExtractor(max_token_features=30, max_api_features=20, min_df=1),
        AstFeatureExtractor(),
        ControlFlowFeatureExtractor(),
        DataFlowFeatureExtractor(),
        StructuralFeatureExtractor(),
    ]:
        ext.fit(recs)
        m1, s1 = ext.transform(recs)
        m2, _ = ext.transform(recs)
        assert m1.shape[0] == len(recs)
        assert m1.shape[1] == len(ext.get_feature_names())
        assert np.allclose(m1.toarray(), m2.toarray())

        m_empty, s_empty = ext.transform([empty_rec])
        assert m_empty.shape == (1, len(ext.get_feature_names()))
        assert s_empty.failed_items == 1
        assert s_empty.missing_semantic_items == 1
        assert s1.group_name == ext.group_name


def test_feature_pipeline_matches_all_experiments_and_train_infer_consistency(fixtures_dir: Path) -> None:
    with RoslynPreprocessorClient() as client:
        buggy = client.analyze_file_path(fixtures_dir / "verified_buggy.cs")
        fixed = client.analyze_file_path(fixtures_dir / "verified_fixed.cs")

    train_recs = [_method_to_feature_record(m) for m in buggy.methods]
    infer_recs = [_method_to_feature_record(m) for m in fixed.methods]

    for code, groups in EXPERIMENT_DEFINITIONS.items():
        pipe = FeaturePipeline(groups=groups, feature_config=FeatureConfig(experiment_code=code, min_df=1))
        X_tr, _ = pipe.fit_transform(train_recs)
        X_inf, _ = pipe.transform(infer_recs)
        assert X_tr.shape[1] == X_inf.shape[1] == len(pipe.get_feature_names())
        group_map = pipe.get_feature_group_map()
        assert set(group_map.keys()) == set(groups)

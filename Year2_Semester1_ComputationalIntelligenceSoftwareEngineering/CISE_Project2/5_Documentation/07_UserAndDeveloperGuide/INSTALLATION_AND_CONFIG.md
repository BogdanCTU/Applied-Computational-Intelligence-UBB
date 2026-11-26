# Installation and Configuration Reference

## 1. Prerequisites

- Python `3.13+` with virtual environment (`.venv/`)
- `.NET 9.0` SDK (`dotnet --version` -> `9.0.x`)
- Git CLI (for sparse-cloning InferredBugs and mining local GitHub repositories)
- Optional: `GITHUB_TOKEN` in `.env` (raises GitHub REST API rate limit from `60 req/hr` to `5,000 req/hr`)

## 2. Setup Steps

```bash
# 1. Build the Roslyn C# preprocessor in Release mode
dotnet build 2_SourceCode/RoslynPreprocessor/RoslynPreprocessor.csproj -c Release

# 2. Initialize SQLite database & apply migrations
PYTHONPATH=2_SourceCode .venv/bin/python -m bug_detector init-db

# 3. Copy .env.example if using GitHub REST API collection
cp .env.example .env
```

## 3. Configuration Reference (`4_AppBuild/Config/active_config.json`)

Validated via Pydantic v2 models in `2_SourceCode/bug_detector/config/settings.py`:

| Section | Key Parameters | Default |
| --- | --- | --- |
| `collection` | `inferredbugs_max_records`, `github_max_repos`, `hard_negatives_max_repos`, `hard_negative_min_complexity` | `5000`, `60`, `45`, `4` |
| `normalization` | `strip_comments`, `collapse_whitespace`, `abstract_string_literals`, `abstract_numeric_literals`, `preserve_special_literals` | `true` |
| `features` | `experiment_code` (`A`–`I`), `enabled_groups`, `tfidf_max_token_features`, `tfidf_max_api_features`, `tfidf_ngram_min/max` | `I`, all 5 groups, `300`, `100`, `1..2` |
| `random_forest` | `n_estimators`, `max_depth`, `min_samples_split`, `min_samples_leaf`, `max_features`, `class_weight`, `random_state` | `300`, `20`, `4`, `2`, `"sqrt"`, `"balanced_subsample"`, `42` |
| `thresholds` | `threshold_low < threshold_center < threshold_high`, `target_confident_error`, `calibration_method` | validation-calibrated, `0.25`, `"none"`/`"sigmoid"`/`"isotonic"` |
| `validation` | `outer_folds`, `inner_folds`, `independent_test_repo_fraction`, `hard_negative_test_repos`, `temporal_test_fraction` | `5`, `3`, `0.22`, `12`, `0.25` |
| `inference` | `active_model_version`, `active_model_path`, `require_clean_syntax`, `top_local_evidence_count` | active champion, `true`, `8` |

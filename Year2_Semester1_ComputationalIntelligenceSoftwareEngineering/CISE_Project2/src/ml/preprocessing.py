"""Preprocessing and repository-aware data partitioning for machine learning."""
from __future__ import annotations

import pandas as pd
import numpy as np
from typing import Any, Dict, List, Optional, Tuple, Set
from sklearn.impute import SimpleImputer
from sklearn.feature_selection import VarianceThreshold
from sklearn.model_selection import GroupShuffleSplit

from src.dataset.dataset_builder import DEFAULT_NUMERICAL_FEATURES, IDENTIFIER_COLUMNS
from src.utils.logger import setup_logger

logger = setup_logger("preprocessing")


class PreprocessingError(Exception):
    """Base exception for preprocessing and splitting failures."""
    pass


class DataPreprocessor:
    """Pipelines median imputation and constant-feature removal fitted strictly on training data."""

    def __init__(self, impute_missing: bool = True, remove_constant: bool = True) -> None:
        self.impute_missing = impute_missing
        self.remove_constant = remove_constant
        self.imputer: Optional[SimpleImputer] = None
        self.selector: Optional[VarianceThreshold] = None
        self.feature_names_in_: List[str] = []
        self.feature_names_out_: List[str] = []

    def fit(self, X_train: pd.DataFrame) -> DataPreprocessor:
        """Fit imputer and variance threshold exclusively on training features."""
        if X_train.empty:
            raise PreprocessingError("Cannot fit preprocessor on empty training matrix.")

        self.feature_names_in_ = list(X_train.columns)
        curr_X = X_train.copy()

        # 1. Median Imputation
        if self.impute_missing:
            self.imputer = SimpleImputer(strategy="median")
            curr_X = pd.DataFrame(
                self.imputer.fit_transform(curr_X),
                columns=self.feature_names_in_,
                index=curr_X.index,
            )

        # 2. Variance Threshold (remove constant features with zero variance)
        if self.remove_constant:
            self.selector = VarianceThreshold(threshold=0.0)
            self.selector.fit(curr_X)
            surviving_indices = self.selector.get_support(indices=True)
            self.feature_names_out_ = [self.feature_names_in_[i] for i in surviving_indices]
            if not self.feature_names_out_:
                raise PreprocessingError("All features were removed by variance threshold (all constant).")
        else:
            self.feature_names_out_ = list(self.feature_names_in_)

        logger.info(f"Preprocessor fitted: {len(self.feature_names_in_)} input features -> {len(self.feature_names_out_)} surviving features.")
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Transform features using pre-fitted transformers without data leakage."""
        if not self.feature_names_in_:
            raise PreprocessingError("Preprocessor must be fitted before transforming data.")

        # Ensure input columns match expected schema
        curr_X = X.copy()
        for col in self.feature_names_in_:
            if col not in curr_X.columns:
                curr_X[col] = 0.0

        curr_X = curr_X[self.feature_names_in_]

        if self.imputer is not None:
            curr_X = pd.DataFrame(
                self.imputer.transform(curr_X),
                columns=self.feature_names_in_,
                index=curr_X.index,
            )

        if self.selector is not None:
            curr_X = pd.DataFrame(
                self.selector.transform(curr_X),
                columns=self.feature_names_out_,
                index=curr_X.index,
            )
        else:
            curr_X = curr_X[self.feature_names_out_]

        return curr_X

    def fit_transform(self, X_train: pd.DataFrame) -> pd.DataFrame:
        """Fit and transform training features."""
        return self.fit(X_train).transform(X_train)


def split_by_repository(
    X: pd.DataFrame,
    y: pd.Series,
    metadata: pd.DataFrame,
    test_size: float = 0.25,
    random_state: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """Partition dataset into train and holdout test sets grouped strictly by repository_id.
    
    Guarantees zero repository overlap to prevent cross-repository data leakage.
    """
    if "repository_id" not in metadata.columns:
        raise PreprocessingError("Metadata must contain 'repository_id' for repository-aware splitting.")

    groups = metadata["repository_id"].values
    unique_repos = np.unique(groups)

    if len(unique_repos) < 2:
        raise PreprocessingError(
            f"Repository-aware splitting requires at least 2 distinct repositories, but found only {len(unique_repos)}: {list(unique_repos)}. "
            "Collect additional repositories before training to avoid data leakage."
        )

    gss = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=random_state)
    train_idx, test_idx = next(gss.split(X, y, groups=groups))

    X_train, X_test = X.iloc[train_idx].copy(), X.iloc[test_idx].copy()
    y_train, y_test = y.iloc[train_idx].copy(), y.iloc[test_idx].copy()
    meta_train, meta_test = metadata.iloc[train_idx].copy(), metadata.iloc[test_idx].copy()

    # Validate zero repository overlap
    train_repos: Set[Any] = set(meta_train["repository_id"].unique())
    test_repos: Set[Any] = set(meta_test["repository_id"].unique())
    overlap = train_repos.intersection(test_repos)

    if overlap:
        raise PreprocessingError(f"Fatal data leakage detected: Repositories present in both train and test splits: {overlap}")

    split_summary = {
        "train_repositories": list(train_repos),
        "test_repositories": list(test_repos),
        "train_repo_count": len(train_repos),
        "test_repo_count": len(test_repos),
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "train_buggy_count": int((y_train == 1).sum()),
        "train_clean_count": int((y_train == 0).sum()),
        "test_buggy_count": int((y_test == 1).sum()),
        "test_clean_count": int((y_test == 0).sum()),
    }

    logger.info(
        f"Repository split completed: Train={len(train_repos)} repos ({len(X_train)} methods), "
        f"Test={len(test_repos)} repos ({len(X_test)} methods). Zero overlap verified."
    )
    return X_train, X_test, y_train, y_test, meta_train, meta_test, split_summary


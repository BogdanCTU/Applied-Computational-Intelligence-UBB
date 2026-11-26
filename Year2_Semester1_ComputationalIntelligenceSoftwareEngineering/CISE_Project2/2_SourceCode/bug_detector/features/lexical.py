"""Lexical feature extractor: Roslyn token stats + TF-IDF token n-grams + API invocation TF-IDF."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer

from bug_detector.features.base import BaseFeatureExtractor, ExtractionStats, extract_fixed_dense_matrix

LEXICAL_DENSE_COLUMNS = [
    "token_count",
    "keyword_count",
    "operator_count",
    "identifier_count",
    "distinct_identifier_count",
    "literal_count",
    "null_literal_count",
    "string_literal_count",
    "numeric_literal_count",
    "bool_literal_count",
    "punctuation_count",
    "api_call_count",
    "distinct_api_call_count",
    "keyword_ratio",
    "operator_ratio",
    "identifier_ratio",
    "literal_ratio",
    "null_literal_ratio",
    "identifier_diversity",
    "avg_token_length",
]


def _identity_tokenizer(tokens: list[str]) -> list[str]:
    return tokens


def _identity_preprocessor(tokens: list[str]) -> list[str]:
    return tokens


class LexicalFeatureExtractor(BaseFeatureExtractor):
    """Extracts Roslyn lexical statistics plus training-fitted token n-gram and API-call TF-IDF."""

    group_name = "lexical"
    version = "1.0.0"

    def __init__(
        self,
        max_token_features: int = 300,
        max_api_features: int = 100,
        ngram_range: tuple[int, int] = (1, 2),
        min_df: int = 2,
    ) -> None:
        self.max_token_features = max_token_features
        self.max_api_features = max_api_features
        self.ngram_range = ngram_range
        self.min_df = min_df
        self._token_vectorizer: TfidfVectorizer | None = None
        self._api_vectorizer: TfidfVectorizer | None = None
        self._token_names: list[str] = []
        self._api_names: list[str] = []

    def fit(self, records: list[dict[str, Any]]) -> "LexicalFeatureExtractor":
        token_docs = [list(rec.get("tokens_normalized") or []) for rec in records]
        api_docs = [list(rec.get("api_calls") or []) for rec in records]

        effective_min_df = min(self.min_df, max(1, len(records)))

        if any(token_docs):
            self._token_vectorizer = TfidfVectorizer(
                tokenizer=_identity_tokenizer,
                preprocessor=_identity_preprocessor,
                token_pattern=None,
                lowercase=False,
                ngram_range=self.ngram_range,
                max_features=self.max_token_features,
                min_df=effective_min_df,
                sublinear_tf=True,
                dtype=np.float64,
            )
            try:
                self._token_vectorizer.fit(token_docs)
                self._token_names = [f"lex_tok_tfidf::{t}" for t in self._token_vectorizer.get_feature_names_out()]
            except ValueError:
                self._token_vectorizer = None
                self._token_names = []
        else:
            self._token_vectorizer = None
            self._token_names = []

        if any(api_docs):
            self._api_vectorizer = TfidfVectorizer(
                tokenizer=_identity_tokenizer,
                preprocessor=_identity_preprocessor,
                token_pattern=None,
                lowercase=False,
                ngram_range=(1, 1),
                max_features=self.max_api_features,
                min_df=1,
                sublinear_tf=True,
                dtype=np.float64,
            )
            try:
                self._api_vectorizer.fit(api_docs)
                self._api_names = [f"lex_api_tfidf::{t}" for t in self._api_vectorizer.get_feature_names_out()]
            except ValueError:
                self._api_vectorizer = None
                self._api_names = []
        else:
            self._api_vectorizer = None
            self._api_names = []

        return self

    def transform(self, records: list[dict[str, Any]]) -> tuple[sparse.csr_matrix, ExtractionStats]:
        dense_mat, stats = extract_fixed_dense_matrix(
            records,
            payload_key="lexical_metrics",
            columns=LEXICAL_DENSE_COLUMNS,
            group_name=self.group_name,
            version=self.version,
        )
        blocks = [dense_mat]
        if self._token_vectorizer is not None:
            token_docs = [list(rec.get("tokens_normalized") or []) for rec in records]
            blocks.append(self._token_vectorizer.transform(token_docs).tocsr())
        if self._api_vectorizer is not None:
            api_docs = [list(rec.get("api_calls") or []) for rec in records]
            blocks.append(self._api_vectorizer.transform(api_docs).tocsr())
        combined = sparse.hstack(blocks, format="csr") if len(blocks) > 1 else blocks[0]
        return combined, stats

    def get_feature_names(self) -> list[str]:
        return [f"lex_{c}" for c in LEXICAL_DENSE_COLUMNS] + self._token_names + self._api_names

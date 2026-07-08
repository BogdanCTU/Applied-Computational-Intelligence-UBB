"""
CCM Knowledge Discovery / Data Mining Pipeline  –  Claude V9
Changes from V7:
  - Adapted to the new dataset schema (same column names as V7).
  - _BIN and _ENCODED columns are now explicitly excluded from:
      * ALL plots (EDA scatter, correlation, histograms of derived columns)
      * PCA (prepare_unsupervised_matrix already excluded targets, now also
             excludes any column whose name ends with "_BIN" or "_ENCODED")
      * Clustering (K-Means, DBSCAN) feature matrix
      * Anomaly detection feature matrix
      * EDA correlation computation
      * Decision-tree numeric feature set
  - All numeric values are scaled (StandardScaler) before any analysis that
    uses distances or linear algebra (PCA, K-Means, DBSCAN, Isolation Forest).
    The EDA scatter / correlation plots still operate on raw values so the
    axis labels remain interpretable, but a note is included in the report.
  - A helper ``_get_analysis_cols(df)`` centralises the logic of selecting
    the raw sensor / process columns (no targets, no _BIN, no _ENCODED,
    no datetime, no categorical ids).
  - Output folder: Analysis_Outputs_Claude_V9

RUL LEAKAGE FIX (applied throughout this file):
  ANY column whose name contains the substring "rul" (case-insensitive) is a
  direct transformation of either the regression target (calculated_RUL_tons)
  or the classification target (RUL_Class) and therefore constitutes target
  leakage.  Examples that are excluded from every supervised feature matrix:
      calculated_RUL_tons  (regression target itself  – kept only for regression)
      RUL_Class            (classification target      – kept only for classification)
      RUL_Class_ENCODED    (ordinal encoding of RUL_Class)
      RUL_percentage       (linear transform of calculated_RUL_tons)
      <any future *RUL* column added to the dataset>
  The same columns are also excluded from EDA correlation analysis and all
  unsupervised feature matrices so that "easy" RUL-derived signals cannot
  inflate correlation scores or dominate PCA axes.

Expected folder structure:
    script_folder/
    ├── Analysis_Claude_V9.py
    ├── Dataset2/
    │   └── Final_Processed_Steel_Data.csv  ← new schema
    └── Analysis_Outputs_Claude_V9/
        └── plots/
Run:
    python Analysis_Claude_V9.py
"""

from pathlib import Path
import os
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix,
    silhouette_score,
    silhouette_samples,
)
from sklearn.ensemble import (
    RandomForestRegressor,
    RandomForestClassifier,
    IsolationForest,
)
from sklearn.tree import DecisionTreeClassifier, export_text
from sklearn.cluster import KMeans, DBSCAN
from sklearn.decomposition import PCA
from sklearn.neighbors import NearestNeighbors

warnings.filterwarnings("ignore")

try:
    from mlxtend.frequent_patterns import apriori, association_rules
    MLXTEND_AVAILABLE = True
except ImportError:
    MLXTEND_AVAILABLE = False

# ============================================================
# Global configuration
# ============================================================
TARGET_REGRESSION    = "calculated_RUL_tons"
TARGET_CLASSIFICATION = "RUL_Class"

RANDOM_STATE = 42
PLOT_DPI     = 160
TOP_N_FEATURES       = 25
TOP_N_CORRELATIONS   = 25
TOP_N_ASSOCIATION_RULES = 20

# K-Means search range for elbow / silhouette curves
KMEANS_K_RANGE = range(2, 11)

# Final K chosen for the main clustering run
KMEANS_N_CLUSTERS = 4

# DBSCAN – min_samples is fixed; eps is AUTO-estimated from the k-distance knee.
# Override eps by setting DBSCAN_EPS_OVERRIDE to a positive float.
DBSCAN_MIN_SAMPLES  = 10
DBSCAN_EPS_OVERRIDE = None   # e.g. 2.5 — set to None to auto-detect

# Cap on BIN columns passed to Apriori to avoid OOM on large transaction matrices.
MAX_APRIORI_COLUMNS = 20

# Maximum rows sampled for Apriori (keeps candidate generation fast on large datasets).
APRIORI_MAX_ROWS = 5_000

# Apriori hyperparameters
APRIORI_MIN_SUPPORT = 0.15
APRIORI_MAX_LEN     = 3

# ============================================================
# V9: columns always excluded from numeric analysis/plots
# ============================================================
# Any column whose name ends with one of these suffixes is a derived/encoded
# column and must NOT appear in plots, PCA, clustering or correlation analysis.
_DERIVED_SUFFIXES = ("_BIN", "_ENCODED")

# Additional leakage columns that are always excluded from feature matrices.
# NOTE: these are also caught by the broader _RUL_LEAKAGE_SUBSTR pattern below,
# but are listed here explicitly for documentation clarity.
_LEAKAGE_ALWAYS = [
    "RUL_Class_ENCODED",   # ordinal encoding of classification target
    "RUL_percentage",      # percentage transform of regression target
]

# ============================================================
# RUL LEAKAGE FIX
# ============================================================
# Every column whose name contains this substring (matched case-insensitively)
# is a direct transformation of either supervised target and must therefore be
# excluded from ALL supervised feature matrices and EDA correlation analyses.
# The only exception is the single target column required by the current task
# (handled inside remove_leakage_columns and _get_analysis_cols).
_RUL_LEAKAGE_SUBSTR = "rul"

def _is_rul_leakage(col_name: str) -> bool:
    """Return True if the column name contains 'rul' (case-insensitive)."""
    return (_RUL_LEAKAGE_SUBSTR in col_name.lower() or "sleeve" in col_name.lower())

# ============================================================
# Colour palettes (consistent across all cluster plots)
# ============================================================
_CLUSTER_CMAP  = "tab10"
_NOISE_COLOR   = "#B0BEC5"   # light grey for noise / anomaly points

def _cluster_colours(n_colours: int):
    """Return a list of *n_colours* distinct colours from the qualitative tab10 cmap."""
    cmap = plt.get_cmap(_CLUSTER_CMAP)
    return [cmap(i % 10) for i in range(n_colours)]

# ============================================================
# V9: central helper – raw analysis columns
# ============================================================
def _is_derived_col(col_name: str) -> bool:
    """Return True if the column is a _BIN or _ENCODED derived column."""
    return any(col_name.endswith(sfx) for sfx in _DERIVED_SUFFIXES)


def _get_analysis_cols(df: pd.DataFrame) -> list:
    """
    Return the list of numeric columns that are suitable for EDA / unsupervised
    analysis in V9.  Excluded:
        * Target columns (regression + classification)
        * Always-leakage columns (RUL_percentage, RUL_Class_ENCODED)
        * Any column ending in _BIN or _ENCODED
        * Any column whose name contains "rul" (case-insensitive) — these are
          all direct transformations of one of the two supervised targets and
          would inflate correlations or dominate PCA axes if included.
        * Non-numeric columns (datetime, object / categorical)
    """
    exclude = set(
        [TARGET_REGRESSION, TARGET_CLASSIFICATION]
        + _LEAKAGE_ALWAYS
        + [c for c in df.columns if _is_derived_col(c)]
        + [c for c in df.columns if _is_rul_leakage(c)]  # RUL leakage fix
    )
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    return [c for c in numeric_cols if c not in exclude]


# ============================================================
# Utility functions
# ============================================================
def create_output_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def create_plot_dir(output_dir: str) -> str:
    plot_dir = os.path.join(output_dir, "plots")
    os.makedirs(plot_dir, exist_ok=True)
    return plot_dir

def save_current_plot(path: str) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=PLOT_DPI, bbox_inches="tight")
    plt.close()

def safe_filename(name: str) -> str:
    invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', ',', '%']
    result = str(name)
    for ch in invalid_chars:
        result = result.replace(ch, "_")
    result = result.replace(" ", "_")
    return result[:120]

def load_dataset(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    print(f"[INFO] Dataset loaded: {df.shape[0]} rows, {df.shape[1]} columns")
    return df

def basic_cleaning(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = df.dropna(how="all")
    df = df.dropna(axis=1, how="all")
    df.columns = [c.strip() for c in df.columns]
    for col in df.columns:
        if "date" in col.lower() or "time" in col.lower() or "timestamp" in col.lower():
            try:
                df[col] = pd.to_datetime(df[col], errors="ignore")
            except Exception:
                pass
    return df

def remove_leakage_columns(
    df: pd.DataFrame,
    task: str,
    strict_no_resistance: bool = False,
) -> pd.DataFrame:
    """
    Removes target leakage columns for the V9 schema.

    RUL LEAKAGE FIX
    ---------------
    Every column whose name contains the substring "rul" (case-insensitive) is
    a direct transformation of either supervised target and constitutes leakage:

        • calculated_RUL_tons  – regression target (kept only when task="regression")
        • RUL_Class            – classification target (kept only when task="classification")
        • RUL_Class_ENCODED    – ordinal encoding of RUL_Class
        • RUL_percentage       – linear transform of calculated_RUL_tons
        • <any future *RUL* column in the dataset>

    Only the single target column required by the current task survives in the
    returned dataframe; all other RUL-named columns are dropped.

    Additional V9 exclusions:
        - All *_BIN and *_ENCODED derived columns are dropped from every
          supervised feature matrix to prevent indirect leakage.
        - strict_no_resistance=True additionally removes all columns whose name
          contains "resistance" (use this when a clean prognostic experiment is
          required, since RUL is derived from cumulative resistance).
    """
    cols_to_drop = []

    # --- always-explicit leakage columns (subset of the RUL pattern, listed
    #     here for documentation clarity even though the RUL pattern catches them) ---
    for col in df.columns:
        if col in _LEAKAGE_ALWAYS:
            cols_to_drop.append(col)

    # --- V9: drop all _BIN and _ENCODED derived columns ---
    for col in df.columns:
        if _is_derived_col(col):
            cols_to_drop.append(col)

    # --- RUL LEAKAGE FIX: drop every column whose name contains "rul"
    #     (case-insensitive) except the single target for the current task.
    #     This is the primary guard against all forms of RUL-related leakage. ---
    current_task_target = (
        TARGET_REGRESSION if task == "regression" else TARGET_CLASSIFICATION
    )
    for col in df.columns:
        if _is_rul_leakage(col) and col != current_task_target:
            cols_to_drop.append(col)

    if strict_no_resistance:
        for col in df.columns:
            if "resistance" in col.lower():
                cols_to_drop.append(col)

    cols_to_drop = sorted(set([c for c in cols_to_drop if c in df.columns]))

    if cols_to_drop:
        print(f"[INFO]   Leakage columns removed for {task}: {cols_to_drop}")

    return df.drop(columns=cols_to_drop, errors="ignore")

def split_features_target(df: pd.DataFrame, target: str):
    if target not in df.columns:
        raise ValueError(f"Target column '{target}' was not found in dataset.")
    y = df[target]
    X = df.drop(columns=[target])
    datetime_cols = X.select_dtypes(
        include=["datetime64[ns]", "datetimetz"]
    ).columns.tolist()
    X = X.drop(columns=datetime_cols, errors="ignore")
    return X, y

def get_column_types(X: pd.DataFrame):
    numeric_cols     = X.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = X.select_dtypes(exclude=[np.number]).columns.tolist()
    return numeric_cols, categorical_cols

def build_preprocessor(X: pd.DataFrame):
    numeric_cols, categorical_cols = get_column_types(X)

    # HARDENING STEP (critical fix)
    X[categorical_cols] = X[categorical_cols].astype(str)

    numeric_pipeline = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])

    categorical_pipeline = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("encoder", OneHotEncoder(handle_unknown="ignore")),
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_pipeline, numeric_cols),
            ("cat", categorical_pipeline, categorical_cols),
        ],
        remainder="drop",
    )

    return preprocessor, numeric_cols, categorical_cols

def export_feature_importance(pipeline: Pipeline, output_path: str) -> pd.DataFrame:
    model        = pipeline.named_steps["model"]
    preprocessor = pipeline.named_steps["preprocess"]
    if not hasattr(model, "feature_importances_"):
        return pd.DataFrame()
    try:
        feature_names = preprocessor.get_feature_names_out()
    except Exception:
        feature_names = [
            f"feature_{i}" for i in range(len(model.feature_importances_))
        ]
    importance_df = pd.DataFrame(
        {
            "feature":    feature_names,
            "importance": model.feature_importances_,
        }
    ).sort_values(by="importance", ascending=False)
    importance_df.to_csv(output_path, index=False)
    print(f"[RESULT] Feature importance exported: {output_path}")
    return importance_df

# ============================================================
# Plotting: generic helpers
# ============================================================
def plot_bar_from_series(
    series: pd.Series,
    title: str,
    xlabel: str,
    ylabel: str,
    path: str,
    top_n: int = None,
):
    s = series.dropna()
    if top_n is not None:
        s = s.head(top_n)
    if s.empty:
        return
    plt.figure(figsize=(12, max(5, 0.35 * len(s))))
    s.sort_values().plot(kind="barh")
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    save_current_plot(path)

def plot_histogram(
    series: pd.Series,
    title: str,
    xlabel: str,
    ylabel: str,
    path: str,
    bins: int = 40,
):
    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty:
        return
    plt.figure(figsize=(10, 6))
    plt.hist(s, bins=bins)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    save_current_plot(path)

def plot_scatter(x, y, title: str, xlabel: str, ylabel: str, path: str):
    x = pd.to_numeric(pd.Series(x), errors="coerce")
    y = pd.to_numeric(pd.Series(y), errors="coerce")
    valid = x.notna() & y.notna()
    x = x[valid]
    y = y[valid]
    if len(x) == 0:
        return
    plt.figure(figsize=(10, 6))
    plt.scatter(x, y, s=18, alpha=0.7)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    save_current_plot(path)

def plot_line_from_dataframe(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str,
    xlabel: str,
    ylabel: str,
    path: str,
):
    if x_col not in df.columns or y_col not in df.columns:
        return
    plot_df = df[[x_col, y_col]].dropna()
    if plot_df.empty:
        return
    plt.figure(figsize=(12, 6))
    plt.plot(plot_df[x_col], plot_df[y_col], marker="o", linewidth=1)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.xticks(rotation=45)
    save_current_plot(path)

# ============================================================
# EDA plots  (V9: _BIN/_ENCODED columns excluded from all analyses)
# ============================================================
def generate_eda_plots(df: pd.DataFrame, output_dir: str):
    print("\n[INFO] Generating EDA plots...")
    plot_dir = create_plot_dir(output_dir)

    # --- RUL distribution ---
    if TARGET_REGRESSION in df.columns:
        plot_histogram(
            df[TARGET_REGRESSION],
            title="Calculated RUL (tons) Distribution",
            xlabel="RUL (tons)",
            ylabel="Frequency",
            path=os.path.join(plot_dir, "eda_rul_distribution.png"),
        )

    # --- RUL_percentage distribution (informational only, not used in models) ---
    if "RUL_percentage" in df.columns:
        plot_histogram(
            df["RUL_percentage"],
            title="RUL Percentage Distribution",
            xlabel="RUL Percentage (%)",
            ylabel="Frequency",
            path=os.path.join(plot_dir, "eda_rul_percentage_distribution.png"),
        )

    # --- Classification target distribution ---
    if TARGET_CLASSIFICATION in df.columns:
        class_counts = df[TARGET_CLASSIFICATION].astype(str).value_counts()
        plot_bar_from_series(
            class_counts,
            title="RUL_Class Class Distribution",
            xlabel="Count",
            ylabel="RUL FCA Bin",
            path=os.path.join(plot_dir, "eda_rul_class_distribution.png"),
        )

    # --- workpiece_slice_geometry ---
    if "workpiece_slice_geometry" in df.columns and TARGET_REGRESSION in df.columns:
        geom_rul = (
            df.groupby("workpiece_slice_geometry")[TARGET_REGRESSION]
            .mean()
            .sort_values(ascending=False)
        )
        plot_bar_from_series(
            geom_rul,
            title="Average RUL by Workpiece Geometry",
            xlabel="Average RUL (tons)",
            ylabel="Geometry",
            path=os.path.join(plot_dir, "eda_average_rul_by_geometry.png"),
        )

    # --- steel_type ---
    if "steel_type" in df.columns and TARGET_REGRESSION in df.columns:
        steel_rul = (
            df.groupby("steel_type")[TARGET_REGRESSION]
            .mean()
            .sort_values(ascending=False)
        )
        plot_bar_from_series(
            steel_rul,
            title="Average RUL by Steel Type",
            xlabel="Average RUL (tons)",
            ylabel="Steel Type",
            path=os.path.join(plot_dir, "eda_average_rul_by_steel_type.png"),
        )

    # --- alloy_type ---
    if "alloy_type" in df.columns and TARGET_REGRESSION in df.columns:
        alloy_rul = (
            df.groupby("alloy_type")[TARGET_REGRESSION]
            .mean()
            .sort_values(ascending=False)
        )
        plot_bar_from_series(
            alloy_rul,
            title="Average RUL by Alloy Type",
            xlabel="Average RUL (tons)",
            ylabel="Alloy Type",
            path=os.path.join(plot_dir, "eda_average_rul_by_alloy_type.png"),
        )

    # --- num_stream ---
    if "num_stream" in df.columns and TARGET_REGRESSION in df.columns:
        stream_rul = (
            df.groupby("num_stream")[TARGET_REGRESSION]
            .mean()
            .sort_values(ascending=False)
        )
        plot_bar_from_series(
            stream_rul,
            title="Average RUL by Stream",
            xlabel="Average RUL (tons)",
            ylabel="Stream",
            path=os.path.join(plot_dir, "eda_average_rul_by_stream.png"),
        )

    # --- num_crystallizer ---
    if "num_crystallizer" in df.columns and TARGET_REGRESSION in df.columns:
        cryst_rul = (
            df.groupby("num_crystallizer")[TARGET_REGRESSION]
            .mean()
            .sort_values(ascending=False)
        )
        plot_bar_from_series(
            cryst_rul,
            title="Average RUL by Crystallizer",
            xlabel="Average RUL (tons)",
            ylabel="Crystallizer",
            path=os.path.join(plot_dir, "eda_average_rul_by_crystallizer.png"),
        )

    # --- sleeve ---
    if "sleeve" in df.columns and TARGET_REGRESSION in df.columns:
        sleeve_rul = (
            df.groupby("sleeve")[TARGET_REGRESSION]
            .mean()
            .sort_values(ascending=False)
        )
        plot_bar_from_series(
            sleeve_rul,
            title="Top Sleeve Groups by Average RUL",
            xlabel="Average RUL (tons)",
            ylabel="Sleeve",
            path=os.path.join(plot_dir, "eda_average_rul_by_sleeve_top25.png"),
            top_n=25,
        )

    # --- V9: Numerical correlations with RUL —
    #     _BIN/_ENCODED excluded AND all other RUL-named columns excluded ---
    if TARGET_REGRESSION in df.columns:
        # Use only the curated analysis columns (no _BIN, no _ENCODED, no *rul*)
        analysis_cols = _get_analysis_cols(df)
        if analysis_cols:
            corr_df = df[analysis_cols + [TARGET_REGRESSION]].copy()
            corr_df = corr_df.select_dtypes(include=[np.number])
            if TARGET_REGRESSION in corr_df.columns:
                corr = (
                    corr_df.corr(numeric_only=True)[TARGET_REGRESSION]
                    .drop(TARGET_REGRESSION, errors="ignore")
                )
                corr = corr.reindex(
                    corr.abs().sort_values(ascending=False).index
                ).head(TOP_N_CORRELATIONS)
                plot_bar_from_series(
                    corr,
                    title=(
                        f"Top {TOP_N_CORRELATIONS} Numerical Correlations with RUL (tons)\n"
                        "(Raw sensor/process columns only — no _BIN/_ENCODED, no RUL-derived)"
                    ),
                    xlabel="Correlation with RUL",
                    ylabel="Feature",
                    path=os.path.join(plot_dir, "eda_top_correlations_with_rul.png"),
                )

    # --- V9: scatter candidates — raw sensor columns only (no _BIN/_ENCODED) ---
    candidate_scatter_cols = [
        "resistance, tonn",
        "water_consumption, liter/minute",
        "water_temperature_delta, Celsius deg.",
        "steel_temperature_grab1, Celsius deg.",
        "swing_frequency, amount/minute",
        "crystallizer_movement, mm",
        "alloy_speed, meter/minute",
        "steel_weight, tonn",
        "temperature_measurement1, Celsius deg.",
        "temperature_measurement2, Celsius deg.",
        "cast_in_row",
    ]
    if TARGET_REGRESSION in df.columns:
        for col in candidate_scatter_cols:
            if col in df.columns and not _is_derived_col(col):
                plot_scatter(
                    df[col],
                    df[TARGET_REGRESSION],
                    title=f"RUL vs {col}",
                    xlabel=col,
                    ylabel="RUL (tons)",
                    path=os.path.join(
                        plot_dir,
                        f"eda_scatter_rul_vs_{safe_filename(col)}.png",
                    ),
                )

    # --- time-series trend using "datetime_combined" ---
    if "datetime_combined" in df.columns and TARGET_REGRESSION in df.columns:
        temp = df.copy()
        temp["datetime_combined"] = pd.to_datetime(
            temp["datetime_combined"], errors="coerce"
        )
        temp = temp.dropna(
            subset=["datetime_combined", TARGET_REGRESSION]
        ).sort_values("datetime_combined")
        if not temp.empty:
            daily = (
                temp.set_index("datetime_combined")[TARGET_REGRESSION]
                .resample("D")
                .mean()
                .reset_index()
            )
            plot_line_from_dataframe(
                daily,
                x_col="datetime_combined",
                y_col=TARGET_REGRESSION,
                title="Daily Average RUL (tons) Trend",
                xlabel="Date",
                ylabel="Average RUL (tons)",
                path=os.path.join(plot_dir, "eda_daily_average_rul_trend.png"),
            )

    print(f"[RESULT] EDA plots exported to: {plot_dir}")

# ============================================================
# Supervised learning: RUL regression
# ============================================================
def run_rul_regression(
    df: pd.DataFrame,
    output_dir: str,
    strict_no_resistance: bool = False,
):
    print("\n[INFO] Running supervised RUL regression...")
    plot_dir = create_plot_dir(output_dir)

    # RUL LEAKAGE FIX: remove_leakage_columns now drops every column containing
    # "rul" except calculated_RUL_tons, plus all _BIN/_ENCODED columns.
    df_model = remove_leakage_columns(
        df, task="regression", strict_no_resistance=strict_no_resistance
    )
    X, y = split_features_target(df_model, TARGET_REGRESSION)

    valid_idx = y.notna()
    X = X.loc[valid_idx]
    y = pd.to_numeric(y.loc[valid_idx], errors="coerce")
    valid_idx = y.notna()
    X = X.loc[valid_idx]
    y = y.loc[valid_idx]

    if len(y) < 10:
        print("[WARNING] Not enough valid RUL samples for regression.")
        return

    preprocessor, _, _ = build_preprocessor(X)
    model = RandomForestRegressor(
        n_estimators=300,
        max_depth=None,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    pipeline = Pipeline(
        steps=[
            ("preprocess", preprocessor),
            ("model", model),
        ]
    )
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=RANDOM_STATE
    )
    pipeline.fit(X_train, y_train)
    preds = pipeline.predict(X_test)

    mae  = mean_absolute_error(y_test, preds)
    rmse = np.sqrt(mean_squared_error(y_test, preds))
    r2   = r2_score(y_test, preds)

    metrics = pd.DataFrame(
        {"metric": ["MAE", "RMSE", "R2"], "value": [mae, rmse, r2]}
    )
    metrics_path = os.path.join(output_dir, "rul_regression_metrics.csv")
    metrics.to_csv(metrics_path, index=False)
    print("[RESULT] RUL Regression Metrics")
    print(metrics)

    predictions_df = pd.DataFrame(
        {
            "actual_RUL":    y_test.values,
            "predicted_RUL": preds,
            "error":         y_test.values - preds,
        }
    )
    predictions_df.to_csv(
        os.path.join(output_dir, "rul_regression_predictions.csv"), index=False
    )

    importance_df = export_feature_importance(
        pipeline=pipeline,
        output_path=os.path.join(output_dir, "rul_regression_feature_importance.csv"),
    )

    plot_scatter(
        predictions_df["actual_RUL"],
        predictions_df["predicted_RUL"],
        title="RUL Regression: Actual vs Predicted (tons)",
        xlabel="Actual RUL (tons)",
        ylabel="Predicted RUL (tons)",
        path=os.path.join(plot_dir, "regression_actual_vs_predicted_rul.png"),
    )
    plot_histogram(
        predictions_df["error"],
        title="RUL Regression Error Distribution",
        xlabel="Prediction Error (tons)",
        ylabel="Frequency",
        path=os.path.join(plot_dir, "regression_error_distribution.png"),
    )
    if not importance_df.empty:
        top_features = importance_df.head(TOP_N_FEATURES).set_index("feature")["importance"]
        plot_bar_from_series(
            top_features,
            title=f"Top {TOP_N_FEATURES} Features for RUL Regression",
            xlabel="Importance",
            ylabel="Feature",
            path=os.path.join(plot_dir, "regression_feature_importance_top25.png"),
        )

# ============================================================
# Supervised learning: RUL_FCA_BIN classification
# ============================================================
def run_rul_classification(
    df: pd.DataFrame,
    output_dir: str,
    strict_no_resistance: bool = False,
):
    print("\n[INFO] Running supervised RUL_FCA_BIN classification...")
    plot_dir = create_plot_dir(output_dir)

    # Normalize column names (prevents hidden whitespace drift)
    df.columns = df.columns.str.strip()

    # RUL LEAKAGE FIX: remove_leakage_columns now drops every column containing
    # "rul" except RUL_Class, plus all _BIN/_ENCODED columns.
    df_model = remove_leakage_columns(
        df, task="classification", strict_no_resistance=strict_no_resistance
    )

    # CRITICAL FIX: re-apply normalization after leakage removal
    df_model.columns = df_model.columns.str.strip()

    # HARD GUARANTEE: validate target existence before proceeding
    if TARGET_CLASSIFICATION not in df_model.columns:
        raise ValueError(
            f"Missing target column '{TARGET_CLASSIFICATION}'. "
            f"Available columns: {df_model.columns.tolist()}\n"
            f"[DIAGNOSTIC] Columns containing 'RUL': "
            f"{[c for c in df_model.columns if 'RUL' in c.upper()]}"
        )

    X, y = split_features_target(df_model, TARGET_CLASSIFICATION)

    valid_idx = y.notna()
    X = X.loc[valid_idx]
    y = y.loc[valid_idx].astype(str)

    if len(y) < 10:
        print("[WARNING] Not enough valid RUL_FCA_BIN samples for classification.")
        return

    preprocessor, _, _ = build_preprocessor(X)

    model = RandomForestClassifier(
        n_estimators=300,
        random_state=RANDOM_STATE,
        n_jobs=-1,
        class_weight="balanced",
    )

    pipeline = Pipeline(
        steps=[
            ("preprocess", preprocessor),
            ("model", model),
        ]
    )

    stratify = y if y.value_counts().min() >= 2 else None

    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.25,
        random_state=RANDOM_STATE,
        stratify=stratify
    )

    pipeline.fit(X_train, y_train)
    preds = pipeline.predict(X_test)

    metrics = pd.DataFrame(
        {
            "metric": ["Accuracy", "Precision_macro", "Recall_macro", "F1_macro"],
            "value": [
                accuracy_score(y_test, preds),
                precision_score(y_test, preds, average="macro", zero_division=0),
                recall_score(y_test, preds, average="macro", zero_division=0),
                f1_score(y_test, preds, average="macro", zero_division=0),
            ],
        }
    )

    metrics.to_csv(
        os.path.join(output_dir, "rul_classification_metrics.csv"), index=False
    )

    print("[RESULT] RUL_FCA_BIN Classification Metrics")
    print(metrics)

    report = classification_report(y_test, preds, zero_division=0)

    with open(
        os.path.join(output_dir, "rul_classification_report.txt"),
        "w",
        encoding="utf-8",
    ) as f:
        f.write(report)

    labels = sorted(y.unique())

    cm = pd.DataFrame(
        confusion_matrix(y_test, preds, labels=labels),
        index=labels,
        columns=labels,
    )

    cm.to_csv(
        os.path.join(output_dir, "rul_classification_confusion_matrix.csv")
    )

    predictions_df = pd.DataFrame(
        {
            "actual_RUL_FCA_BIN": y_test.values,
            "predicted_RUL_FCA_BIN": preds,
        }
    )

    predictions_df.to_csv(
        os.path.join(output_dir, "rul_classification_predictions.csv"),
        index=False,
    )

    importance_df = export_feature_importance(
        pipeline=pipeline,
        output_path=os.path.join(
            output_dir,
            "rul_classification_feature_importance.csv"
        ),
    )

    # Plot: confusion matrix
    plt.figure(figsize=(8, 7))
    plt.imshow(cm.values, interpolation="nearest")
    plt.title("RUL_FCA_BIN Confusion Matrix")
    plt.xlabel("Predicted Class")
    plt.ylabel("Actual Class")
    plt.xticks(np.arange(len(labels)), labels, rotation=45, ha="right")
    plt.yticks(np.arange(len(labels)), labels)

    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            plt.text(j, i, str(cm.values[i, j]), ha="center", va="center")

    plt.colorbar()

    save_current_plot(
        os.path.join(plot_dir, "classification_confusion_matrix.png")
    )

    if not importance_df.empty:
        top_features = (
            importance_df.head(TOP_N_FEATURES)
            .set_index("feature")["importance"]
        )

        plot_bar_from_series(
            top_features,
            title=f"Top {TOP_N_FEATURES} Features for RUL_FCA_BIN Classification",
            xlabel="Importance",
            ylabel="Feature",
            path=os.path.join(
                plot_dir,
                "classification_feature_importance_top25.png",
            ),
        )

    # Plot: actual vs predicted class counts
    actual_counts = pd.Series(y_test.values).value_counts().sort_index()
    predicted_counts = pd.Series(preds).value_counts().sort_index()

    combined = pd.DataFrame(
        {"actual": actual_counts, "predicted": predicted_counts}
    ).fillna(0)

    plt.figure(figsize=(10, 6))
    combined.plot(kind="bar")

    plt.title("Actual vs Predicted RUL_FCA_BIN Distribution")
    plt.xlabel("RUL FCA Bin Class")
    plt.ylabel("Count")
    plt.xticks(rotation=45, ha="right")

    save_current_plot(
        os.path.join(
            plot_dir,
            "classification_actual_vs_predicted_distribution.png"
        )
    )

# ============================================================
# Decision tree rule extraction
# ============================================================
def run_decision_tree_rules(
    df: pd.DataFrame,
    output_dir: str,
    strict_no_resistance: bool = False,
):
    print("\n[INFO] Extracting decision-tree rules...")
    plot_dir = create_plot_dir(output_dir)

    # RUL LEAKAGE FIX: remove_leakage_columns now drops every column containing
    # "rul" except RUL_Class, plus all _BIN/_ENCODED columns.
    df_model = remove_leakage_columns(
        df, task="classification", strict_no_resistance=strict_no_resistance
    )
    X, y = split_features_target(df_model, TARGET_CLASSIFICATION)

    valid_idx = y.notna()
    X = X.loc[valid_idx]
    y = y.loc[valid_idx].astype(str)

    # V9: only pure numeric columns (no _BIN/_ENCODED after leakage removal)
    numeric_cols = X.select_dtypes(include=[np.number]).columns.tolist()
    if len(numeric_cols) == 0:
        print("[WARNING] No numeric columns available for decision tree rule extraction.")
        return

    X_num = X[numeric_cols].replace([np.inf, -np.inf], np.nan)
    X_num = X_num.fillna(X_num.median(numeric_only=True))

    # V9: scale numeric features before fitting decision tree
    scaler = StandardScaler()
    X_num_scaled = pd.DataFrame(
        scaler.fit_transform(X_num),
        columns=numeric_cols,
        index=X_num.index,
    )

    clf = DecisionTreeClassifier(
        max_depth=4,
        min_samples_leaf=10,
        random_state=RANDOM_STATE,
        class_weight="balanced",
    )
    clf.fit(X_num_scaled, y)

    rules = export_text(clf, feature_names=numeric_cols)
    with open(
        os.path.join(output_dir, "decision_tree_rules.txt"), "w", encoding="utf-8"
    ) as f:
        f.write(rules)
    print("[RESULT] Decision tree rules exported to decision_tree_rules.txt")

    importance = pd.Series(clf.feature_importances_, index=numeric_cols)
    importance = importance.sort_values(ascending=False)
    importance = importance[importance > 0]
    if not importance.empty:
        importance.to_csv(
            os.path.join(output_dir, "decision_tree_rule_feature_importance.csv")
        )
        plot_bar_from_series(
            importance.head(TOP_N_FEATURES),
            title="Decision Tree Rule Feature Importance",
            xlabel="Importance",
            ylabel="Feature",
            path=os.path.join(
                plot_dir, "decision_tree_rule_feature_importance.png"
            ),
        )

# ============================================================
# V9: Unsupervised matrix preparation
#     _BIN and _ENCODED columns are now explicitly excluded.
#     All values are scaled (StandardScaler) before analysis.
# ============================================================
def prepare_unsupervised_matrix(df: pd.DataFrame):
    """
    Builds the numeric feature matrix used for clustering, PCA and anomaly
    detection.

    V9 changes:
        - Explicitly excludes ALL columns ending with _BIN or _ENCODED via
          ``_get_analysis_cols()``, in addition to the target/leakage exclusions
          from V7.
        - Excludes ALL columns containing "rul" (case-insensitive) via the
          shared _get_analysis_cols() helper so that no RUL-derived signal
          dominates PCA axes or clustering distances.
        - Returns a StandardScaler-scaled matrix (as before) and also the
          plain DataFrame of raw column values so callers can inspect feature
          names.
    """
    # Use the V9 central helper – returns only raw sensor/process numeric cols,
    # with RUL-related columns already excluded.
    analysis_cols = _get_analysis_cols(df)

    # Also exclude equipment-id columns that are not process signals
    id_cols = {"sleeve", "num_crystallizer", "num_stream"}
    analysis_cols = [c for c in analysis_cols if c not in id_cols]

    if not analysis_cols:
        empty = np.empty((len(df), 0))
        return pd.DataFrame(index=df.index), empty

    X = df[analysis_cols].copy()
    X = X.replace([np.inf, -np.inf], np.nan)

    imputer = SimpleImputer(strategy="median")
    scaler  = StandardScaler()
    X_imputed = imputer.fit_transform(X)
    X_scaled  = scaler.fit_transform(X_imputed)
    return X, X_scaled

# ============================================================
# Helper: 2D / 3D PCA projection (shared by clustering & anomaly)
# ============================================================
def _get_pca2d(X_scaled: np.ndarray) -> tuple:
    pca        = PCA(n_components=2, random_state=RANDOM_STATE)
    components = pca.fit_transform(X_scaled)
    return pca, components

def _get_pca3d(X_scaled: np.ndarray) -> tuple:
    n_components = min(3, X_scaled.shape[1])
    pca          = PCA(n_components=n_components, random_state=RANDOM_STATE)
    components   = pca.fit_transform(X_scaled)
    return pca, components

# ============================================================
# K-Means rich visualisations
# ============================================================
def _plot_kmeans_elbow(X_scaled: np.ndarray, k_range, plot_dir: str):
    print("[INFO]   Computing K-Means elbow curve...")
    inertias = []
    for k in k_range:
        km = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=10)
        km.fit(X_scaled)
        inertias.append(km.inertia_)
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(list(k_range), inertias, marker="o", linewidth=2, color="#2196F3")
    ax.fill_between(list(k_range), inertias, alpha=0.15, color="#2196F3")
    ax.set_title("K-Means – Elbow Curve (Inertia)", fontsize=14, fontweight="bold")
    ax.set_xlabel("Number of Clusters (k)")
    ax.set_ylabel("Inertia (Within-Cluster SSE)")
    ax.grid(True, linestyle="--", alpha=0.5)
    save_current_plot(os.path.join(plot_dir, "kmeans_elbow_curve.png"))

def _plot_kmeans_silhouette_curve(X_scaled: np.ndarray, k_range, plot_dir: str):
    print("[INFO]   Computing K-Means silhouette scores...")
    sil_scores = []
    max_sil_rows = 5_000
    if X_scaled.shape[0] > max_sil_rows:
        rng = np.random.default_rng(RANDOM_STATE)
        idx = rng.choice(X_scaled.shape[0], max_sil_rows, replace=False)
        Xs  = X_scaled[idx]
    else:
        Xs = X_scaled
    for k in k_range:
        km     = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=10)
        labels = km.fit_predict(Xs)
        score  = silhouette_score(Xs, labels)
        sil_scores.append(score)
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(list(k_range), sil_scores, marker="s", linewidth=2, color="#4CAF50")
    ax.fill_between(list(k_range), sil_scores, alpha=0.15, color="#4CAF50")
    ax.set_title("K-Means – Silhouette Score vs k", fontsize=14, fontweight="bold")
    ax.set_xlabel("Number of Clusters (k)")
    ax.set_ylabel("Average Silhouette Score")
    ax.grid(True, linestyle="--", alpha=0.5)
    save_current_plot(os.path.join(plot_dir, "kmeans_silhouette_curve.png"))

def _plot_kmeans_silhouette_diagram(
    X_scaled: np.ndarray, labels: np.ndarray, k: int, plot_dir: str
):
    print("[INFO]   Plotting K-Means silhouette diagram...")
    max_rows = 5_000
    if X_scaled.shape[0] > max_rows:
        rng = np.random.default_rng(RANDOM_STATE)
        idx = rng.choice(X_scaled.shape[0], max_rows, replace=False)
        Xs  = X_scaled[idx]
        ls  = labels[idx]
    else:
        Xs = X_scaled
        ls = labels
    sample_sil = silhouette_samples(Xs, ls)
    colours    = _cluster_colours(k)
    fig, ax    = plt.subplots(figsize=(10, 7))
    y_lower = 10
    for i in range(k):
        cluster_vals = np.sort(sample_sil[ls == i])
        size_cluster = cluster_vals.shape[0]
        y_upper      = y_lower + size_cluster
        ax.fill_betweenx(
            np.arange(y_lower, y_upper),
            0,
            cluster_vals,
            facecolor=colours[i],
            alpha=0.8,
            label=f"Cluster {i}",
        )
        ax.text(-0.05, y_lower + 0.5 * size_cluster, str(i), fontsize=9)
        y_lower = y_upper + 10
    avg_score = np.mean(sample_sil)
    ax.axvline(x=avg_score, color="red", linestyle="--",
               label=f"Mean = {avg_score:.3f}")
    ax.set_title(
        f"K-Means Silhouette Diagram  (k={k})", fontsize=14, fontweight="bold"
    )
    ax.set_xlabel("Silhouette Coefficient")
    ax.set_ylabel("Cluster")
    ax.legend(loc="lower right", fontsize=8)
    ax.grid(True, axis="x", linestyle="--", alpha=0.4)
    save_current_plot(os.path.join(plot_dir, "kmeans_silhouette_diagram.png"))

def _plot_kmeans_pca2d(
    components: np.ndarray,
    labels: np.ndarray,
    pca,
    k: int,
    rul_values,
    plot_dir: str,
):
    print("[INFO]   Plotting K-Means 2D PCA scatter...")
    colours = _cluster_colours(k)
    fig, ax = plt.subplots(figsize=(10, 7))
    for i in range(k):
        mask = labels == i
        ax.scatter(
            components[mask, 0], components[mask, 1],
            s=14, alpha=0.65, color=colours[i], label=f"Cluster {i}",
        )
    ax.set_title("K-Means Clusters – PCA 2D Projection", fontsize=14, fontweight="bold")
    ax.set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0]:.2%} variance)")
    ax.set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1]:.2%} variance)")
    ax.legend(title="Cluster", fontsize=9, loc="best")
    ax.grid(True, linestyle="--", alpha=0.3)
    save_current_plot(os.path.join(plot_dir, "kmeans_pca2d_scatter.png"))

    if rul_values is not None and len(rul_values) == len(components):
        fig, ax = plt.subplots(figsize=(10, 7))
        sc = ax.scatter(
            components[:, 0], components[:, 1],
            c=rul_values, cmap="plasma", s=14, alpha=0.65,
        )
        plt.colorbar(sc, ax=ax, label="RUL (tons)")
        for i in range(k):
            mask = labels == i
            cx, cy = components[mask, 0].mean(), components[mask, 1].mean()
            ax.scatter(cx, cy, marker="X", s=180, color="black", zorder=5,
                       edgecolors="white", linewidths=0.8)
            ax.text(cx, cy + 0.1, f" C{i}", fontsize=9, ha="center",
                    color="black", fontweight="bold")
        ax.set_title(
            "K-Means Clusters – PCA 2D coloured by RUL (tons)",
            fontsize=14, fontweight="bold",
        )
        ax.set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0]:.2%} variance)")
        ax.set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1]:.2%} variance)")
        ax.grid(True, linestyle="--", alpha=0.3)
        save_current_plot(os.path.join(plot_dir, "kmeans_pca2d_rul_heatmap.png"))

def _plot_kmeans_pca3d(
    components3d: np.ndarray, labels: np.ndarray, k: int, plot_dir: str
):
    if components3d.shape[1] < 3:
        return
    print("[INFO]   Plotting K-Means 3D PCA scatter...")
    colours = _cluster_colours(k)
    fig     = plt.figure(figsize=(12, 8))
    ax      = fig.add_subplot(111, projection="3d")
    for i in range(k):
        mask = labels == i
        ax.scatter(
            components3d[mask, 0], components3d[mask, 1], components3d[mask, 2],
            s=10, alpha=0.55, color=colours[i], label=f"Cluster {i}",
        )
    ax.set_title("K-Means Clusters – PCA 3D Projection", fontsize=13, fontweight="bold")
    ax.set_xlabel("PC1")
    ax.set_ylabel("PC2")
    ax.set_zlabel("PC3")
    ax.legend(title="Cluster", fontsize=8)
    save_current_plot(os.path.join(plot_dir, "kmeans_pca3d_scatter.png"))

def _plot_kmeans_centroid_heatmap(
    X_scaled: np.ndarray,
    labels: np.ndarray,
    feature_names: list,
    k: int,
    plot_dir: str,
):
    print("[INFO]   Plotting K-Means centroid heatmap...")
    n_features_show = min(20, len(feature_names))
    centroids       = np.array([X_scaled[labels == i].mean(axis=0) for i in range(k)])
    feature_var     = centroids.var(axis=0)
    top_idx         = np.argsort(feature_var)[::-1][:n_features_show]
    centroid_subset = centroids[:, top_idx]
    feat_subset     = [feature_names[i] for i in top_idx]
    fig, ax = plt.subplots(figsize=(max(8, n_features_show * 0.5), k + 2))
    im = ax.imshow(centroid_subset, aspect="auto", cmap="RdBu_r")
    ax.set_xticks(range(n_features_show))
    ax.set_xticklabels(
        [f[:25] for f in feat_subset], rotation=60, ha="right", fontsize=8
    )
    ax.set_yticks(range(k))
    ax.set_yticklabels([f"Cluster {i}" for i in range(k)])
    ax.set_title(
        "K-Means Centroid Heatmap\n(Top features by inter-cluster variance)",
        fontsize=13, fontweight="bold",
    )
    plt.colorbar(im, ax=ax, label="Normalised mean value (scaled)")
    save_current_plot(os.path.join(plot_dir, "kmeans_centroid_heatmap.png"))

def _plot_kmeans_rul_boxplot(
    labels: np.ndarray, rul_values, k: int, plot_dir: str
):
    if rul_values is None:
        return
    print("[INFO]   Plotting K-Means RUL box-plot per cluster...")
    data_by_cluster = [rul_values[labels == i] for i in range(k)]
    data_by_cluster = [d[~np.isnan(d)] for d in data_by_cluster]
    colours         = _cluster_colours(k)
    fig, ax         = plt.subplots(figsize=(10, 6))
    bp = ax.boxplot(data_by_cluster, patch_artist=True, notch=False)
    for patch, colour in zip(bp["boxes"], colours):
        patch.set_facecolor(colour)
        patch.set_alpha(0.75)
    ax.set_xticks(range(1, k + 1))
    ax.set_xticklabels([f"Cluster {i}" for i in range(k)])
    ax.set_title(
        "RUL (tons) Distribution per K-Means Cluster", fontsize=14, fontweight="bold"
    )
    ax.set_xlabel("K-Means Cluster")
    ax.set_ylabel("RUL (tons)")
    ax.grid(True, axis="y", linestyle="--", alpha=0.5)
    save_current_plot(os.path.join(plot_dir, "kmeans_rul_boxplot.png"))

# ============================================================
# DBSCAN helpers
# ============================================================
def _estimate_dbscan_eps(
    X_scaled: np.ndarray, min_samples: int, plot_dir: str
) -> float:
    print("[INFO]   Computing DBSCAN k-distance curve and estimating eps...")
    max_rows = 5_000
    if X_scaled.shape[0] > max_rows:
        rng = np.random.default_rng(RANDOM_STATE)
        idx = rng.choice(X_scaled.shape[0], max_rows, replace=False)
        Xs  = X_scaled[idx]
    else:
        Xs = X_scaled

    nbrs               = NearestNeighbors(n_neighbors=min_samples).fit(Xs)
    distances, _       = nbrs.kneighbors(Xs)
    kth_distances      = np.sort(distances[:, -1])[::-1]

    if len(kth_distances) >= 5:
        smooth_window = max(3, len(kth_distances) // 100)
        smoothed      = np.convolve(
            kth_distances, np.ones(smooth_window) / smooth_window, mode="valid"
        )
        second_diff   = np.diff(np.diff(smoothed))
        search_end    = max(1, int(len(second_diff) * 0.6))
        knee_idx      = int(np.argmax(second_diff[:search_end]))
        knee_idx      = min(knee_idx + smooth_window, len(kth_distances) - 1)
    else:
        knee_idx = len(kth_distances) // 2

    eps_auto = float(kth_distances[knee_idx])
    print(
        f"[INFO]   DBSCAN knee at index {knee_idx}, "
        f"auto-estimated eps = {eps_auto:.4f}"
    )

    fig, ax = plt.subplots(figsize=(10, 5))
    x_vals  = np.arange(len(kth_distances))
    ax.plot(x_vals, kth_distances, linewidth=1.5, color="#FF5722",
            label=f"{min_samples}-NN distance")
    ax.axhline(y=eps_auto, color="#1565C0", linestyle="--", linewidth=1.5,
               label=f"Auto eps ≈ {eps_auto:.3f}")
    ax.axvline(x=knee_idx, color="#1565C0", linestyle=":", linewidth=1.2, alpha=0.7)
    ax.annotate(
        f"Knee  (eps ≈ {eps_auto:.3f})",
        xy=(knee_idx, eps_auto),
        xytext=(
            knee_idx + max(10, int(len(kth_distances) * 0.05)),
            eps_auto + (kth_distances[0] - kth_distances[-1]) * 0.12,
        ),
        fontsize=9,
        color="#1565C0",
        arrowprops=dict(arrowstyle="->", color="#1565C0", lw=1.5),
    )
    ax.set_title(
        f"DBSCAN – k-Distance Graph  (k={min_samples})\n"
        f"Auto-estimated eps = {eps_auto:.4f}",
        fontsize=13, fontweight="bold",
    )
    ax.set_xlabel("Points sorted by k-NN distance (descending)")
    ax.set_ylabel(f"Distance to {min_samples}-th Nearest Neighbour")
    ax.legend(fontsize=9)
    ax.grid(True, linestyle="--", alpha=0.4)
    save_current_plot(os.path.join(plot_dir, "dbscan_kdistance_plot.png"))
    return eps_auto

def _plot_dbscan_pca2d(
    components: np.ndarray,
    labels: np.ndarray,
    pca,
    eps: float,
    min_samples: int,
    plot_dir: str,
):
    print("[INFO]   Plotting DBSCAN 2D PCA scatter...")
    unique_labels  = sorted(set(labels))
    cluster_labels = [l for l in unique_labels if l != -1]
    n_clusters     = len(cluster_labels)
    colours        = _cluster_colours(max(n_clusters, 1))
    colour_map     = {lbl: colours[ci % len(colours)]
                      for ci, lbl in enumerate(cluster_labels)}
    noise_mask     = labels == -1
    n_noise        = int(noise_mask.sum())
    n_total        = len(labels)

    fig, ax = plt.subplots(figsize=(12, 8))
    if n_clusters == 0:
        ax.scatter(
            components[:, 0], components[:, 1],
            s=18, alpha=0.6, color=_NOISE_COLOR,
            marker="x", label=f"Noise (n={n_total})",
        )
        ax.set_title(
            f"DBSCAN – PCA 2D  (eps={eps:.3f}, min_samples={min_samples})\n"
            f"⚠ All {n_total} points classified as NOISE — try a larger eps",
            fontsize=13, fontweight="bold", color="#B71C1C",
        )
    else:
        for lbl in cluster_labels:
            mask = labels == lbl
            cnt  = int(mask.sum())
            ax.scatter(
                components[mask, 0], components[mask, 1],
                s=15, alpha=0.60, color=colour_map[lbl],
                label=f"Cluster {lbl}  (n={cnt})",
            )
            cx = components[mask, 0].mean()
            cy = components[mask, 1].mean()
            ax.scatter(cx, cy, marker="D", s=120, color=colour_map[lbl],
                       edgecolors="black", linewidths=0.8, zorder=6)
            ax.text(cx, cy, f" C{lbl}", fontsize=8, fontweight="bold",
                    color="black", zorder=7, va="center")
        if n_noise > 0:
            ax.scatter(
                components[noise_mask, 0], components[noise_mask, 1],
                s=22, alpha=0.75, color=_NOISE_COLOR,
                marker="x", linewidths=0.8,
                label=f"Noise  (n={n_noise}, {n_noise/n_total:.1%})",
                zorder=5,
            )
        noise_pct = f"{n_noise/n_total:.1%}" if n_noise > 0 else "0 %"
        ax.set_title(
            f"DBSCAN Clusters – PCA 2D Projection\n"
            f"eps={eps:.3f}  |  min_samples={min_samples}  |  "
            f"{n_clusters} cluster(s)  |  noise: {noise_pct}",
            fontsize=13, fontweight="bold",
        )
    ax.set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0]:.2%} variance)")
    ax.set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1]:.2%} variance)")
    ax.legend(title="DBSCAN label", fontsize=8, loc="best", markerscale=1.5,
              framealpha=0.85)
    ax.grid(True, linestyle="--", alpha=0.3)
    save_current_plot(os.path.join(plot_dir, "dbscan_pca2d_scatter.png"))

    if n_noise > 0 and n_clusters > 0:
        fig2, ax2 = plt.subplots(figsize=(12, 8))
        ax2.scatter(
            components[~noise_mask, 0], components[~noise_mask, 1],
            s=12, alpha=0.25, color="#90CAF9",
            label=f"Clustered points  (n={n_total - n_noise})",
        )
        ax2.scatter(
            components[noise_mask, 0], components[noise_mask, 1],
            s=30, alpha=0.90, color="#EF5350",
            marker="x", linewidths=1.2,
            label=f"Noise / outliers  (n={n_noise})",
        )
        ax2.set_title(
            f"DBSCAN – Noise Points Highlighted\n"
            f"eps={eps:.3f}  |  min_samples={min_samples}  |  "
            f"noise rate: {n_noise/n_total:.1%}",
            fontsize=13, fontweight="bold",
        )
        ax2.set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0]:.2%} variance)")
        ax2.set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1]:.2%} variance)")
        ax2.legend(fontsize=9, loc="best", framealpha=0.85)
        ax2.grid(True, linestyle="--", alpha=0.3)
        save_current_plot(
            os.path.join(plot_dir, "dbscan_noise_highlight_scatter.png")
        )

def _plot_dbscan_cluster_sizes(labels: np.ndarray, plot_dir: str):
    print("[INFO]   Plotting DBSCAN cluster sizes...")
    unique_labels, counts = np.unique(labels, return_counts=True)
    label_names = ["Noise" if l == -1 else f"Cluster {l}" for l in unique_labels]
    bar_colours = [
        _NOISE_COLOR if l == -1 else plt.get_cmap("tab10")(i % 10)
        for i, l in enumerate(unique_labels)
    ]
    fig, ax = plt.subplots(figsize=(max(8, len(unique_labels)), 5))
    bars = ax.bar(
        label_names, counts, color=bar_colours, edgecolor="white", linewidth=0.8
    )
    for bar, cnt in zip(bars, counts):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(counts) * 0.01,
            str(cnt), ha="center", va="bottom", fontsize=9, fontweight="bold",
        )
    ax.set_title(
        "DBSCAN Cluster Sizes (incl. Noise)", fontsize=14, fontweight="bold"
    )
    ax.set_xlabel("Cluster")
    ax.set_ylabel("Number of Points")
    ax.grid(True, axis="y", linestyle="--", alpha=0.4)
    save_current_plot(os.path.join(plot_dir, "dbscan_cluster_sizes_bar.png"))

def _plot_dbscan_rul_per_cluster(labels: np.ndarray, rul_values, plot_dir: str):
    if rul_values is None:
        return
    print("[INFO]   Plotting DBSCAN average RUL per cluster...")
    unique_labels   = sorted(set(labels))
    means, label_names = [], []
    for lbl in unique_labels:
        mask = labels == lbl
        vals = rul_values[mask]
        vals = vals[~np.isnan(vals)]
        if len(vals) > 0:
            means.append(vals.mean())
            label_names.append("Noise" if lbl == -1 else f"Cluster {lbl}")
    bar_colours = [
        _NOISE_COLOR if "Noise" in n else plt.get_cmap("tab10")(i % 10)
        for i, n in enumerate(label_names)
    ]
    fig, ax = plt.subplots(figsize=(max(8, len(label_names)), 5))
    bars    = ax.bar(
        label_names, means, color=bar_colours, edgecolor="white", linewidth=0.8
    )
    for bar, val in zip(bars, means):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(means) * 0.01,
            f"{val:.1f}", ha="center", va="bottom", fontsize=9, fontweight="bold",
        )
    ax.set_title(
        "DBSCAN – Average RUL (tons) per Cluster", fontsize=14, fontweight="bold"
    )
    ax.set_xlabel("Cluster")
    ax.set_ylabel("Average RUL (tons)")
    ax.grid(True, axis="y", linestyle="--", alpha=0.4)
    save_current_plot(
        os.path.join(plot_dir, "dbscan_average_rul_per_cluster.png")
    )

def _plot_dbscan_rul_boxplot(labels: np.ndarray, rul_values, plot_dir: str):
    if rul_values is None:
        return
    print("[INFO]   Plotting DBSCAN RUL box-plot per label...")
    unique_labels = sorted(set(labels))
    data_groups, tick_labels, colours, hatches = [], [], [], []
    cluster_labels_only = [l for l in unique_labels if l != -1]
    cluster_colours     = _cluster_colours(max(len(cluster_labels_only), 1))
    ci = 0
    for lbl in unique_labels:
        mask = labels == lbl
        vals = rul_values[mask]
        vals = vals[~np.isnan(vals)]
        if len(vals) == 0:
            continue
        data_groups.append(vals)
        if lbl == -1:
            tick_labels.append("Noise")
            colours.append(_NOISE_COLOR)
            hatches.append("//")
        else:
            tick_labels.append(f"Cluster {lbl}")
            colours.append(cluster_colours[ci % len(cluster_colours)])
            hatches.append("")
            ci += 1
    if len(data_groups) < 2:
        return
    fig, ax = plt.subplots(figsize=(max(8, len(data_groups) * 1.2), 6))
    bp      = ax.boxplot(data_groups, patch_artist=True, notch=False)
    for patch, colour, hatch in zip(bp["boxes"], colours, hatches):
        patch.set_facecolor(colour)
        patch.set_alpha(0.75)
        patch.set_hatch(hatch)
    ax.set_xticks(range(1, len(tick_labels) + 1))
    ax.set_xticklabels(tick_labels, rotation=15, ha="right")
    ax.set_title(
        "RUL (tons) Distribution per DBSCAN Label\n(Noise shown with hatching)",
        fontsize=14, fontweight="bold",
    )
    ax.set_xlabel("DBSCAN Label")
    ax.set_ylabel("RUL (tons)")
    ax.grid(True, axis="y", linestyle="--", alpha=0.5)
    save_current_plot(os.path.join(plot_dir, "dbscan_rul_boxplot.png"))

# ============================================================
# Isolation Forest rich visualisations
# ============================================================
def _plot_iforest_pca2d_scatter(
    components: np.ndarray,
    pca,
    is_anomaly: np.ndarray,
    scores: np.ndarray,
    plot_dir: str,
):
    print("[INFO]   Plotting Isolation Forest PCA 2D scatter...")
    fig, ax      = plt.subplots(figsize=(10, 7))
    normal_mask  = is_anomaly == 0
    anomaly_mask = is_anomaly == 1
    ax.scatter(components[normal_mask, 0], components[normal_mask, 1],
               s=12, alpha=0.5, color="#42A5F5", label="Normal")
    ax.scatter(components[anomaly_mask, 0], components[anomaly_mask, 1],
               s=28, alpha=0.9, color="#EF5350", marker="^", label="Anomaly",
               edgecolors="darkred", linewidths=0.5)
    ax.set_title(
        "Isolation Forest – Anomalies on PCA 2D Projection",
        fontsize=14, fontweight="bold",
    )
    ax.set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0]:.2%} variance)")
    ax.set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1]:.2%} variance)")
    ax.legend(fontsize=10)
    ax.grid(True, linestyle="--", alpha=0.3)
    save_current_plot(os.path.join(plot_dir, "iforest_pca2d_anomaly_scatter.png"))

    fig, ax = plt.subplots(figsize=(10, 7))
    sc = ax.scatter(
        components[:, 0], components[:, 1],
        c=scores, cmap="RdYlGn", s=14, alpha=0.7,
        vmin=scores.min(), vmax=scores.max(),
    )
    plt.colorbar(sc, ax=ax, label="Anomaly Score (higher = more normal)")
    ax.set_title(
        "Isolation Forest – Anomaly Score on PCA 2D", fontsize=14, fontweight="bold"
    )
    ax.set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0]:.2%} variance)")
    ax.set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1]:.2%} variance)")
    ax.grid(True, linestyle="--", alpha=0.3)
    save_current_plot(os.path.join(plot_dir, "iforest_pca2d_score_heatmap.png"))

def _plot_iforest_score_distribution(
    scores: np.ndarray, is_anomaly: np.ndarray, plot_dir: str
):
    print("[INFO]   Plotting Isolation Forest score distribution...")
    normal_scores  = scores[is_anomaly == 0]
    anomaly_scores = scores[is_anomaly == 1]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.hist(normal_scores, bins=50, alpha=0.6, color="#42A5F5",
            label=f"Normal (n={len(normal_scores)})", density=True)
    ax.hist(anomaly_scores, bins=30, alpha=0.7, color="#EF5350",
            label=f"Anomaly (n={len(anomaly_scores)})", density=True)
    ax.axvline(normal_scores.mean(), color="#1565C0", linestyle="--", linewidth=1.5,
               label=f"Normal mean={normal_scores.mean():.3f}")
    ax.axvline(anomaly_scores.mean(), color="#B71C1C", linestyle="--", linewidth=1.5,
               label=f"Anomaly mean={anomaly_scores.mean():.3f}")
    ax.set_title(
        "Isolation Forest – Anomaly Score Distribution by Class",
        fontsize=14, fontweight="bold",
    )
    ax.set_xlabel("Decision Function Score")
    ax.set_ylabel("Density")
    ax.legend(fontsize=9)
    ax.grid(True, axis="y", linestyle="--", alpha=0.4)
    save_current_plot(
        os.path.join(plot_dir, "iforest_score_distribution_by_class.png")
    )

def _plot_iforest_violin(
    scores: np.ndarray, is_anomaly: np.ndarray, plot_dir: str
):
    print("[INFO]   Plotting Isolation Forest violin plot...")
    normal_scores  = scores[is_anomaly == 0]
    anomaly_scores = scores[is_anomaly == 1]
    fig, ax = plt.subplots(figsize=(8, 6))
    parts   = ax.violinplot(
        [normal_scores, anomaly_scores],
        positions=[1, 2], showmedians=True, showextrema=True,
    )
    colours = ["#42A5F5", "#EF5350"]
    for i, pc in enumerate(parts["bodies"]):
        pc.set_facecolor(colours[i])
        pc.set_alpha(0.75)
    parts["cmedians"].set_color("black")
    parts["cmaxes"].set_color("grey")
    parts["cmins"].set_color("grey")
    parts["cbars"].set_color("grey")
    ax.set_xticks([1, 2])
    ax.set_xticklabels(["Normal", "Anomaly"])
    ax.set_title(
        "Isolation Forest – Score Violin Plot", fontsize=14, fontweight="bold"
    )
    ax.set_ylabel("Decision Function Score")
    ax.grid(True, axis="y", linestyle="--", alpha=0.4)
    save_current_plot(os.path.join(plot_dir, "iforest_score_violin.png"))

def _plot_iforest_anomaly_by_rul_class(
    is_anomaly: np.ndarray, rul_class_values, plot_dir: str
):
    if rul_class_values is None:
        return
    print("[INFO]   Plotting Isolation Forest anomaly rate per RUL_FCA_BIN...")
    tmp = pd.DataFrame({"is_anomaly": is_anomaly, "rul_class": rul_class_values})
    tmp = tmp.dropna(subset=["rul_class"])
    tmp["rul_class"] = tmp["rul_class"].astype(str)
    grouped = (
        tmp.groupby("rul_class")["is_anomaly"]
        .value_counts(normalize=True)
        .unstack(fill_value=0)
    )
    grouped.columns = ["Normal" if c == 0 else "Anomaly" for c in grouped.columns]
    if "Normal" not in grouped.columns:
        grouped["Normal"] = 0
    if "Anomaly" not in grouped.columns:
        grouped["Anomaly"] = 0
    grouped = grouped[["Normal", "Anomaly"]]
    fig, ax = plt.subplots(figsize=(max(8, len(grouped) * 0.8), 6))
    grouped.plot(
        kind="bar", stacked=True, ax=ax,
        color=["#42A5F5", "#EF5350"], edgecolor="white", linewidth=0.5,
    )
    ax.set_title(
        "Isolation Forest – Anomaly Proportion per RUL_FCA_BIN",
        fontsize=14, fontweight="bold",
    )
    ax.set_xlabel("RUL FCA Bin")
    ax.set_ylabel("Proportion")
    ax.set_ylim(0, 1.05)
    ax.legend(title="State", fontsize=10)
    plt.xticks(rotation=30, ha="right")
    ax.grid(True, axis="y", linestyle="--", alpha=0.4)
    save_current_plot(
        os.path.join(plot_dir, "iforest_anomaly_proportion_per_rul_class.png")
    )

def _plot_iforest_rul_vs_score(
    scores: np.ndarray, rul_values, is_anomaly: np.ndarray, plot_dir: str
):
    if rul_values is None:
        return
    print("[INFO]   Plotting Isolation Forest RUL vs score scatter...")
    valid = ~np.isnan(rul_values)
    r = rul_values[valid]
    s = scores[valid]
    a = is_anomaly[valid]
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(r[a == 0], s[a == 0], s=12, alpha=0.5, color="#42A5F5", label="Normal")
    ax.scatter(r[a == 1], s[a == 1], s=28, alpha=0.85, color="#EF5350", marker="^",
               label="Anomaly", edgecolors="darkred", linewidths=0.5)
    ax.set_title(
        "Isolation Forest – RUL (tons) vs Anomaly Score",
        fontsize=14, fontweight="bold",
    )
    ax.set_xlabel("RUL (tons)")
    ax.set_ylabel("Anomaly Score (higher = more normal)")
    ax.legend(fontsize=10)
    ax.grid(True, linestyle="--", alpha=0.3)
    save_current_plot(os.path.join(plot_dir, "iforest_rul_vs_score_scatter.png"))

# ============================================================
# Unsupervised learning: clustering
# ============================================================
def run_clustering(df: pd.DataFrame, output_dir: str):
    print(
        "\n[INFO] Running unsupervised clustering "
        "(K-Means + DBSCAN with rich plots)..."
    )
    plot_dir = create_plot_dir(output_dir)
    X_df, X_scaled = prepare_unsupervised_matrix(df)
    if X_scaled.shape[1] == 0:
        print("[WARNING] No numerical columns available for clustering.")
        return
    feature_names = list(X_df.columns)
    rul_values    = (
        df[TARGET_REGRESSION].values.astype(float)
        if TARGET_REGRESSION in df.columns
        else None
    )

    pca2d, components2d = _get_pca2d(X_scaled)
    pca3d, components3d = _get_pca3d(X_scaled)

    # ---- K-Means ----
    print("\n[INFO] --- K-Means clustering ---")
    _plot_kmeans_elbow(X_scaled, KMEANS_K_RANGE, plot_dir)
    _plot_kmeans_silhouette_curve(X_scaled, KMEANS_K_RANGE, plot_dir)
    kmeans        = KMeans(
        n_clusters=KMEANS_N_CLUSTERS, random_state=RANDOM_STATE, n_init=10
    )
    kmeans_labels = kmeans.fit_predict(X_scaled)
    _plot_kmeans_silhouette_diagram(X_scaled, kmeans_labels, KMEANS_N_CLUSTERS, plot_dir)
    _plot_kmeans_pca2d(
        components2d, kmeans_labels, pca2d, KMEANS_N_CLUSTERS, rul_values, plot_dir
    )
    _plot_kmeans_pca3d(components3d, kmeans_labels, KMEANS_N_CLUSTERS, plot_dir)
    _plot_kmeans_centroid_heatmap(
        X_scaled, kmeans_labels, feature_names, KMEANS_N_CLUSTERS, plot_dir
    )
    _plot_kmeans_rul_boxplot(kmeans_labels, rul_values, KMEANS_N_CLUSTERS, plot_dir)

    cluster_counts = pd.Series(kmeans_labels).value_counts().sort_index()
    plot_bar_from_series(
        cluster_counts,
        title="K-Means Cluster Sizes",
        xlabel="Count",
        ylabel="Cluster",
        path=os.path.join(plot_dir, "clustering_kmeans_cluster_sizes.png"),
    )
    if rul_values is not None:
        avg_rul = (
            pd.Series(rul_values)
            .groupby(pd.Series(kmeans_labels))
            .mean()
            .sort_values(ascending=False)
        )
        plot_bar_from_series(
            avg_rul,
            title="Average RUL (tons) by K-Means Cluster",
            xlabel="Average RUL (tons)",
            ylabel="K-Means Cluster",
            path=os.path.join(plot_dir, "clustering_average_rul_by_kmeans_cluster.png"),
        )

    # ---- DBSCAN ----
    print("\n[INFO] --- DBSCAN clustering ---")
    if DBSCAN_EPS_OVERRIDE is not None and DBSCAN_EPS_OVERRIDE > 0:
        eps = float(DBSCAN_EPS_OVERRIDE)
        print(f"[INFO]   Using manual eps override: {eps}")
        _estimate_dbscan_eps(X_scaled, DBSCAN_MIN_SAMPLES, plot_dir)
    else:
        eps = _estimate_dbscan_eps(X_scaled, DBSCAN_MIN_SAMPLES, plot_dir)

    dbscan        = DBSCAN(eps=eps, min_samples=DBSCAN_MIN_SAMPLES)
    dbscan_labels = dbscan.fit_predict(X_scaled)
    n_clusters_found = len(set(dbscan_labels) - {-1})
    n_noise_found    = int((dbscan_labels == -1).sum())
    print(
        f"[INFO]   DBSCAN result: {n_clusters_found} cluster(s), "
        f"{n_noise_found} noise point(s) "
        f"({n_noise_found / len(dbscan_labels):.1%} of data)"
    )

    _plot_dbscan_pca2d(
        components2d, dbscan_labels, pca2d, eps, DBSCAN_MIN_SAMPLES, plot_dir
    )
    _plot_dbscan_cluster_sizes(dbscan_labels, plot_dir)
    _plot_dbscan_rul_per_cluster(dbscan_labels, rul_values, plot_dir)
    _plot_dbscan_rul_boxplot(dbscan_labels, rul_values, plot_dir)

    dbscan_counts = pd.Series(dbscan_labels).value_counts().sort_index()
    plot_bar_from_series(
        dbscan_counts,
        title="DBSCAN Cluster Sizes",
        xlabel="Count",
        ylabel="DBSCAN Cluster",
        path=os.path.join(plot_dir, "clustering_dbscan_cluster_sizes.png"),
    )

    # ---- Save combined results ----
    result = pd.DataFrame(
        {"kmeans_cluster": kmeans_labels, "dbscan_cluster": dbscan_labels}
    )
    if TARGET_REGRESSION in df.columns:
        result[TARGET_REGRESSION] = df[TARGET_REGRESSION].values
    if TARGET_CLASSIFICATION in df.columns:
        result[TARGET_CLASSIFICATION] = df[TARGET_CLASSIFICATION].values
    result.to_csv(
        os.path.join(output_dir, "clustering_results.csv"), index=False
    )

    if TARGET_REGRESSION in result.columns:
        summary = result.groupby("kmeans_cluster").agg(
            count=("kmeans_cluster", "size"),
            avg_RUL=(TARGET_REGRESSION, "mean"),
            median_RUL=(TARGET_REGRESSION, "median"),
            min_RUL=(TARGET_REGRESSION, "min"),
            max_RUL=(TARGET_REGRESSION, "max"),
        )
    else:
        summary = result.groupby("kmeans_cluster").agg(
            count=("kmeans_cluster", "size")
        )
    summary.to_csv(os.path.join(output_dir, "kmeans_cluster_summary.csv"))
    print("[RESULT] Clustering results and plots exported.")

# ============================================================
# PCA  (V9: _BIN/_ENCODED and all *RUL* columns excluded from feature matrix)
# ============================================================
def run_pca(df: pd.DataFrame, output_dir: str):
    print("\n[INFO] Running PCA dimensionality reduction...")
    plot_dir      = create_plot_dir(output_dir)
    _, X_scaled   = prepare_unsupervised_matrix(df)
    if X_scaled.shape[1] < 2:
        print("[WARNING] Not enough numeric features for PCA.")
        return
    pca        = PCA(n_components=2, random_state=RANDOM_STATE)
    components = pca.fit_transform(X_scaled)
    pca_df     = pd.DataFrame({"PC1": components[:, 0], "PC2": components[:, 1]})
    if TARGET_REGRESSION in df.columns:
        pca_df[TARGET_REGRESSION] = df[TARGET_REGRESSION].values
    if TARGET_CLASSIFICATION in df.columns:
        pca_df[TARGET_CLASSIFICATION] = df[TARGET_CLASSIFICATION].values
    pca_df.to_csv(
        os.path.join(output_dir, "pca_2d_projection.csv"), index=False
    )
    explained = pd.DataFrame(
        {
            "component":               ["PC1", "PC2"],
            "explained_variance_ratio": pca.explained_variance_ratio_,
        }
    )
    explained.to_csv(
        os.path.join(output_dir, "pca_explained_variance.csv"), index=False
    )
    plt.figure(figsize=(10, 7))
    if TARGET_CLASSIFICATION in pca_df.columns:
        classes = pca_df[TARGET_CLASSIFICATION].astype(str).unique()
        for cls in sorted(classes):
            subset = pca_df[pca_df[TARGET_CLASSIFICATION].astype(str) == cls]
            plt.scatter(subset["PC1"], subset["PC2"], s=18, alpha=0.7, label=cls)
        plt.legend(title="RUL_FCA_BIN")
    else:
        plt.scatter(pca_df["PC1"], pca_df["PC2"], s=18, alpha=0.7)
    plt.title(
        "PCA 2D Projection\n"
        "(raw sensor/process columns only — no _BIN/_ENCODED, no RUL-derived)"
    )
    plt.xlabel(f"PC1 ({pca.explained_variance_ratio_[0]:.2%} variance)")
    plt.ylabel(f"PC2 ({pca.explained_variance_ratio_[1]:.2%} variance)")
    save_current_plot(os.path.join(plot_dir, "pca_2d_projection.png"))
    plt.figure(figsize=(8, 5))
    plt.bar(explained["component"], explained["explained_variance_ratio"])
    plt.title("PCA Explained Variance Ratio")
    plt.xlabel("Component")
    plt.ylabel("Explained Variance Ratio")
    save_current_plot(os.path.join(plot_dir, "pca_explained_variance.png"))
    print("[RESULT] PCA results and plots exported.")

# ============================================================
# Anomaly detection  (V9: _BIN/_ENCODED and all *RUL* columns excluded)
# ============================================================
def run_anomaly_detection(df: pd.DataFrame, output_dir: str):
    print(
        "\n[INFO] Running anomaly detection "
        "(Isolation Forest with rich plots)..."
    )
    plot_dir        = create_plot_dir(output_dir)
    X_df, X_scaled  = prepare_unsupervised_matrix(df)
    if X_scaled.shape[1] == 0:
        print("[WARNING] No numeric columns available for anomaly detection.")
        return
    iso = IsolationForest(
        n_estimators=300, contamination=0.05, random_state=RANDOM_STATE
    )
    raw_labels = iso.fit_predict(X_scaled)
    scores     = iso.decision_function(X_scaled)
    is_anomaly = (raw_labels == -1).astype(int)

    rul_values       = (
        df[TARGET_REGRESSION].values.astype(float)
        if TARGET_REGRESSION in df.columns
        else None
    )
    rul_class_values = (
        df[TARGET_CLASSIFICATION].values
        if TARGET_CLASSIFICATION in df.columns
        else None
    )

    anomaly_df = pd.DataFrame(
        {
            "anomaly_label": raw_labels,
            "anomaly_score": scores,
            "is_anomaly":    is_anomaly,
        }
    )
    if TARGET_REGRESSION in df.columns:
        anomaly_df[TARGET_REGRESSION] = df[TARGET_REGRESSION].values
    if TARGET_CLASSIFICATION in df.columns:
        anomaly_df[TARGET_CLASSIFICATION] = df[TARGET_CLASSIFICATION].values
    anomaly_df.to_csv(
        os.path.join(output_dir, "anomaly_detection_results.csv"), index=False
    )

    pca2d, components2d = _get_pca2d(X_scaled)
    _plot_iforest_pca2d_scatter(components2d, pca2d, is_anomaly, scores, plot_dir)
    _plot_iforest_score_distribution(scores, is_anomaly, plot_dir)
    _plot_iforest_violin(scores, is_anomaly, plot_dir)
    _plot_iforest_anomaly_by_rul_class(is_anomaly, rul_class_values, plot_dir)
    _plot_iforest_rul_vs_score(scores, rul_values, is_anomaly, plot_dir)

    plot_histogram(
        anomaly_df["anomaly_score"],
        title="Isolation Forest Anomaly Score Distribution",
        xlabel="Anomaly Score",
        ylabel="Frequency",
        path=os.path.join(plot_dir, "anomaly_score_distribution.png"),
    )
    anomaly_counts = (
        anomaly_df["is_anomaly"]
        .map({0: "Normal", 1: "Anomaly"})
        .value_counts()
    )
    plot_bar_from_series(
        anomaly_counts,
        title="Isolation Forest Normal vs Anomaly Count",
        xlabel="Count",
        ylabel="Label",
        path=os.path.join(plot_dir, "anomaly_normal_vs_anomaly_count.png"),
    )
    if TARGET_REGRESSION in anomaly_df.columns:
        avg_rul = anomaly_df.groupby("is_anomaly")[TARGET_REGRESSION].mean()
        avg_rul.index = avg_rul.index.map({0: "Normal", 1: "Anomaly"})
        plot_bar_from_series(
            avg_rul,
            title="Average RUL (tons) by Anomaly State",
            xlabel="Average RUL (tons)",
            ylabel="State",
            path=os.path.join(plot_dir, "anomaly_average_rul_by_state.png"),
        )
    print("[RESULT] Anomaly detection results and plots exported.")

# ============================================================
# Association rule mining  (V9: _BIN suffix, unchanged from V7)
# ============================================================
def run_association_rule_mining(df: pd.DataFrame, output_dir: str):
    print("\n[INFO] Running association rule mining on _BIN columns...")
    plot_dir = create_plot_dir(output_dir)

    if not MLXTEND_AVAILABLE:
        print("[WARNING] mlxtend is not installed.")
        print("Install it with: pip install mlxtend")
        return

    # Association rules intentionally operate on the _BIN discretised columns —
    # that is their purpose.  All other analyses exclude _BIN/_ENCODED.
    bin_cols = [c for c in df.columns if c.endswith("_BIN")]

    if len(bin_cols) < 2:
        print("[WARNING] Not enough _BIN columns for association rule mining.")
        return

    # Prioritise RUL-related bins so they appear as consequents
    target_cols = [c for c in bin_cols if "RUL" in c]
    other_cols  = [c for c in bin_cols if c not in target_cols]
    bin_cols    = (target_cols + other_cols)[:MAX_APRIORI_COLUMNS]

    print(
        f"[INFO] Association rule mining on {len(bin_cols)} _BIN columns "
        f"(capped at {MAX_APRIORI_COLUMNS})."
    )

    data         = df[bin_cols].copy()
    data         = data.fillna("Missing").astype(str)
    transactions = pd.DataFrame(index=data.index)
    for col in data.columns:
        dummies      = pd.get_dummies(data[col], prefix=col)
        transactions = pd.concat([transactions, dummies], axis=1)
    transactions = transactions.astype(bool)

    if len(transactions) > APRIORI_MAX_ROWS:
        transactions = transactions.sample(
            n=APRIORI_MAX_ROWS, random_state=RANDOM_STATE, replace=False
        )
        print(
            f"[INFO] Sampled {APRIORI_MAX_ROWS} rows for Apriori "
            f"(from {len(df)} total)."
        )

    print(
        f"[INFO] Running Apriori: min_support={APRIORI_MIN_SUPPORT}, "
        f"max_len={APRIORI_MAX_LEN}, "
        f"{transactions.shape[1]} one-hot columns, "
        f"{len(transactions)} rows..."
    )
    frequent_itemsets = apriori(
        transactions,
        min_support=APRIORI_MIN_SUPPORT,
        use_colnames=True,
        max_len=APRIORI_MAX_LEN,
    )
    if frequent_itemsets.empty:
        print("[WARNING] No frequent itemsets found. Try lowering min_support.")
        return

    rules = association_rules(
        frequent_itemsets, metric="lift", min_threshold=1.2
    )
    if rules.empty:
        print("[WARNING] No association rules found. Try lowering min_threshold.")
        frequent_itemsets.to_csv(
            os.path.join(output_dir, "frequent_itemsets.csv"), index=False
        )
        return

    rules["antecedents_str"]   = rules["antecedents"].apply(
        lambda x: ", ".join(sorted(list(x)))
    )
    rules["consequents_str"]   = rules["consequents"].apply(
        lambda x: ", ".join(sorted(list(x)))
    )
    rules["contains_RUL_target"] = rules["consequents_str"].apply(
        lambda x: "RUL_FCA_BIN" in x or "RUL" in x
    )
    rules = rules.sort_values(
        by=["contains_RUL_target", "lift", "confidence"],
        ascending=[False, False, False],
    )

    frequent_itemsets.to_csv(
        os.path.join(output_dir, "frequent_itemsets.csv"), index=False
    )
    rules.to_csv(os.path.join(output_dir, "association_rules.csv"), index=False)

    top_rules = rules.head(TOP_N_ASSOCIATION_RULES).copy()
    if not top_rules.empty:
        labels = [
            f"{row['antecedents_str']} => {row['consequents_str']}"
            for _, row in top_rules.iterrows()
        ]
        lift_series = pd.Series(top_rules["lift"].values, index=labels)
        plot_bar_from_series(
            lift_series,
            title=f"Top {TOP_N_ASSOCIATION_RULES} Association Rules by Lift",
            xlabel="Lift",
            ylabel="Rule",
            path=os.path.join(plot_dir, "association_rules_top_lift.png"),
        )
        confidence_series = pd.Series(top_rules["confidence"].values, index=labels)
        plot_bar_from_series(
            confidence_series,
            title=f"Top {TOP_N_ASSOCIATION_RULES} Association Rules by Confidence",
            xlabel="Confidence",
            ylabel="Rule",
            path=os.path.join(plot_dir, "association_rules_top_confidence.png"),
        )
    print("[RESULT] Association rules and plots exported.")

# ============================================================
# First-layer text report  (V9: updated column references)
# ============================================================
def generate_first_layer_knowledge_report(df: pd.DataFrame, output_dir: str):
    print("\n[INFO] Generating first-layer knowledge report...")
    report_path = os.path.join(output_dir, "first_layer_knowledge_report.txt")
    lines = []
    lines.append("FIRST-LAYER KNOWLEDGE DISCOVERY REPORT  (V9 schema)")
    lines.append("=" * 70)
    lines.append("")
    lines.append(f"Dataset size: {df.shape[0]} rows, {df.shape[1]} columns")
    lines.append("")
    lines.append("V9 Analysis Notes")
    lines.append("-" * 70)
    lines.append(
        "All _BIN and _ENCODED columns are excluded from numeric analysis, "
        "PCA, clustering, anomaly detection, and correlation plots."
    )
    lines.append(
        "All numeric features are scaled with StandardScaler before "
        "distance-based or linear-algebraic analyses (PCA, K-Means, DBSCAN, "
        "Isolation Forest, Decision Tree)."
    )
    lines.append(
        "Association rule mining intentionally uses _BIN columns — that is "
        "their purpose."
    )
    lines.append("")
    lines.append("RUL LEAKAGE FIX (applied to all supervised tasks)")
    lines.append("-" * 70)
    lines.append(
        "Every column whose name contains 'rul' (case-insensitive) is a direct "
        "transformation of either supervised target and is therefore removed from "
        "all supervised feature matrices and EDA correlation analyses."
    )
    lines.append(
        "  Regression  (task='regression')  : all *rul* cols dropped except "
        "calculated_RUL_tons"
    )
    lines.append(
        "  Classification (task='classification'): all *rul* cols dropped except "
        "RUL_Class"
    )
    lines.append(
        "  EDA correlation / unsupervised    : all *rul* cols excluded from "
        "_get_analysis_cols()"
    )

    # Show which RUL-related columns were found in this dataset
    rul_cols_found = [c for c in df.columns if _is_rul_leakage(c)]
    lines.append(
        f"  RUL-related columns found in this dataset ({len(rul_cols_found)}): "
        + (", ".join(rul_cols_found) if rul_cols_found else "none")
    )
    lines.append("")

    analysis_cols = _get_analysis_cols(df)
    lines.append(
        f"Raw sensor/process columns used in analysis ({len(analysis_cols)}):"
    )
    lines.append("  " + ", ".join(analysis_cols))
    lines.append("")

    if TARGET_REGRESSION in df.columns:
        lines.append("Calculated RUL (tons) Summary")
        lines.append("-" * 70)
        lines.append(str(df[TARGET_REGRESSION].describe()))
        lines.append("")

    if "RUL_percentage" in df.columns:
        lines.append("RUL Percentage Summary")
        lines.append("-" * 70)
        lines.append(str(df["RUL_percentage"].describe()))
        lines.append("")

    if TARGET_CLASSIFICATION in df.columns:
        lines.append("RUL_FCA_BIN Distribution")
        lines.append("-" * 70)
        lines.append(str(df[TARGET_CLASSIFICATION].value_counts(dropna=False)))
        lines.append("")

    if "workpiece_slice_geometry" in df.columns and TARGET_REGRESSION in df.columns:
        lines.append("Average RUL by Workpiece Geometry")
        lines.append("-" * 70)
        lines.append(
            str(
                df.groupby("workpiece_slice_geometry")[TARGET_REGRESSION].agg(
                    ["count", "mean", "median", "min", "max"]
                )
            )
        )
        lines.append("")

    if "steel_type" in df.columns and TARGET_REGRESSION in df.columns:
        lines.append("Average RUL by Steel Type")
        lines.append("-" * 70)
        lines.append(
            str(
                df.groupby("steel_type")[TARGET_REGRESSION].agg(
                    ["count", "mean", "median", "min", "max"]
                )
            )
        )
        lines.append("")

    if "alloy_type" in df.columns and TARGET_REGRESSION in df.columns:
        lines.append("Average RUL by Alloy Type")
        lines.append("-" * 70)
        lines.append(
            str(
                df.groupby("alloy_type")[TARGET_REGRESSION].agg(
                    ["count", "mean", "median", "min", "max"]
                )
            )
        )
        lines.append("")

    if "sleeve" in df.columns and TARGET_REGRESSION in df.columns:
        lines.append("Sleeve-Level RUL Summary")
        lines.append("-" * 70)
        sleeve_summary = df.groupby("sleeve")[TARGET_REGRESSION].agg(
            ["count", "mean", "min", "max"]
        )
        lines.append(str(sleeve_summary.sort_values("mean").head(30)))
        lines.append("")

    if "num_stream" in df.columns and TARGET_REGRESSION in df.columns:
        lines.append("Average RUL by Stream")
        lines.append("-" * 70)
        lines.append(
            str(
                df.groupby("num_stream")[TARGET_REGRESSION].agg(
                    ["count", "mean", "median", "min", "max"]
                )
            )
        )
        lines.append("")

    if "num_crystallizer" in df.columns and TARGET_REGRESSION in df.columns:
        lines.append("Average RUL by Crystallizer")
        lines.append("-" * 70)
        lines.append(
            str(
                df.groupby("num_crystallizer")[TARGET_REGRESSION].agg(
                    ["count", "mean", "median", "min", "max"]
                )
            )
        )
        lines.append("")

    if TARGET_REGRESSION in df.columns and analysis_cols:
        corr_df = df[analysis_cols + [TARGET_REGRESSION]].copy()
        corr_df = corr_df.select_dtypes(include=[np.number])
        if TARGET_REGRESSION in corr_df.columns:
            corr = (
                corr_df.corr(numeric_only=True)[TARGET_REGRESSION]
                .drop(TARGET_REGRESSION, errors="ignore")
            )
            corr = corr.sort_values(key=lambda x: x.abs(), ascending=False).head(30)
            lines.append(
                "Top Numerical Correlations with RUL (tons)  "
                "[raw sensor/process columns only — no _BIN/_ENCODED, no RUL-derived]"
            )
            lines.append("-" * 70)
            lines.append(str(corr))
            lines.append("")

    lines.append("Interpretable First-Layer Knowledge  (V9)")
    lines.append("-" * 70)
    lines.append(
        "1.  calculated_RUL_tons can be modeled as a supervised regression "
        "target."
    )
    lines.append(
        "2.  RUL_Class can be modeled as a supervised classification target "
        "(ordinal health bins)."
    )
    lines.append(
        "3.  Cooling-circuit variables (water_consumption, water_temperature_delta) "
        "are key degradation indicators."
    )
    lines.append(
        "4.  Steel chemistry (steel_type, alloy_type) and processing parameters "
        "(alloy_speed, swing_frequency) provide degradation context."
    )
    lines.append(
        "5.  Sleeve, crystallizer, and stream identifiers support equipment-specific "
        "degradation analysis."
    )
    lines.append(
        "6.  _BIN columns enable association rule mining and formal concept-style "
        "knowledge extraction."
    )
    lines.append(
        "7.  Clustering can reveal process regimes with distinct average RUL values."
    )
    lines.append(
        "8.  Isolation Forest can detect abnormal casts linked to accelerated "
        "sleeve degradation."
    )
    lines.append(
        "9.  PCA exposes global separation between Healthy, Critical and transitional "
        "states."
    )
    lines.append(
        "10. Feature-importance and decision-tree rules convert predictive models "
        "into interpretable industrial knowledge."
    )
    lines.append(
        "11. (V9) All _BIN and _ENCODED columns are excluded from numeric analysis "
        "to avoid inflating correlations and PCA axes with derived/redundant signals."
    )
    lines.append(
        "12. (V9) StandardScaler is applied to all numeric features before "
        "distance-based analyses to give equal weight to each sensor dimension."
    )
    lines.append(
        "13. (V9 RUL leakage fix) Every column whose name contains 'rul' "
        "(case-insensitive) is excluded from supervised feature matrices and EDA "
        "correlation analyses.  This catches RUL_Class_ENCODED, RUL_percentage, "
        "and any future RUL-named columns added to the dataset."
    )
    lines.append("")
    lines.append("Leakage Warning")
    lines.append("-" * 70)
    lines.append(
        "RUL is derived from cumulative resistance.  Resistance-related columns "
        "(resistance, tonn; resistance, tonn_BIN; resistance, tonn_ENCODED) may "
        "dominate prediction and should be removed for a clean prognostic "
        "experiment (STRICT_NO_RESISTANCE = True)."
    )
    lines.append(
        "RUL_Class_ENCODED and RUL_percentage are always removed as leakage "
        "because they are direct transforms of the regression and classification "
        "targets."
    )
    lines.append(
        "All *_BIN and *_ENCODED columns are removed from supervised model "
        "feature matrices in V9 to prevent indirect leakage through encoded targets."
    )
    lines.append(
        "ALL columns containing 'rul' (case-insensitive) are removed from "
        "supervised feature matrices (RUL leakage fix).  Only the specific target "
        "column for the current task is retained."
    )
    lines.append("")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[RESULT] Knowledge report exported: {report_path}")

# ============================================================
# Main launcher
# ============================================================
if __name__ == "__main__":
    SCRIPT_DIR = Path(__file__).resolve().parent
    INPUT_FILE = SCRIPT_DIR / "Dataset2" / "Final_Processed_Steel_Data_Clean.csv"
    OUTPUT_DIR = SCRIPT_DIR / "Analysis_Outputs_Claude_V9"

    # Set True to remove resistance columns (RUL is derived from resistance):
    STRICT_NO_RESISTANCE = False

    create_output_dir(str(OUTPUT_DIR))
    create_plot_dir(str(OUTPUT_DIR))

    df = load_dataset(str(INPUT_FILE))
    df = basic_cleaning(df)

    generate_first_layer_knowledge_report(df, str(OUTPUT_DIR))
    generate_eda_plots(df, str(OUTPUT_DIR))

    if TARGET_REGRESSION in df.columns:
        run_rul_regression(
            df, str(OUTPUT_DIR), strict_no_resistance=STRICT_NO_RESISTANCE
        )
    else:
        print(
            f"[WARNING] '{TARGET_REGRESSION}' column not found. "
            "Skipping regression."
        )

    if TARGET_CLASSIFICATION in df.columns:
        run_rul_classification(
            df, str(OUTPUT_DIR), strict_no_resistance=STRICT_NO_RESISTANCE
        )
        run_decision_tree_rules(
            df, str(OUTPUT_DIR), strict_no_resistance=STRICT_NO_RESISTANCE
        )
    else:
        print(
            f"[WARNING] '{TARGET_CLASSIFICATION}' column not found. "
            "Skipping classification and rule extraction."
        )

    run_clustering(df, str(OUTPUT_DIR))
    run_pca(df, str(OUTPUT_DIR))
    run_anomaly_detection(df, str(OUTPUT_DIR))
    run_association_rule_mining(df, str(OUTPUT_DIR))

    print("\n[DONE] Knowledge Discovery pipeline completed.")
    print(f"[DONE] Input file : {INPUT_FILE}")
    print(f"[DONE] Results    : {OUTPUT_DIR}")
    print(f"[DONE] Plots      : {OUTPUT_DIR / 'plots'}")
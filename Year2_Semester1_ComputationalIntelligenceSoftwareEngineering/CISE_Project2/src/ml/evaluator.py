"""Model Evaluation module computing test metrics, confusion matrix, ROC/PR curves, and feature importances."""
from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Any, Dict, List, Optional, Tuple
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
    confusion_matrix,
    classification_report,
    roc_curve,
    precision_recall_curve,
)
from sklearn.inspection import permutation_importance
import plotly.express as px
import plotly.graph_objects as go
import plotly.figure_factory as ff

from src.utils.logger import setup_logger

logger = setup_logger("evaluator")


class ModelEvaluator:
    """Computes comprehensive evaluation metrics and visualization figures on held-out test data."""

    @staticmethod
    def evaluate(
        model: Any,
        X_test: pd.DataFrame,
        y_test: pd.Series,
    ) -> Dict[str, Any]:
        """Compute metrics on holdout test set."""
        y_pred = model.predict(X_test)
        has_proba = hasattr(model, "predict_proba")
        y_prob = model.predict_proba(X_test)[:, 1] if has_proba else None

        acc = float(accuracy_score(y_test, y_pred))
        prec = float(precision_score(y_test, y_pred, zero_division=0))
        rec = float(recall_score(y_test, y_pred, zero_division=0))
        f1 = float(f1_score(y_test, y_pred, zero_division=0))

        # Check if test set contains multiple classes
        has_multiple_classes = len(np.unique(y_test)) > 1

        roc_auc: Optional[float] = None
        pr_auc: Optional[float] = None

        if has_multiple_classes and y_prob is not None:
            try:
                roc_auc = float(roc_auc_score(y_test, y_prob))
                pr_auc = float(average_precision_score(y_test, y_prob))
            except Exception as e:
                logger.warning(f"Could not compute AUC: {e}")

        cm = confusion_matrix(y_test, y_pred).tolist()
        report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)

        # MDI Feature Importance
        feature_names = list(X_test.columns)
        mdi_importances: List[Dict[str, Any]] = []
        if hasattr(model, "feature_importances_"):
            for fname, imp in zip(feature_names, model.feature_importances_):
                mdi_importances.append({"feature": fname, "importance": float(imp)})
            mdi_importances.sort(key=lambda x: x["importance"], reverse=True)

        # Permutation Feature Importance (measured on held-out test data)
        perm_importances: List[Dict[str, Any]] = []
        try:
            perm_res = permutation_importance(model, X_test, y_test, n_repeats=5, random_state=42, n_jobs=-1)
            for fname, mean_imp, std_imp in zip(feature_names, perm_res.importances_mean, perm_res.importances_std):
                perm_importances.append({
                    "feature": fname,
                    "importance_mean": float(mean_imp),
                    "importance_std": float(std_imp),
                })
            perm_importances.sort(key=lambda x: x["importance_mean"], reverse=True)
        except Exception as e:
            logger.debug(f"Permutation importance skipped: {e}")

        results = {
            "accuracy": round(acc, 4),
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "roc_auc": round(roc_auc, 4) if roc_auc is not None else None,
            "average_precision": round(pr_auc, 4) if pr_auc is not None else None,
            "confusion_matrix": cm,
            "classification_report": report,
            "test_sample_count": len(y_test),
            "mdi_feature_importances": mdi_importances,
            "permutation_feature_importances": perm_importances,
        }

        logger.info(f"Test evaluation: Acc={acc:.3f}, Prec={prec:.3f}, Rec={rec:.3f}, F1={f1:.3f}, AUC={roc_auc}")
        return results

    @staticmethod
    def create_confusion_matrix_figure(cm: List[List[int]]) -> go.Figure:
        """Create a styled Plotly heatmap for the confusion matrix."""
        z = np.array(cm)
        x = ["Predicted Clean (0)", "Predicted Buggy (1)"]
        y = ["Actual Clean (0)", "Actual Buggy (1)"]

        fig = px.imshow(
            z,
            text_auto=True,
            x=x,
            y=y,
            color_continuous_scale="Blues",
            labels=dict(x="Predicted Label", y="Actual Label", color="Count"),
        )
        fig.update_layout(
            title_text="Confusion Matrix (Holdout Test Set)",
            xaxis_title="Predicted Label",
            yaxis_title="Actual Label",
        )
        return fig

    @staticmethod
    def create_roc_curve_figure(model: Any, X_test: pd.DataFrame, y_test: pd.Series) -> Optional[go.Figure]:
        """Generate Plotly ROC curve figure."""
        if len(np.unique(y_test)) < 2 or not hasattr(model, "predict_proba"):
            return None

        y_prob = model.predict_proba(X_test)[:, 1]
        fpr, tpr, _ = roc_curve(y_test, y_prob)
        auc_val = roc_auc_score(y_test, y_prob)

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=fpr, y=tpr, mode="lines", name=f"Random Forest (AUC = {auc_val:.3f})", line=dict(color="#2980b9", width=2)))
        fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", name="Random Guess (AUC = 0.5)", line=dict(color="grey", dash="dash")))

        fig.update_layout(
            title="Receiver Operating Characteristic (ROC) Curve",
            xaxis_title="False Positive Rate (1 - Specificity)",
            yaxis_title="True Positive Rate (Recall)",
            xaxis=dict(range=[0, 1]),
            yaxis=dict(range=[0, 1.05]),
        )
        return fig

    @staticmethod
    def create_pr_curve_figure(model: Any, X_test: pd.DataFrame, y_test: pd.Series) -> Optional[go.Figure]:
        """Generate Plotly Precision-Recall curve figure."""
        if len(np.unique(y_test)) < 2 or not hasattr(model, "predict_proba"):
            return None

        y_prob = model.predict_proba(X_test)[:, 1]
        precision, recall, _ = precision_recall_curve(y_test, y_prob)
        ap_val = average_precision_score(y_test, y_prob)

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=recall, y=precision, mode="lines", name=f"PR Curve (AP = {ap_val:.3f})", line=dict(color="#27ae60", width=2)))

        fig.update_layout(
            title="Precision-Recall Curve",
            xaxis_title="Recall",
            yaxis_title="Precision",
            xaxis=dict(range=[0, 1]),
            yaxis=dict(range=[0, 1.05]),
        )
        return fig

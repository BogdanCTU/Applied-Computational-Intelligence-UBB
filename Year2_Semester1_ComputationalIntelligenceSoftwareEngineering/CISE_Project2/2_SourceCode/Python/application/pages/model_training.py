"""Model Training Page with Repository-Aware GroupKFold Cross-Validation and Precision Tuning."""
from __future__ import annotations

import pandas as pd
import streamlit as st
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

from core.settings import AppSettings
from database.repository import RepositoryDB
from ml.cross_validation import (
    RepositoryGroupKFoldValidator,
    compute_binary_classification_metrics,
    select_classifier_threshold,
)
from ml.evaluator import ModelEvaluator
from ml.model_manager import ModelManager
from ml.preprocessing import DataPreprocessor, PreprocessingError, split_by_repository
from services.dataset.dataset_builder import DatasetBuilder


def render_model_training(db: RepositoryDB, settings: AppSettings) -> None:
    st.title("Model Training")
    st.caption(
        "Train class-level (or preserved method-level) defect detection models with strict repository "
        "separation, GroupKFold validation, and inner-CV precision threshold optimization."
    )

    datasets = db.list_datasets()
    if not datasets:
        st.warning("No datasets available. Create a dataset snapshot in Dataset Management first.")
        return

    builder = DatasetBuilder(db)
    model_mgr = ModelManager(settings.storage.models_dir, db=db)

    # 1. Dataset Selection
    st.subheader("Dataset Selection")
    ds_options = {
        f"#{d['id']}: {d['name']} (v{d['version']} | {d.get('granularity', 'method')} | {d['total_count']} items)": d
        for d in datasets
    }
    selected_ds_label = st.selectbox("Dataset snapshot", list(ds_options.keys()))
    selected_ds = ds_options[selected_ds_label]
    selected_ds_id = selected_ds["id"]
    ds_granularity = selected_ds.get("granularity", "method")
    ds_version = selected_ds.get("version", "1.0.0")

    stats = builder.compute_dataset_statistics(selected_ds_id, [])
    unit_label = "Classes" if ds_granularity == "class" else "Methods"
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(f"Total {unit_label}", stats.get("total_observations", 0))
    c2.metric("BUG (1)", stats.get("buggy_count", 0))
    c3.metric("CLEAN (0)", stats.get("clean_count", 0))
    c4.metric("Repositories", len(stats.get("repository_distribution", {})))

    # 2. Model Family & Hyperparameters
    st.subheader("Model Family & Hyperparameters")
    col1, col2, col3 = st.columns(3)
    with col1:
        algo_choice = st.selectbox(
            "Model family",
            [
                "RandomForestClassifier",
                "ExtraTreesClassifier",
                "HistGradientBoostingClassifier",
                "LogisticRegression",
                "DecisionTreeClassifier",
                "CalibratedRandomForest",
            ],
        )
        class_weight_opt = st.selectbox("Class weighting", ["balanced_subsample", "balanced", "None"])
        class_weight = None if class_weight_opt == "None" else class_weight_opt
    with col2:
        n_estimators = st.slider("Estimators (n_estimators / max_iter)", 50, 400, 200, 25)
        max_depth = st.slider("Max depth (0 = None)", 0, 25, 10, 1)
        max_depth_val = None if max_depth == 0 else max_depth
    with col3:
        min_samples_leaf = st.slider("Min samples leaf", 1, 25, 4, 1)
        max_features = st.selectbox("Max features", ["log2", "sqrt"])
        random_state = st.number_input("Random seed", value=42, step=1)

    # 3. Validation & Precision Optimization
    st.subheader("Validation & Precision Threshold Optimization")
    col_v1, col_v2, col_v3, col_v4 = st.columns(4)
    with col_v1:
        test_size = st.slider("Holdout repository ratio", 0.15, 0.35, 0.20, 0.05)
    with col_v2:
        n_splits = st.slider("GroupKFold folds", 2, 10, 5, 1)
    with col_v3:
        optimize_precision = st.checkbox("Optimize threshold on CV OOF for Precision", value=True)
    with col_v4:
        model_save_name = st.text_input("Model identifier", value=f"{algo_choice[:3].lower()}_{ds_granularity}_v{selected_ds_id}")

    if st.button("Train and Validate Model", width="stretch"):
        with st.spinner("Partitioning repositories, running GroupKFold CV, and evaluating holdout..."):
            try:
                X, y, metadata = builder.get_features_and_labels(selected_ds_id)
                X_train, X_test, y_train, y_test, meta_train, meta_test, split_sum = split_by_repository(
                    X, y, metadata, test_size=test_size, random_state=int(random_state)
                )

                needs_scaling = algo_choice == "LogisticRegression"

                def make_est():
                    cw = "balanced" if (class_weight == "balanced_subsample" and algo_choice != "RandomForestClassifier") else class_weight
                    if algo_choice == "RandomForestClassifier":
                        return RandomForestClassifier(
                            n_estimators=n_estimators, max_depth=max_depth_val,
                            min_samples_leaf=min_samples_leaf, max_features=max_features,
                            class_weight=class_weight, random_state=int(random_state), n_jobs=-1,
                        )
                    if algo_choice == "ExtraTreesClassifier":
                        return ExtraTreesClassifier(
                            n_estimators=n_estimators, max_depth=max_depth_val,
                            min_samples_leaf=min_samples_leaf, max_features=max_features,
                            class_weight=cw, random_state=int(random_state), n_jobs=-1,
                        )
                    if algo_choice == "HistGradientBoostingClassifier":
                        return HistGradientBoostingClassifier(
                            max_iter=n_estimators, max_depth=max_depth_val,
                            min_samples_leaf=max(10, min_samples_leaf), l2_regularization=2.0,
                            class_weight=cw, random_state=int(random_state),
                        )
                    if algo_choice == "LogisticRegression":
                        return LogisticRegression(C=0.1, max_iter=1000, class_weight=cw, random_state=int(random_state))
                    if algo_choice == "DecisionTreeClassifier":
                        return DecisionTreeClassifier(
                            max_depth=max_depth_val, min_samples_leaf=min_samples_leaf,
                            class_weight=cw, random_state=int(random_state),
                        )
                    base = RandomForestClassifier(
                        n_estimators=n_estimators, max_depth=max_depth_val,
                        min_samples_leaf=min_samples_leaf, max_features=max_features,
                        class_weight=class_weight, random_state=int(random_state), n_jobs=-1,
                    )
                    return CalibratedClassifierCV(estimator=base, method="sigmoid", cv=3)

                validator = RepositoryGroupKFoldValidator(
                    n_splits=min(n_splits, int(meta_train["repository_id"].nunique())),
                    strict_repo_count=False,
                )
                cv_res = validator.evaluate_model(
                    model_factory=make_est,
                    X_train_raw=X_train,
                    y_train=y_train,
                    meta_train=meta_train,
                    needs_scaling=needs_scaling,
                )

                decision_threshold = 0.50
                criterion = "nominal_0.50"
                if optimize_precision and cv_res.oof_predictions:
                    t_res = select_classifier_threshold(
                        cv_res.oof_predictions["y_true"],
                        cv_res.oof_predictions["y_prob"],
                        min_precision_target=settings.ml.preferred_precision_target,
                        min_precision_floor=settings.ml.min_precision_target,
                        min_recall=settings.ml.min_recall_floor,
                    )
                    decision_threshold = float(t_res["selected_threshold"])
                    criterion = t_res["criterion"]

                preprocessor = DataPreprocessor(impute_missing=True, remove_constant=True)
                X_train_proc = preprocessor.fit_transform(X_train)
                X_test_proc = preprocessor.transform(X_test)

                est = make_est()
                final_model = Pipeline([("scaler", StandardScaler()), ("classifier", est)]) if needs_scaling else est
                final_model.fit(X_train_proc, y_train)

                eval_results = ModelEvaluator.evaluate(final_model, X_test_proc, y_test)
                probs_ho = final_model.predict_proba(X_test_proc)[:, 1]
                ho_thresh_metrics = compute_binary_classification_metrics(y_test.values, probs_ho, threshold=decision_threshold)
                eval_results.update({
                    "precision": ho_thresh_metrics["precision"],
                    "recall": ho_thresh_metrics["recall"],
                    "f1": ho_thresh_metrics["f1"],
                    "accuracy": ho_thresh_metrics["accuracy"],
                    "confusion_matrix": ho_thresh_metrics["confusion_matrix"],
                    "brier_score": ho_thresh_metrics["brier_score"],
                    "decision_threshold": decision_threshold,
                })

                params_dict = {
                    "algorithm": algo_choice,
                    "n_estimators": n_estimators,
                    "max_depth": max_depth_val,
                    "min_samples_leaf": min_samples_leaf,
                    "max_features": max_features,
                    "class_weight": class_weight,
                    "random_state": int(random_state),
                }

                saved_path = model_mgr.save_model(
                    model_name=model_save_name,
                    model=final_model,
                    preprocessor=preprocessor,
                    feature_names=preprocessor.feature_names_out_,
                    parameters=params_dict,
                    metrics=eval_results,
                    dataset_id=selected_ds_id,
                    split_summary=split_sum,
                    overwrite=True,
                    granularity=ds_granularity,
                    version=ds_version,
                    dataset_version=ds_version,
                    decision_threshold=decision_threshold,
                    threshold_selection_criterion=criterion,
                )

                st.subheader("Training and Holdout Results")
                st.caption(
                    f"Saved to `{saved_path}` | Threshold: `{decision_threshold:.2f}` ({criterion}) | "
                    f"Train: {split_sum['train_repo_count']} repos ({split_sum['train_samples']} {unit_label.lower()}); "
                    f"Holdout: {split_sum['test_repo_count']} repos ({split_sum['test_samples']} {unit_label.lower()})."
                )
                results_df = pd.DataFrame([
                    {
                        "Partition": "GroupKFold CV (Nominal 0.50)",
                        "Precision": f"{cv_res.aggregate_metrics['precision']['mean']:.3f} ± {cv_res.aggregate_metrics['precision']['std']:.3f}",
                        "Recall": f"{cv_res.aggregate_metrics['recall']['mean']:.3f} ± {cv_res.aggregate_metrics['recall']['std']:.3f}",
                        "F1-Score": f"{cv_res.aggregate_metrics['f1']['mean']:.3f} ± {cv_res.aggregate_metrics['f1']['std']:.3f}",
                        "ROC-AUC": f"{cv_res.aggregate_metrics['roc_auc']['mean']:.3f} ± {cv_res.aggregate_metrics['roc_auc']['std']:.3f}",
                    },
                    {
                        "Partition": f"Held-Out Repositories (tau={decision_threshold:.2f})",
                        "Precision": f"{eval_results['precision']:.3f}",
                        "Recall": f"{eval_results['recall']:.3f}",
                        "F1-Score": f"{eval_results['f1']:.3f}",
                        "ROC-AUC": f"{eval_results.get('roc_auc', 0.0):.3f}",
                    },
                ])
                st.table(results_df)
            except PreprocessingError as pe:
                st.error(f"Preprocessing or splitting error: {pe}")
            except Exception as e:
                st.error(f"Training failed: {e}")

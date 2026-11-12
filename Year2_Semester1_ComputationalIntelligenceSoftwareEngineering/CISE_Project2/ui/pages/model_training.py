"""Model Training Page with Repository-Aware GroupKFold Cross-Validation and Baseline Comparison."""
from __future__ import annotations

import json
import pandas as pd
import streamlit as st

from config.settings import AppSettings
from src.database.repository import RepositoryDB
from src.dataset.dataset_builder import DatasetBuilder
from src.ml.preprocessing import DataPreprocessor, split_by_repository, PreprocessingError
from src.ml.trainer import ModelTrainer
from src.ml.evaluator import ModelEvaluator
from src.ml.model_manager import ModelManager


def render_model_training(db: RepositoryDB, settings: AppSettings) -> None:
    st.header("🧠 Machine Learning Model Training: Random Forest Classifier")
    st.markdown("""
    Train a Supervised Random Forest Classifier to predict method defect proneness.
    To prevent data leakage, training uses **Repository-Aware Partitioning**: code from the same repository
    never appears in both training and test sets.
    """)

    datasets = db.list_datasets()
    if not datasets:
        st.warning("No datasets available. Please generate a dataset snapshot in 'Dataset Management' first.")
        return

    builder = DatasetBuilder(db)
    model_mgr = ModelManager(settings.storage.models_dir, db=db)

    # 1. Dataset Selection
    st.subheader("1. Select Training Dataset Snapshot")
    ds_options = {f"#{d['id']}: {d['name']} (v{d['version']} — {d['total_count']} items)": d["id"] for d in datasets}
    selected_ds_name = st.selectbox("Dataset Snapshot", list(ds_options.keys()))
    selected_ds_id = ds_options[selected_ds_name]

    # Show dataset info
    stats = builder.compute_dataset_statistics(selected_ds_id, [])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Methods", stats.get("total_observations", 0))
    c2.metric("Buggy Methods (1)", stats.get("buggy_count", 0))
    c3.metric("Candidate Clean (0)", stats.get("clean_count", 0))
    c4.metric("Repositories", len(stats.get("repository_distribution", {})))

    st.markdown("---")

    # 2. Hyperparameters
    st.subheader("2. Configure Random Forest Hyperparameters")
    col1, col2, col3 = st.columns(3)
    with col1:
        n_estimators = st.slider("Number of Trees (n_estimators)", 10, 300, 100, 10)
        max_depth = st.slider("Max Tree Depth (0 = None)", 0, 30, 15, 1)
        max_depth_val = None if max_depth == 0 else max_depth
    with col2:
        min_samples_split = st.slider("Min Samples Split", 2, 20, 5, 1)
        min_samples_leaf = st.slider("Min Samples Leaf", 1, 10, 2, 1)
    with col3:
        class_weight_opt = st.selectbox("Class Weighting", ["balanced", "None"])
        class_weight = "balanced" if class_weight_opt == "balanced" else None
        random_state = st.number_input("Deterministic Random Seed", value=42, step=1)

    st.markdown("---")

    # 3. Validation Strategy
    st.subheader("3. Repository-Aware Holdout & Cross-Validation")
    col_v1, col_v2 = st.columns(2)
    with col_v1:
        test_size = st.slider("Holdout Test Repository Ratio", 0.15, 0.40, 0.25, 0.05, help="Proportion of entire repositories held out for final testing.")
    with col_v2:
        n_splits = st.slider("GroupKFold CV Folds (on Training data)", 2, 10, 5, 1)

    model_save_name = st.text_input("Model Version Identifier", value=f"rf_csharp_v{selected_ds_id}")

    # 4. Train Action
    if st.button("🚀 Train Model with GroupKFold", use_container_width=True):
        with st.spinner("Loading dataset and performing repository-aware splitting..."):
            try:
                # 1. Load data
                X, y, metadata = builder.get_features_and_labels(selected_ds_id)

                # 2. Repository-aware split
                X_train, X_test, y_train, y_test, meta_train, meta_test, split_sum = split_by_repository(
                    X, y, metadata, test_size=test_size, random_state=random_state
                )

                st.info(
                    f"**Repository Partition:** Training on {split_sum['train_repo_count']} repositories ({split_sum['train_samples']} methods). "
                    f"Holding out {split_sum['test_repo_count']} repositories ({split_sum['test_samples']} methods) for final evaluation."
                )

                # 3. Fit Preprocessor strictly on training data
                preprocessor = DataPreprocessor(impute_missing=True, remove_constant=True)
                X_train_proc = preprocessor.fit_transform(X_train)
                X_test_proc = preprocessor.transform(X_test)

                # 4. Train with GroupKFold CV and Dummy Baseline
                trainer = ModelTrainer(
                    n_estimators=n_estimators,
                    max_depth=max_depth_val,
                    min_samples_split=min_samples_split,
                    min_samples_leaf=min_samples_leaf,
                    class_weight=class_weight,
                    random_state=random_state,
                )
                model, cv_results, baseline_results, duration = trainer.train_with_cv(
                    X_train=X_train_proc,
                    y_train=y_train,
                    meta_train=meta_train,
                    n_splits=n_splits,
                )

                # 5. Evaluate on untouched Holdout Test Set
                eval_results = ModelEvaluator.evaluate(model, X_test_proc, y_test)

                # 6. Save model bundle
                saved_path = model_mgr.save_model(
                    model_name=model_save_name,
                    model=model,
                    preprocessor=preprocessor,
                    feature_names=preprocessor.feature_names_out_,
                    parameters=trainer.params,
                    metrics=eval_results,
                    dataset_id=selected_ds_id,
                    split_summary=split_sum,
                    overwrite=True,
                )

                st.success(f"Model trained and saved successfully in {duration}s to `{saved_path}`!")

                # Display Results comparison
                st.markdown("### Training & Validation Summary")
                res_col1, res_col2 = st.columns(2)
                with res_col1:
                    st.markdown("**Cross-Validation Performance (Training Repositories):**")
                    st.write(f"- **Mean F1-Score:** `{cv_results['f1']['mean']:.3f} +/- {cv_results['f1']['std']:.3f}`")
                    st.write(f"- **Mean Accuracy:** `{cv_results['accuracy']['mean']:.3f} +/- {cv_results['accuracy']['std']:.3f}`")
                    st.write(f"- **Mean ROC-AUC:** `{cv_results['roc_auc']['mean']:.3f} +/- {cv_results['roc_auc']['std']:.3f}`")
                    st.caption("Fitted only on train folds; test repositories remained untouched.")
                with res_col2:
                    st.markdown("**Baseline Comparison (DummyClassifier):**")
                    st.write(f"- **Baseline F1-Score:** `{baseline_results['f1']['mean']:.3f}`")
                    st.write(f"- **Baseline Accuracy:** `{baseline_results['accuracy']['mean']:.3f}`")
                    st.markdown("**Holdout Test Set Performance:**")
                    st.write(f"- **Test F1-Score:** `{eval_results['f1']:.3f}`")
                    st.write(f"- **Test Accuracy:** `{eval_results['accuracy']:.3f}`")

                st.info("Head to the **📈 Model Evaluation** page for detailed confusion matrices, ROC/PR curves, and feature importance analysis!")

            except PreprocessingError as pe:
                st.error(f"Preprocessing / Splitting Error: {pe}")
            except Exception as e:
                st.error(f"Training failed: {e}")

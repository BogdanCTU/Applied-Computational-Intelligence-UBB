"""Model Training Page with Repository-Aware GroupKFold Cross-Validation."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from core.settings import AppSettings
from database.repository import RepositoryDB
from services.dataset.dataset_builder import DatasetBuilder
from ml.preprocessing import DataPreprocessor, split_by_repository, PreprocessingError
from ml.trainer import ModelTrainer
from ml.evaluator import ModelEvaluator
from ml.model_manager import ModelManager


def render_model_training(db: RepositoryDB, settings: AppSettings) -> None:
    st.title("Model Training")
    st.caption("Train a Random Forest classifier using repository-level GroupKFold cross-validation.")

    datasets = db.list_datasets()
    if not datasets:
        st.warning("No datasets available. Create a dataset snapshot in Dataset Management first.")
        return

    builder = DatasetBuilder(db)
    model_mgr = ModelManager(settings.storage.models_dir, db=db)

    # 1. Dataset Selection
    st.subheader("Dataset Selection")
    ds_options = {f"#{d['id']}: {d['name']} (v{d['version']} - {d['total_count']} items)": d["id"] for d in datasets}
    selected_ds_name = st.selectbox("Dataset snapshot", list(ds_options.keys()))
    selected_ds_id = ds_options[selected_ds_name]

    stats = builder.compute_dataset_statistics(selected_ds_id, [])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Methods", stats.get("total_observations", 0))
    c2.metric("Defect-Prone (1)", stats.get("buggy_count", 0))
    c3.metric("Candidate-Clean (0)", stats.get("clean_count", 0))
    c4.metric("Repositories", len(stats.get("repository_distribution", {})))

    # 2. Hyperparameters
    st.subheader("Random Forest Hyperparameters")
    col1, col2, col3 = st.columns(3)
    with col1:
        n_estimators = st.slider("Estimators (n_estimators)", 10, 300, 100, 10)
        max_depth = st.slider("Max depth (0 = None)", 0, 30, 15, 1)
        max_depth_val = None if max_depth == 0 else max_depth
    with col2:
        min_samples_split = st.slider("Min samples split", 2, 20, 5, 1)
        min_samples_leaf = st.slider("Min samples leaf", 1, 10, 2, 1)
    with col3:
        class_weight_opt = st.selectbox("Class weighting", ["balanced", "None"])
        class_weight = "balanced" if class_weight_opt == "balanced" else None
        random_state = st.number_input("Random seed", value=42, step=1)

    # 3. Validation Strategy
    st.subheader("Validation Partitioning")
    col_v1, col_v2, col_v3 = st.columns(3)
    with col_v1:
        test_size = st.slider("Holdout repository ratio", 0.15, 0.40, 0.25, 0.05)
    with col_v2:
        n_splits = st.slider("GroupKFold folds", 2, 10, 5, 1)
    with col_v3:
        model_save_name = st.text_input("Model identifier", value=f"rf_csharp_v{selected_ds_id}")

    # 4. Train Action
    if st.button("Train Model", width="stretch"):
        with st.spinner("Splitting by repository and training model..."):
            try:
                X, y, metadata = builder.get_features_and_labels(selected_ds_id)

                X_train, X_test, y_train, y_test, meta_train, meta_test, split_sum = split_by_repository(
                    X, y, metadata, test_size=test_size, random_state=random_state
                )

                preprocessor = DataPreprocessor(impute_missing=True, remove_constant=True)
                X_train_proc = preprocessor.fit_transform(X_train)
                X_test_proc = preprocessor.transform(X_test)

                trainer = ModelTrainer(
                    n_estimators=n_estimators,
                    max_depth=max_depth_val,
                    min_samples_split=min_samples_split,
                    min_samples_leaf=min_samples_leaf,
                    class_weight=class_weight,
                    random_state=random_state,
                )
                model, cv_results, _, duration = trainer.train_with_cv(
                    X_train=X_train_proc,
                    y_train=y_train,
                    meta_train=meta_train,
                    n_splits=n_splits,
                )

                eval_results = ModelEvaluator.evaluate(model, X_test_proc, y_test)

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

                st.subheader("Training and Validation Results")
                st.caption(
                    f"Saved to `{saved_path}` ({duration}s). "
                    f"Training: {split_sum['train_repo_count']} repositories ({split_sum['train_samples']} methods); "
                    f"Holdout: {split_sum['test_repo_count']} repositories ({split_sum['test_samples']} methods)."
                )

                test_roc = eval_results.get("roc_auc")
                results_df = pd.DataFrame([
                    {
                        "Partition": "GroupKFold Cross-Validation (Train)",
                        "Accuracy": f"{cv_results['accuracy']['mean']:.3f} ± {cv_results['accuracy']['std']:.3f}",
                        "F1-Score": f"{cv_results['f1']['mean']:.3f} ± {cv_results['f1']['std']:.3f}",
                        "ROC-AUC": f"{cv_results['roc_auc']['mean']:.3f} ± {cv_results['roc_auc']['std']:.3f}",
                    },
                    {
                        "Partition": "Held-Out Repositories (Test)",
                        "Accuracy": f"{eval_results['accuracy']:.3f}",
                        "F1-Score": f"{eval_results['f1']:.3f}",
                        "ROC-AUC": f"{test_roc:.3f}" if test_roc is not None else "N/A",
                    },
                ])
                st.table(results_df)

            except PreprocessingError as pe:
                st.error(f"Preprocessing or splitting error: {pe}")
            except Exception as e:
                st.error(f"Training failed: {e}")

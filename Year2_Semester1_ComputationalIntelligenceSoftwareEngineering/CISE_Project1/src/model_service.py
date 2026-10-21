"""Model service layer coordinating dataset caching, model training, inference,
and configuration state for both CLI and GUI interfaces.
"""

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import time
from typing import Any, Callable, Dict, List, Optional, Tuple


import pandas as pd
import numpy as np
from pgmpy.models import DiscreteBayesianNetwork

from src import config
from src.execution_log import ExecutionLogger, global_logger
from src.preprocessing import BankPreprocessor, split_data
from src.evaluation import compute_metrics, report_text
import bayesian_network
import branch_counter
import data_loader
import rule_based


@dataclass
class ModelConfig:
    """Safe, user-configurable model parameters."""
    test_size: float = config.TEST_SIZE
    random_seed: int = config.RANDOM_SEED
    max_indegree: int = config.MAX_INDEGREE
    scoring_method: str = "bic-d"
    equivalent_sample_size: int = config.BDEU_EQUIVALENT_SAMPLE_SIZE
    n_bins_age: int = config.N_BINS["age"]
    n_bins_balance: int = config.N_BINS["balance"]
    n_bins_day: int = config.N_BINS["day"]
    n_bins_campaign: int = config.N_BINS["campaign"]

    def to_n_bins_dict(self) -> dict[str, int]:
        d = dict(config.N_BINS)
        d["age"] = self.n_bins_age
        d["balance"] = self.n_bins_balance
        d["day"] = self.n_bins_day
        d["campaign"] = self.n_bins_campaign
        return d

    def get_signature(self) -> str:
        """Deterministic hash signature for cache invalidation."""
        rep = json.dumps({
            "test_size": self.test_size,
            "random_seed": self.random_seed,
            "max_indegree": self.max_indegree,
            "scoring_method": self.scoring_method,
            "equivalent_sample_size": self.equivalent_sample_size,
            "bins": self.to_n_bins_dict()
        }, sort_keys=True)
        return hashlib.md5(rep.encode()).hexdigest()


@dataclass
class TrainedArtifacts:
    """Holds fitted models, test datasets, and evaluation metrics."""
    config: ModelConfig
    signature: str
    model: DiscreteBayesianNetwork
    preprocessor: BankPreprocessor
    edges: List[Tuple[str, str]]
    X_train: pd.DataFrame
    X_test: pd.DataFrame
    y_train: pd.Series
    y_test: pd.Series
    bn_predictions: pd.Series
    bn_proba_yes: pd.Series
    bn_metrics: Dict[str, Any]
    rule_predictions: pd.Series
    rule_metrics: Dict[str, Any]
    baseline_metrics: Dict[str, Any]
    training_duration: float
    stage_durations: Dict[str, float]
    timestamp: float = field(default_factory=time.time)


class ModelService:
    """Service handling dataset loading, training execution, inference, and state."""

    def __init__(self, logger: Optional[ExecutionLogger] = None):
        self.logger = logger or global_logger
        self._raw_dataset: Optional[pd.DataFrame] = None
        self._artifacts: Optional[TrainedArtifacts] = None
        self._cv_results: Optional[Any] = None

    def get_raw_dataset(self, force_reload: bool = False) -> pd.DataFrame:
        """Loads and caches the raw Bank Marketing dataset."""
        if self._raw_dataset is None or force_reload:
            self.logger.info("DATA", "Loading dataset from disk or UCI repository...")
            self._raw_dataset = data_loader.load_dataset()
            self.logger.success(
                "DATA",
                f"Dataset loaded successfully: {len(self._raw_dataset):,} rows, {self._raw_dataset.shape[1]} columns."
            )
        return self._raw_dataset

    def is_trained(self, current_config: Optional[ModelConfig] = None) -> bool:
        """Checks if a trained model exists and matches the provided configuration."""
        if self._artifacts is None:
            return False
        if current_config is not None:
            return self._artifacts.signature == current_config.get_signature()
        return True

    def get_artifacts(self) -> Optional[TrainedArtifacts]:
        return self._artifacts

    def invalidate_model(self, reason: str = "Configuration changed") -> None:
        """Invalidates stale trained artifacts when parameters change."""
        if self._artifacts is not None:
            self._artifacts = None
            self.logger.warning("MODEL", f"Previous model invalidated: {reason}. Retraining required.")

    def train_models(
        self,
        cfg: ModelConfig,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> TrainedArtifacts:
        """Executes full training and evaluation with explicit progress reporting.

        Stages:
        1. Loading dataset
        2. Splitting data
        3. Preprocessing & discretization
        4. Structure learning (Bayesian Network DAG)
        5. Parameter estimation (CPTs with BDeu prior)
        6. Validating model
        7. Evaluating Bayesian Network on held-out test set
        8. Evaluating Rule-Based classifier on the exact same test set
        """
        total_start = time.time()
        stage_durations: Dict[str, float] = {}

        def update(stage_name: str, frac: float):
            if progress_callback:
                progress_callback(stage_name, frac)

        # Stage 1: Load Data
        s_time = time.time()
        update("Stage 1/8: Loading dataset...", 0.10)
        df = self.get_raw_dataset()
        stage_durations["load_data"] = time.time() - s_time

        # Stage 2: Data Splitting
        s_time = time.time()
        update("Stage 2/8: Splitting train and test sets...", 0.20)
        self.logger.info("SPLIT", f"Splitting data: test_size={cfg.test_size}, random_seed={cfg.random_seed} (stratified).")
        X_train, X_test, y_train, y_test = split_data(
            df, test_size=cfg.test_size, seed=cfg.random_seed
        )
        self.logger.success("SPLIT", f"Training set: {len(X_train):,} rows. Held-out test set: {len(X_test):,} rows.")
        stage_durations["split"] = time.time() - s_time

        # Stage 3: Preprocessing
        s_time = time.time()
        update("Stage 3/8: Discretizing numeric features & fitting categories...", 0.35)
        self.logger.info("PREPROCESSING", "Fitting preprocessor on training data only (quantile binning).")
        preprocessor = BankPreprocessor(n_bins=cfg.to_n_bins_dict()).fit(X_train)
        P_train = preprocessor.transform(X_train)
        P_test = preprocessor.transform(X_test)
        self.logger.success(
            "PREPROCESSING",
            f"Numerical features discretized into quantile bins. Unseen test categories replaced: {preprocessor.n_unseen_replaced_}."
        )
        stage_durations["preprocessing"] = time.time() - s_time

        # Stage 4: Structure Learning
        s_time = time.time()
        update("Stage 4/8: Learning Bayesian Network DAG structure (Hill Climb Search + BIC)...", 0.50)
        self.logger.info("STRUCTURE", f"Learning structure with HillClimbSearch, score={cfg.scoring_method}, max_indegree={cfg.max_indegree}...")
        train_table = P_train.assign(**{config.TARGET: y_train})
        edges = bayesian_network.learn_structure(
            train_table, max_indegree=cfg.max_indegree, scoring_method=cfg.scoring_method
        )
        self.logger.success("STRUCTURE", f"Network structure learned: {len(edges)} directed edges found across {len(train_table.columns)} nodes.")
        stage_durations["structure_learning"] = time.time() - s_time

        # Stage 5: Parameter Estimation
        s_time = time.time()
        update("Stage 5/8: Estimating Conditional Probability Tables (CPTs)...", 0.65)
        self.logger.info("PARAMETERS", f"Estimating CPTs using DiscreteBayesianEstimator (BDeu prior, sample_size={cfg.equivalent_sample_size})...")
        state_names = {c: preprocessor.states(c) for c in config.FEATURES}
        state_names[config.TARGET] = config.LABELS
        model = bayesian_network.build_network(edges, list(train_table.columns))
        bayesian_network.fit_parameters(
            model, train_table, state_names=state_names, equivalent_sample_size=cfg.equivalent_sample_size
        )
        self.logger.success("PARAMETERS", "All CPTs successfully estimated with smoothing pseudo-counts.")
        stage_durations["parameter_estimation"] = time.time() - s_time

        # Stage 6: Validation
        s_time = time.time()
        update("Stage 6/8: Validating probabilistic model...", 0.75)
        if not model.check_model():
            err_msg = "Bayesian Network model validation failed (invalid probability distributions)."
            self.logger.error("MODEL", err_msg)
            raise RuntimeError(err_msg)
        self.logger.success("MODEL", "Model validation passed: DAG is acyclic and all CPTs sum to 1.0.")
        stage_durations["validation"] = time.time() - s_time

        # Stage 7: Bayesian Network Inference & Evaluation
        s_time = time.time()
        update("Stage 7/8: Performing exact inference (Variable Elimination) on test set...", 0.85)
        self.logger.info("INFERENCE", f"Running Variable Elimination inference on {len(P_test):,} test instances...")
        bn_output = bayesian_network.predict(model, P_test)
        bn_pred = bn_output["prediction"]
        bn_proba_yes = bn_output["proba_yes"]
        bn_metrics = compute_metrics(y_test, bn_pred)
        self.logger.success(
            "EVALUATION",
            f"Bayesian Network test evaluation complete: Accuracy={bn_metrics['accuracy']:.4f}, Precision={bn_metrics['precision']:.4f}, Recall={bn_metrics['recall']:.4f}, F1={bn_metrics['f1']:.4f}."
        )
        stage_durations["bn_evaluation"] = time.time() - s_time

        # Stage 8: Rule-Based Classifier Evaluation
        s_time = time.time()
        update("Stage 8/8: Evaluating Rule-Based classifier on the exact same test set...", 0.95)
        self.logger.info("RULES", "Evaluating explicit branching logic on raw test records...")
        rule_pred = rule_based.predict_rules(X_test)
        rule_metrics = compute_metrics(y_test, rule_pred)
        self.logger.success(
            "RULES",
            f"Rule-Based test evaluation complete: Accuracy={rule_metrics['accuracy']:.4f}, Precision={rule_metrics['precision']:.4f}, Recall={rule_metrics['recall']:.4f}, F1={rule_metrics['f1']:.4f}."
        )

        baseline_pred = pd.Series(config.NEGATIVE_LABEL, index=y_test.index)
        baseline_metrics = compute_metrics(y_test, baseline_pred)
        stage_durations["rule_evaluation"] = time.time() - s_time

        total_duration = time.time() - total_start
        update("Training complete!", 1.0)

        artifacts = TrainedArtifacts(
            config=cfg,
            signature=cfg.get_signature(),
            model=model,
            preprocessor=preprocessor,
            edges=edges,
            X_train=X_train,
            X_test=X_test,
            y_train=y_train,
            y_test=y_test,
            bn_predictions=bn_pred,
            bn_proba_yes=bn_proba_yes,
            bn_metrics=bn_metrics,
            rule_predictions=rule_pred,
            rule_metrics=rule_metrics,
            baseline_metrics=baseline_metrics,
            training_duration=total_duration,
            stage_durations=stage_durations,
        )
        self._artifacts = artifacts
        return artifacts

    def predict_single_bn(
        self,
        raw_record: Dict[str, Any],
        artifacts: Optional[TrainedArtifacts] = None
    ) -> Dict[str, Any]:
        """Perform exact inference for a single input record using the Bayesian Network."""
        art = artifacts or self._artifacts
        if art is None:
            raise RuntimeError("Bayesian Network has not been trained yet. Retraining required.")

        record_df = pd.DataFrame([raw_record])
        P_record = art.preprocessor.transform(record_df)
        evidence = P_record.iloc[0].to_dict()

        # Keep evidence for nodes actually present in the network
        valid_evidence = {k: v for k, v in evidence.items() if k in art.model.nodes()}

        from pgmpy.inference import VariableElimination
        infer = VariableElimination(art.model)
        query_result = infer.query([config.TARGET], evidence=valid_evidence, show_progress=False)

        state_names = query_result.state_names[config.TARGET]
        pos_idx = state_names.index(config.POSITIVE_LABEL)
        neg_idx = state_names.index(config.NEGATIVE_LABEL)

        p_yes = float(query_result.values[pos_idx])
        p_no = float(query_result.values[neg_idx])

        prediction = config.POSITIVE_LABEL if p_yes >= 0.5 else config.NEGATIVE_LABEL

        self.logger.info(
            "INFERENCE",
            f"BN single-instance query: P(yes|evidence)={p_yes:.4f}, predicted={prediction}."
        )

        return {
            "prediction": prediction,
            "probabilities": {config.POSITIVE_LABEL: p_yes, config.NEGATIVE_LABEL: p_no},
            "p_yes": p_yes,
            "p_no": p_no,
            "evidence": valid_evidence,
            "discretized_record": evidence,
            "markov_blanket": sorted(art.model.get_markov_blanket(config.TARGET)),
            "disclaimer": "Posterior probability is computed conditional on the model structure and prior assumptions. It reflects model-based statistical belief, not an empirical guarantee."
        }

    def predict_single_rule_based(self, raw_record: Dict[str, Any]) -> Dict[str, Any]:
        """Classify a single record with the Rule-Based classifier, returning a step-by-step trace."""
        self.logger.info("CLASSIFICATION", f"Rule-based input received: poutcome='{raw_record.get('poutcome')}', month='{raw_record.get('month')}'.")
        trace: List[Dict[str, Any]] = []

        # Step 1: Input reading
        trace.append({
            "step": 1,
            "action": "Read supplied input attributes",
            "attributes": {
                "poutcome": raw_record.get("poutcome"),
                "month": raw_record.get("month")
            }
        })

        # Step 2: Evaluate Rule 1
        cond1_eval = raw_record.get("poutcome") == "success"
        trace.append({
            "step": 2,
            "rule": "Rule 1",
            "condition": "poutcome == 'success'",
            "evaluated_value": raw_record.get("poutcome"),
            "result": cond1_eval,
            "action": "Predict 'yes'" if cond1_eval else "Proceed to next rule"
        })

        if cond1_eval:
            self.logger.success("CLASSIFICATION", "Rule 1 matched: poutcome == 'success' -> predicted 'yes'.")
            return {
                "prediction": "yes",
                "matched_rule_id": "RULE_1",
                "matched_rule_title": "Rule 1: Previous Campaign Success",
                "explanation": "Client's previous marketing campaign was successful. Training data showed a 64.6% subscription rate under this condition.",
                "trace": trace,
            }

        # Step 3: Evaluate Rule 2
        high_months = rule_based.HIGH_SUCCESS_MONTHS
        cond2_eval = raw_record.get("month") in high_months
        trace.append({
            "step": 3,
            "rule": "Rule 2",
            "condition": f"month in {high_months}",
            "evaluated_value": raw_record.get("month"),
            "result": cond2_eval,
            "action": "Predict 'yes'" if cond2_eval else "Proceed to default rule"
        })

        if cond2_eval:
            self.logger.success("CLASSIFICATION", f"Rule 2 matched: month '{raw_record.get('month')}' in {high_months} -> predicted 'yes'.")
            return {
                "prediction": "yes",
                "matched_rule_id": "RULE_2",
                "matched_rule_title": "Rule 2: High-Response Calendar Month",
                "explanation": f"Client contacted in '{raw_record.get('month')}' (one of March, September, October, December). Historical response rates in these shoulder months range between 44% and 51% in training data.",
                "trace": trace,
            }

        # Step 4: Default Rule
        trace.append({
            "step": 4,
            "rule": "Rule 3 (Default)",
            "condition": "else (no previous rules matched)",
            "result": True,
            "action": "Predict 'no'"
        })
        self.logger.info("CLASSIFICATION", "No special rule matched: applying default majority rule -> predicted 'no'.")
        return {
            "prediction": "no",
            "matched_rule_id": "RULE_DEFAULT",
            "matched_rule_title": "Rule 3 (Default): Fallback Majority Class",
            "explanation": "Neither Rule 1 nor Rule 2 matched. Because 88.3% of clients in the baseline population do not subscribe, the default decision predicts 'no'.",
            "trace": trace,
        }

    def get_cpt_table(self, node_name: str, artifacts: Optional[TrainedArtifacts] = None) -> pd.DataFrame:
        """Extract a readable DataFrame from the TabularCPD of a given node."""
        art = artifacts or self._artifacts
        if art is None:
            raise RuntimeError("Model is not trained.")
        cpd = art.model.get_cpds(node_name)
        if cpd is None:
            raise ValueError(f"No CPD found for node {node_name}")

        values = cpd.values
        variable = cpd.variable
        state_names = cpd.state_names
        var_states = state_names[variable]
        evidence = cpd.variables[1:]  # parent nodes

        if not evidence:
            # Prior distribution (no parents)
            df = pd.DataFrame({
                "State": var_states,
                "Probability": [float(v) for v in values]
            })
            return df

        # Conditional distribution
        # Build multi-index columns for parents
        parent_states_list = [state_names[p] for p in evidence]
        col_tuples = list(pd.MultiIndex.from_product(parent_states_list, names=evidence))

        flat_values = values.reshape(len(var_states), -1)
        df = pd.DataFrame(flat_values, index=var_states, columns=pd.MultiIndex.from_tuples(col_tuples, names=evidence))
        df.index.name = variable
        return df

    def get_cv_results(self) -> Optional[Any]:
        """Returns in-memory cross-validation results or loads them from disk if available."""
        if self._cv_results is None:
            from src.cross_validation import load_cv_results
            self._cv_results = load_cv_results(config.RESULTS_DIR)
        return self._cv_results

    def run_cross_validation(
        self,
        cfg: Optional[ModelConfig] = None,
        n_splits: int = 5,
        random_state: int = config.RANDOM_SEED,
        progress_callback: Optional[Callable[[str, float], None]] = None,
        results_dir: Optional[Path] = None
    ) -> Any:
        """Executes Stratified K-Fold Cross-Validation, preventing data leakage across folds."""
        from src.cross_validation import run_stratified_cv
        from src.evaluation import plot_cv_comparison
        df = self.get_raw_dataset()
        active_cfg = cfg or ModelConfig()
        out_dir = results_dir or config.RESULTS_DIR
        self.logger.info("CV", f"Starting Stratified {n_splits}-Fold Cross-Validation (seed={random_state})...")
        cv_results = run_stratified_cv(
            df=df,
            cfg=active_cfg,
            n_splits=n_splits,
            random_state=random_state,
            progress_callback=progress_callback,
            logger=self.logger
        )
        self._cv_results = cv_results
        cv_results.save(out_dir)
        plot_cv_comparison(cv_results.summary_df, out_dir / "cv_comparison.png")
        self.logger.success("CV", f"Cross-validation completed in {cv_results.total_duration:.2f}s and saved to {out_dir}.")
        return cv_results



# Singleton instance for application runtime
model_service = ModelService()


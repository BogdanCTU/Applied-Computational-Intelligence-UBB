"""Part A: Bayesian Network classifier built with pgmpy (version 1.1.x API).

Three separate stages (do not confuse them!):
  1. STRUCTURE learning  -> which nodes are connected by directed edges
                            (score-based Hill Climbing with the BIC score).
  2. PARAMETER learning  -> the conditional probability table (CPT) of every node,
                            estimated by counting in the training data with a
                            smoothing prior (Bayesian estimator, BDeu prior).
  3. INFERENCE           -> for a new client, compute P(y | all known features)
                            with Variable Elimination and pick the likelier class.
"""

import pandas as pd

from pgmpy.causal_discovery import HillClimbSearch
from pgmpy.inference import VariableElimination
from pgmpy.models import DiscreteBayesianNetwork
from pgmpy.parameter_estimator import DiscreteBayesianEstimator

from src import config


def learn_structure(train_df: pd.DataFrame, max_indegree: int = config.MAX_INDEGREE,
                    scoring_method: str = "bic-d") -> list[tuple[str, str]]:
    """Learn the DAG from training data with Hill Climbing + BIC.

    Hill climbing starts from an empty graph and repeatedly applies the single edge
    addition / removal / reversal that increases the BIC score most, until no change
    improves it. BIC = log-likelihood - penalty for model size, so it adds an edge only
    if the data supports it (this avoids a fully connected, over-fitted graph).
    `max_indegree` limits the number of parents per node to keep the CPTs small.

    `train_df` must contain the (discretised) features AND the target column `y`.
    """
    search = HillClimbSearch(scoring_method=scoring_method, max_indegree=max_indegree,
                             return_type="dag", show_progress=False)
    search.fit(train_df)
    return sorted(search.causal_graph_.edges())


def build_network(edges: list[tuple[str, str]], columns: list[str]) -> DiscreteBayesianNetwork:
    """Create the network object. Isolated nodes (no edges) are added explicitly."""
    model = DiscreteBayesianNetwork(edges)
    model.add_nodes_from(columns)
    return model


def fit_parameters(model: DiscreteBayesianNetwork, train_df: pd.DataFrame,
                   state_names: dict[str, list[str]],
                   equivalent_sample_size: int = config.BDEU_EQUIVALENT_SAMPLE_SIZE
                   ) -> DiscreteBayesianNetwork:
    """Estimate every CPT from the training data.

    Estimator: Bayesian estimation with a BDeu prior. It is "counting + smoothing":
        P(X = x | parents = u) = (count(x, u) + a) / (count(u) + a * |states of X|)
    where a is a small pseudo-count derived from `equivalent_sample_size`.
    Because of the pseudo-counts NO probability is ever exactly 0, so parent
    combinations that never occurred in training still get a valid (almost uniform)
    distribution, and test records with rare combinations never get probability 0.

    `state_names` lists ALL possible states of each variable (taken from the training
    preprocessor), so categories/bins absent from a CPT's counts are still represented.
    """
    estimator = DiscreteBayesianEstimator(state_names=state_names, prior_type="BDeu",
                                          equivalent_sample_size=equivalent_sample_size)
    model.fit(train_df, estimator=estimator)
    if not model.check_model():
        raise RuntimeError("The fitted Bayesian Network is not a valid model.")
    return model


def predict(model: DiscreteBayesianNetwork, X: pd.DataFrame) -> pd.DataFrame:
    """Predict the class for every row with exact inference (Variable Elimination).

    Returns a DataFrame with columns:
        proba_yes  - P(y = yes | evidence)
        prediction - 'yes' if proba_yes >= 0.5 else 'no'   (MAP class for 2 classes)
    Many clients share the same (binned) feature values, so inference is run once per
    DISTINCT row and the result is copied to all identical rows (same answer, much faster).
    """
    if config.TARGET in X.columns:
        raise ValueError("X must not contain the target column (target leakage).")
    inference = VariableElimination(model)
    unique_rows = X.drop_duplicates()
    probas = {}
    for row in unique_rows.itertuples(index=False, name=None):
        evidence = dict(zip(X.columns, row))
        # Drop evidence for variables that are not in the network.
        evidence = {k: v for k, v in evidence.items() if k in model.nodes()}
        result = inference.query([config.TARGET], evidence=evidence, show_progress=False)
        state_index = result.state_names[config.TARGET].index(config.POSITIVE_LABEL)
        probas[row] = float(result.values[state_index])
    proba_yes = pd.Series([probas[r] for r in X.itertuples(index=False, name=None)],
                          index=X.index, name="proba_yes")
    prediction = proba_yes.map(lambda p: config.POSITIVE_LABEL if p >= 0.5 else config.NEGATIVE_LABEL)
    return pd.DataFrame({"proba_yes": proba_yes, "prediction": prediction})


def describe_network(model: DiscreteBayesianNetwork) -> str:
    """Text description of the learned graph: parents of each node and the target's CPT."""
    lines = [f"Nodes: {len(model.nodes())}   Edges: {len(model.edges())}", "", "Edges (parent -> child):"]
    lines += [f"  {a} -> {b}" for a, b in sorted(model.edges())]
    lines.append("")
    lines.append(f"Markov blanket of '{config.TARGET}' (variables that matter for the "
                 f"prediction once the others are known): "
                 f"{sorted(model.get_markov_blanket(config.TARGET))}")
    lines.append("")
    lines.append(f"CPT of the target node '{config.TARGET}':")
    lines.append(str(model.get_cpds(config.TARGET)))
    return "\n".join(lines)


def save_network_plot(model: DiscreteBayesianNetwork, path) -> None:
    """Save a picture of the learned DAG (target node highlighted)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import networkx as nx

    graph = nx.DiGraph(model.edges())
    graph.add_nodes_from(model.nodes())
    positions = nx.spring_layout(graph, seed=config.RANDOM_SEED, k=1.2)
    colors = ["#e4572e" if n == config.TARGET else "#a7c4e5" for n in graph.nodes()]
    plt.figure(figsize=(11, 8))
    nx.draw_networkx(graph, positions, node_color=colors, node_size=1800, font_size=8,
                     arrowsize=15, edge_color="#555555")
    plt.title("Learned Bayesian Network structure (red = target y)")
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()

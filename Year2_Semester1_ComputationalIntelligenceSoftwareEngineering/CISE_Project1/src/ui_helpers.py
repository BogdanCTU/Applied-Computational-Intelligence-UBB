"""UI helper utilities for Streamlit: custom styles, metric cards, plotting,
and shared session state initialization.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
import seaborn as sns
import streamlit as st

from src import config
from src.model_service import ModelConfig, ModelService, model_service


CUSTOM_CSS = """
<style>
    /* Modern sleek academic styling */
    .stApp {
        background-color: #f8fafc;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Header hero styling */
    .hero-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        color: #ffffff;
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
    .hero-card h1 {
        color: #ffffff !important;
        font-size: 1.85rem;
        margin: 0 0 0.5rem 0;
        font-weight: 700;
    }
    .hero-card p {
        color: #94a3b8;
        font-size: 0.95rem;
        margin: 0;
    }
    
    /* Metric cards */
    .metric-box {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 1rem 1.25rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        text-align: center;
    }
    .metric-value {
        font-size: 1.65rem;
        font-weight: 700;
        color: #0f172a;
    }
    .metric-label {
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #64748b;
        font-weight: 600;
    }
    
    /* Educational callouts */
    .edu-note {
        background-color: #eff6ff;
        border-left: 4px solid #3b82f6;
        padding: 0.85rem 1.15rem;
        border-radius: 0 8px 8px 0;
        margin-bottom: 1rem;
        font-size: 0.9rem;
        color: #1e3a8a;
    }
    .edu-warning {
        background-color: #fffbeb;
        border-left: 4px solid #f59e0b;
        padding: 0.85rem 1.15rem;
        border-radius: 0 8px 8px 0;
        margin-bottom: 1rem;
        font-size: 0.9rem;
        color: #92400e;
    }
    
    /* Badge tags */
    .badge-yes {
        background-color: #dcfce7;
        color: #166534;
        padding: 2px 8px;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-no {
        background-color: #fee2e2;
        color: #991b1b;
        padding: 2px 8px;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.85rem;
    }
</style>
"""


def apply_custom_styles() -> None:
    """Injects custom CSS into the Streamlit app."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def init_session_state() -> None:
    """Ensures model service and configuration exist in session state."""
    if "service" not in st.session_state:
        st.session_state["service"] = model_service
    if "config" not in st.session_state:
        st.session_state["config"] = ModelConfig()


def render_sidebar_info() -> None:
    """Displays standard university header, dataset info and execution log in sidebar."""
    with st.sidebar:
        st.markdown("### 🎓 CISE Project")
        st.markdown("**Bayesian Networks vs. Rule-Based Classification**")
        st.caption("UCI Bank Marketing Classification (Python 3.11)")
        
        st.divider()
        st.markdown("#### 📂 Dataset Summary")
        st.write("• **Total Records:** 45,211")
        st.write("• **Input Attributes:** 15 (excl. `duration`)")
        st.write("• **Target (`y`):** 'yes' (11.7%) / 'no' (88.3%)")
        
        service: ModelService = st.session_state.get("service", model_service)
        artifacts = service.get_artifacts()
        
        st.divider()
        st.markdown("#### ⚙️ Model Status")
        if artifacts is not None:
            st.success(f"Models Trained ({len(artifacts.edges)} BN edges)")
            st.caption(f"Last training: {artifacts.training_duration:.2f}s")
        else:
            # Check if saved files exist on disk
            saved_metrics_file = config.RESULTS_DIR / "metrics.csv"
            if saved_metrics_file.exists():
                st.info("Pre-computed baseline metrics on disk.")
            else:
                st.warning("Models not trained yet.")
                
        st.divider()
        with st.expander("📜 Live Execution Logs", expanded=False):
            events = service.logger.get_events()
            if not events:
                st.caption("No events logged yet.")
            else:
                log_text = "\n".join(e.format_line() for e in events[-20:])
                st.code(log_text, language="log")


def plot_interactive_network(
    model: Any,
    selected_node: Optional[str] = None
) -> plt.Figure:
    """Draws the Bayesian Network DAG with the target node in vivid red and selected node highlighted."""
    graph = nx.DiGraph(model.edges())
    graph.add_nodes_from(model.nodes())
    
    fig, ax = plt.subplots(figsize=(10, 7), facecolor="#f8fafc")
    pos = nx.spring_layout(graph, seed=config.RANDOM_SEED, k=1.3)
    
    node_colors = []
    node_sizes = []
    
    for n in graph.nodes():
        if n == config.TARGET:
            node_colors.append("#ef4444")  # red for target
            node_sizes.append(2400)
        elif selected_node and n == selected_node:
            node_colors.append("#f59e0b")  # amber for selected node
            node_sizes.append(2600)
        else:
            node_colors.append("#93c5fd")  # soft blue for regular features
            node_sizes.append(1800)
            
    nx.draw_networkx_nodes(graph, pos, node_color=node_colors, node_size=node_sizes, ax=ax, alpha=0.92)
    nx.draw_networkx_labels(graph, pos, font_size=8, font_family="sans-serif", font_weight="bold", ax=ax)
    nx.draw_networkx_edges(
        graph, pos,
        edge_color="#64748b",
        arrows=True,
        arrowsize=14,
        arrowstyle="-|>",
        connectionstyle="arc3,rad=0.05",
        ax=ax,
        width=1.2
    )
    
    ax.set_title(
        f"Learned Bayesian Network DAG (Target '{config.TARGET}' highlighted in Red)",
        fontsize=12,
        fontweight="bold",
        pad=12
    )
    ax.axis("off")
    plt.tight_layout()
    return fig


def plot_cm(y_true: Any, y_pred: Any, title: str) -> plt.Figure:
    """Renders a styled confusion matrix heatmap."""
    from sklearn.metrics import confusion_matrix
    cm = confusion_matrix(y_true, y_pred, labels=config.LABELS)
    
    fig, ax = plt.subplots(figsize=(4, 3.2), facecolor="#ffffff")
    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        cmap="Blues",
        cbar=False,
        xticklabels=config.LABELS,
        yticklabels=config.LABELS,
        ax=ax,
        annot_kws={"size": 11, "weight": "bold"}
    )
    ax.set_xlabel("Predicted Class", fontsize=9, fontweight="bold")
    ax.set_ylabel("Actual Class", fontsize=9, fontweight="bold")
    ax.set_title(title, fontsize=10, fontweight="bold", pad=8)
    plt.tight_layout()
    return fig


def create_record_input_form(key_prefix: str = "pred") -> Dict[str, Any]:
    """Provides interactive input controls with realistic default values for all 15 features."""
    c1, c2, c3 = st.columns(3)
    
    with c1:
        poutcome = st.selectbox(
            "Previous Campaign Outcome (`poutcome`)",
            ["unknown", "success", "failure", "other"],
            index=0,
            key=f"{key_prefix}_poutcome",
            help="Outcome of the previous marketing campaign. Highly predictive!"
        )
        month = st.selectbox(
            "Contact Month (`month`)",
            ["may", "jul", "aug", "jun", "nov", "apr", "feb", "jan", "oct", "sep", "mar", "dec"],
            index=0,
            key=f"{key_prefix}_month",
            help="Last contact month of the year."
        )
        contact = st.selectbox(
            "Contact Communication Type (`contact`)",
            ["cellular", "telephone", "unknown"],
            index=0,
            key=f"{key_prefix}_contact"
        )
        housing = st.selectbox(
            "Housing Loan (`housing`)",
            ["yes", "no"],
            index=0,
            key=f"{key_prefix}_housing"
        )
        loan = st.selectbox(
            "Personal Loan (`loan`)",
            ["no", "yes"],
            index=0,
            key=f"{key_prefix}_loan"
        )

    with c2:
        age = st.slider("Client Age (`age`)", min_value=18, max_value=95, value=40, key=f"{key_prefix}_age")
        balance = st.number_input(
            "Average Yearly Balance in € (`balance`)",
            min_value=-8000,
            max_value=110000,
            value=1300,
            step=100,
            key=f"{key_prefix}_balance"
        )
        job = st.selectbox(
            "Job Type (`job`)",
            ["management", "blue-collar", "technician", "admin.", "services",
             "retired", "self-employed", "student", "unemployed", "entrepreneur", "housemaid", "unknown"],
            index=0,
            key=f"{key_prefix}_job"
        )
        marital = st.selectbox(
            "Marital Status (`marital`)",
            ["married", "single", "divorced"],
            index=0,
            key=f"{key_prefix}_marital"
        )
        education = st.selectbox(
            "Education Level (`education`)",
            ["secondary", "tertiary", "primary", "unknown"],
            index=1,
            key=f"{key_prefix}_education"
        )

    with c3:
        day = st.slider("Last Contact Day of Month (`day`)", min_value=1, max_value=31, value=15, key=f"{key_prefix}_day")
        campaign = st.slider("Contacts during this Campaign (`campaign`)", min_value=1, max_value=50, value=2, key=f"{key_prefix}_campaign")
        pdays = st.number_input(
            "Days since previous campaign (`pdays`, -1=never)",
            min_value=-1,
            max_value=900,
            value=-1,
            step=10,
            key=f"{key_prefix}_pdays",
            help="-1 means client was not previously contacted."
        )
        previous = st.number_input(
            "Number of previous contacts (`previous`)",
            min_value=0,
            max_value=100,
            value=0,
            step=1,
            key=f"{key_prefix}_previous"
        )
        default = st.selectbox(
            "Credit in Default (`default`)",
            ["no", "yes"],
            index=0,
            key=f"{key_prefix}_default"
        )

    return {
        "age": age,
        "job": job,
        "marital": marital,
        "education": education,
        "default": default,
        "balance": balance,
        "housing": housing,
        "loan": loan,
        "contact": contact,
        "day": day,
        "month": month,
        "campaign": campaign,
        "pdays": pdays,
        "previous": previous,
        "poutcome": poutcome,
    }

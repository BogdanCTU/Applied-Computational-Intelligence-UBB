"""Main Entry Point for the Streamlit Application:

Run locally via:
    python -m streamlit run app.py
"""

from pathlib import Path
import streamlit as st

from src import config
from src.model_service import ModelConfig, ModelService, model_service
from src.ui_helpers import apply_custom_styles, init_session_state, render_sidebar_info

st.set_page_config(
    page_title="Bank Marketing Classifier | Bayesian vs Rule-Based",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

init_session_state()
apply_custom_styles()
render_sidebar_info()

service: ModelService = st.session_state["service"]
current_cfg: ModelConfig = st.session_state["config"]

st.markdown("""
<div class="hero-card">
    <h1>🏦 Bayesian Network vs. Rule-Based Classification</h1>
    <p>University Machine Learning Project: Empirical Comparison on the UCI Bank Marketing Dataset</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
### Welcome to the Interactive Learning Application!

This project investigates whether a simple, explainable **Rule-Based Classifier** operating under strict
branching constraints (≤ *n* branches for *n* attributes used) can match or outperform a probabilistic
**Bayesian Network** on real-world bank marketing data.

---

### 🗺️ Application Navigation

Use the sidebar on the left or the cards below to explore the application:
""")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    #### ⚖️ [Page 1: Overview & Model Comparison](1_Overview)
    • Comparative performance table (Accuracy, Precision, Recall, F1).<br>
    • Side-by-side Confusion Matrices.<br>
    • Evaluation on the exact same held-out test set.<br>
    • Analysis of class imbalance and business trade-offs.
    """, unsafe_allow_html=True)
    
    st.markdown("""
    #### 🕸️ [Page 2: Bayesian Network (Part A)](2_Bayesian_Network)
    • Interactive hyper-parameter configuration.<br>
    • Real-time training pipeline with stage timers.<br>
    • Network DAG visualization with interactive Node Inspector.<br>
    • Tabular CPT browser with parent conditional distributions.<br>
    • Exact probabilistic inference (Variable Elimination) on custom clients.
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    #### 🌳 [Page 3: Rule-Based Classifier (Part B)](3_Rule_Based)
    • Readable rule specification with training-set rationale.<br>
    • **AST Branching Constraint Verification:** automated proof of compliance.<br>
    • Interactive single client prediction with step-by-step execution trace.<br>
    • Comparison against the Bayesian Network on test data.
    """, unsafe_allow_html=True)

    st.markdown("""
    #### 🔍 [Page 4: Dataset Explorer](4_Dataset_Explorer)
    • Interactive data table and distribution charts.<br>
    • Missing value inspection (`unknown` category analysis).<br>
    • Feature deep-dives with subscription rates.<br>
    • Raw numerical features vs. discrete quantile representations.
    """, unsafe_allow_html=True)

st.divider()

# Quick system readiness check
st.subheader("⚡ Quick System Status")
c1, c2, c3 = st.columns(3)

with c1:
    raw_path = config.CSV_PATH
    if raw_path.exists():
        st.success(f"✅ Dataset available: `{config.CSV_NAME}` ({raw_path.stat().st_size / 1024 / 1024:.1f} MB)")
    else:
        st.info("ℹ️ Dataset will be automatically fetched on first training run.")

with c2:
    artifacts = service.get_artifacts()
    if artifacts is not None:
        st.success(f"✅ Active Model: Trained ({len(artifacts.edges)} DAG edges)")
    else:
        st.warning("⚠️ Active Model: Not yet trained in this session.")

with c3:
    st.info("💡 Use Python 3.11 with: `python -m streamlit run app.py`")

st.write("")
st.markdown("""
<div class="edu-note">
    <strong>Educational Note on Target Leakage:</strong><br>
    In this application, the <code>duration</code> attribute (duration of the telephone call) is 
    <strong>strictly excluded</strong> from both classifiers. While duration strongly correlates with deposit success,
    call duration is unknown before dialing a customer. Excluding it ensures realistic pre-campaign targeting.
</div>
""", unsafe_allow_html=True)

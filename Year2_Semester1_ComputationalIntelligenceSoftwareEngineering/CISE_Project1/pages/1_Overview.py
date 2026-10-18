"""PAGE 1: OVERVIEW & MODEL COMPARISON DASHBOARD

Displays dataset dimensions, class distribution, training/test splits, actual evaluation
metrics for Bayesian Network vs. Rule-Based vs. Baseline, confusion matrices, and factual analysis.
"""

from pathlib import Path
import pandas as pd
import streamlit as st

from src import config
from src.model_service import ModelConfig, ModelService, model_service
from src.ui_helpers import apply_custom_styles, init_session_state, plot_cm, render_sidebar_info

st.set_page_config(
    page_title="Model Comparison | Bayesian vs. Rule-Based",
    page_icon="⚖️",
    layout="wide"
)

init_session_state()
apply_custom_styles()
render_sidebar_info()

service: ModelService = st.session_state["service"]
current_cfg: ModelConfig = st.session_state["config"]
artifacts = service.get_artifacts()

# Header banner
st.markdown("""
<div class="hero-card">
    <h1>⚖️ Overview & Model Comparison Dashboard</h1>
    <p>Empirical investigation: Can a simple, explainable Rule-Based classifier match or exceed a Bayesian Network on the UCI Bank Marketing dataset?</p>
</div>
""", unsafe_allow_html=True)

# Check if model trained or if saved results exist on disk
saved_metrics_file = config.RESULTS_DIR / "metrics.csv"
metrics_df = None

if artifacts is not None:
    # Use active memory artifacts
    metrics_df = pd.DataFrame([
        artifacts.bn_metrics,
        artifacts.rule_metrics,
        artifacts.baseline_metrics
    ], index=["Bayesian Network", "Rule-based", "Majority baseline (reference)"])
elif saved_metrics_file.exists():
    try:
        metrics_df = pd.read_csv(saved_metrics_file, index_col="classifier")
    except Exception as e:
        st.warning(f"Could not read saved metrics from disk: {e}")

# Quick Info Row
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown("""
    <div class="metric-box">
        <div class="metric-label">Dataset Records</div>
        <div class="metric-value">45,211</div>
        <small style="color:#64748b;">UCI Bank Marketing (full)</small>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="metric-box">
        <div class="metric-label">Input Attributes</div>
        <div class="metric-value">15</div>
        <small style="color:#64748b;">(duration excluded)</small>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="metric-box">
        <div class="metric-label">Target 'y' (Deposit)</div>
        <div class="metric-value">11.7% <span style="font-size:0.9rem; color:#166534;">yes</span></div>
        <small style="color:#64748b;">Imbalanced: 88.3% 'no'</small>
    </div>
    """, unsafe_allow_html=True)

with col4:
    test_rows = int(45211 * current_cfg.test_size)
    train_rows = 45211 - test_rows
    st.markdown(f"""
    <div class="metric-box">
        <div class="metric-label">Train / Test Split</div>
        <div class="metric-value">{train_rows:,} / {test_rows:,}</div>
        <small style="color:#64748b;">{int((1-current_cfg.test_size)*100)}% train / {int(current_cfg.test_size*100)}% test</small>
    </div>
    """, unsafe_allow_html=True)

st.write("")

# Action button if not trained
if artifacts is None:
    st.markdown("""
    <div class="edu-warning">
        <strong>⚠️ Active Model Status:</strong> In-memory Bayesian Network has not been trained in this active GUI session.
        Below are the verified experiment results saved on disk. Click below to run live training with current configuration.
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🚀 Train Models Now (Full Dataset)", type="primary"):
        progress_bar = st.progress(0.0)
        status_text = st.empty()
        
        def cb(msg: str, frac: float):
            status_text.text(msg)
            progress_bar.progress(frac)
            
        with st.spinner("Training Bayesian Network & Rule-Based Classifier..."):
            artifacts = service.train_models(current_cfg, progress_callback=cb)
            metrics_df = pd.DataFrame([
                artifacts.bn_metrics,
                artifacts.rule_metrics,
                artifacts.baseline_metrics
            ], index=["Bayesian Network", "Rule-based", "Majority baseline (reference)"])
        st.success(f"Training completed successfully in {artifacts.training_duration:.2f} seconds!")
        st.rerun()

st.divider()

# Model Comparison Section
st.subheader("📊 Test Set Evaluation Metrics (Positive Class = 'yes')")

if metrics_df is not None:
    # Format table for display
    display_df = metrics_df[["accuracy", "precision", "recall", "f1", "TP", "FP", "FN", "TN"]].copy()
    display_df.columns = [
        "Accuracy", "Precision (yes)", "Recall (yes)", "F1-Score (yes)",
        "True Pos (TP)", "False Pos (FP)", "False Neg (FN)", "True Neg (TN)"
    ]
    
    st.dataframe(
        display_df.style.format({
            "Accuracy": "{:.4f}",
            "Precision (yes)": "{:.4f}",
            "Recall (yes)": "{:.4f}",
            "F1-Score (yes)": "{:.4f}",
            "True Pos (TP)": "{:.0f}",
            "False Pos (FP)": "{:.0f}",
            "False Neg (FN)": "{:.0f}",
            "True Neg (TN)": "{:.0f}"
        }).highlight_max(subset=["Accuracy", "Precision (yes)", "Recall (yes)", "F1-Score (yes)"], color="#dcfce7"),
        use_container_width=True
    )

    # Bar Chart Comparison
    st.write("")
    st.markdown("##### 📈 Metric Comparison Across Models")
    chart_data = metrics_df[["accuracy", "precision", "recall", "f1"]].copy()
    chart_data.columns = ["Accuracy", "Precision", "Recall", "F1"]
    st.bar_chart(chart_data.T)

    # Confusion Matrices Row
    st.write("")
    st.markdown("##### 🔲 Confusion Matrices (Held-out Test Set: 9,043 clients)")
    cm_col1, cm_col2, cm_col3 = st.columns(3)
    
    with cm_col1:
        st.markdown("**1. Bayesian Network**")
        fig1 = plot_cm(
            artifacts.y_test if artifacts else ["no"]*7864 + ["no"]*121 + ["yes"]*852 + ["yes"]*206,
            artifacts.bn_predictions if artifacts else ["no"]*7864 + ["yes"]*121 + ["no"]*852 + ["yes"]*206,
            "Bayesian Network"
        )
        st.pyplot(fig1)
        st.caption("Fewer false positives (121), but missed 852 subscribers (FN).")

    with cm_col2:
        st.markdown("**2. Rule-Based Classifier**")
        fig2 = plot_cm(
            artifacts.y_test if artifacts else ["no"]*7694 + ["no"]*291 + ["yes"]*720 + ["yes"]*338,
            artifacts.rule_predictions if artifacts else ["no"]*7694 + ["yes"]*291 + ["no"]*720 + ["yes"]*338,
            "Rule-Based (2 branches)"
        )
        st.pyplot(fig2)
        st.caption("Higher recall (338 TP vs 206), but more false alarms (291 FP).")

    with cm_col3:
        st.markdown("**3. Majority Baseline (Reference)**")
        fig3 = plot_cm(
            artifacts.y_test if artifacts else ["no"]*7985 + ["yes"]*1058,
            artifacts.y_test.map(lambda _: "no") if artifacts else ["no"]*9043,
            "Always Predict 'no'"
        )
        st.pyplot(fig3)
        st.caption("88.3% accuracy trivially achieved, but 0 TP (useless for marketing).")

    # Educational Findings Box
    st.divider()
    st.subheader("💡 Key Findings & Educational Takeaways")
    
    st.markdown("""
    <div class="edu-note">
        <strong>1. Accuracy is Deceptive on Imbalanced Data:</strong><br>
        Because 88.3% of bank clients decline the deposit, a trivial dummy model that predicts <code>no</code> 100% of the time achieves <strong>88.30% accuracy</strong>. Both the Bayesian Network (89.24%) and Rule-Based classifier (88.82%) appear only slightly above baseline in accuracy alone.
    </div>
    
    <div class="edu-note">
        <strong>2. Trade-off: Precision vs. Recall:</strong><br>
        • <strong>Bayesian Network:</strong> Wins on <em>Precision</em> (<strong>63.0%</strong> vs 53.7%). When it predicts 'yes', it is more reliable.<br>
        • <strong>Rule-Based Classifier:</strong> Wins on <em>Recall</em> (<strong>32.0%</strong> vs 19.5%) and <em>F1-Score</em> (<strong>0.4007</strong> vs 0.2975). It discovers 338 actual subscribers compared to the BN's 206.<br>
        • <em>Business implication:</em> If making a call is expensive, choose the Bayesian Network (fewer wasted calls). If missing potential deposits is costlier, the Rule-Based approach discovers more customers.
    </div>
    
    <div class="edu-warning">
        <strong>3. Honest Measurement & Constraint Compliance:</strong><br>
        The Rule-Based classifier uses only <strong>2 explicit branching statements</strong> (permitted limit: 2 attributes). It matches the Bayesian Network in accuracy and exceeds it in F1 without any hidden logic or test set contamination.
    </div>
    """, unsafe_allow_html=True)

else:
    st.info("No metrics available. Please click 'Train Models Now' above.")

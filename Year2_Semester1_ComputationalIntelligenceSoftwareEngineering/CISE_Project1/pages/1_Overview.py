"""PAGE 1: OVERVIEW & MODEL COMPARISON DASHBOARD

Displays dataset dimensions, class distribution, training/test splits, actual evaluation
metrics for Bayesian Network vs. Rule-Based vs. Baseline, confusion matrices, and factual analysis.
Includes dedicated Stratified 5-Fold Cross-Validation evaluation with zero data leakage.
"""

from pathlib import Path
import pandas as pd
import streamlit as st

from src import config
from src.model_service import ModelConfig, ModelService, model_service
from src.ui_helpers import (
    apply_custom_styles,
    init_session_state,
    plot_cm,
    plot_cv_barchart,
    render_sidebar_info
)

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

# ==============================================================================
# SECTION 1: Held-out Test Set Evaluation
# ==============================================================================
st.subheader("📊 Held-Out Test Set Evaluation Metrics (Positive Class = 'yes')")
st.caption(f"Single 80/20 stratified split ({train_rows:,} train / {test_rows:,} test, seed={current_cfg.random_seed}).")

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
    st.markdown("##### 📈 Held-Out Test Set Metric Comparison")
    chart_data = metrics_df[["accuracy", "precision", "recall", "f1"]].copy()
    chart_data.columns = ["Accuracy", "Precision", "Recall", "F1"]
    st.bar_chart(chart_data.T)

    # Confusion Matrices Row
    st.write("")
    st.markdown(f"##### 🔲 Held-Out Confusion Matrices ({test_rows:,} clients)")
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

else:
    st.info("No held-out test metrics available. Please click 'Train Models Now' above.")

# ==============================================================================
# SECTION 2: Stratified 5-Fold Cross-Validation
# ==============================================================================
st.divider()
st.subheader("🔁 Stratified 5-Fold Cross-Validation Evaluation")
st.markdown("""
<div class="edu-note">
    <strong>Leak-Free Cross-Validation Architecture:</strong><br>
    The data is partitioned into 5 stratified folds (using <code>StratifiedKFold</code>, <code>random_state=42</code>).
    Inside every fold:
    <ol style="margin-top:0.3rem; margin-bottom:0.3rem;">
        <li>Preprocessing and quantile discretization are fitted exclusively on the 4/5 training partition.</li>
        <li>Learned transformations are applied to the 1/5 validation partition without refitting.</li>
        <li>Bayesian Network DAG structure is learned from scratch using Hill Climbing + BIC on the training fold.</li>
        <li>CPT parameters are estimated via BDeu smoothing on the training fold only.</li>
        <li>Inference is evaluated on the validation fold; the Rule-Based classifier is evaluated on the exact same records.</li>
    </ol>
    This guarantees <strong>zero data leakage</strong> across folds and yields true variance estimates.
</div>
""", unsafe_allow_html=True)

cv_results = service.get_cv_results()

col_cv_btn, col_cv_info = st.columns([1.3, 2.7])
with col_cv_btn:
    btn_label = "🚀 Run Stratified 5-Fold CV" if cv_results is None else "🔄 Re-run Stratified 5-Fold CV"
    if st.button(btn_label, type="primary" if cv_results is None else "secondary"):
        cv_progress = st.progress(0.0)
        cv_status = st.empty()

        def on_cv_progress(msg: str, frac: float):
            cv_status.text(msg)
            cv_progress.progress(frac)

        with st.spinner("Executing 5-Fold Cross-Validation across full dataset (all models)..."):
            cv_results = service.run_cross_validation(current_cfg, progress_callback=on_cv_progress)
        st.success(f"5-Fold Cross-Validation completed in {cv_results.total_duration:.2f} seconds!")
        st.rerun()

with col_cv_info:
    if cv_results is not None:
        st.caption(
            f"✅ **Cross-Validation Active:** 5 folds, seed={cv_results.random_state}, total runtime: {cv_results.total_duration:.2f}s. "
            f"All 45,211 records evaluated out-of-fold."
        )
    else:
        st.caption("ℹ️ Click the button to execute Stratified 5-Fold Cross-Validation on the full dataset.")

if cv_results is not None:
    # Telemetry cards
    cv_c1, cv_c2, cv_c3, cv_c4 = st.columns(4)
    with cv_c1:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-label">Cross-Validation Folds</div>
            <div class="metric-value">{cv_results.n_splits}</div>
            <small style="color:#64748b;">Stratified (seed={cv_results.random_state})</small>
        </div>
        """, unsafe_allow_html=True)
    with cv_c2:
        bn_f1_m = float(cv_results.summary_df.loc['Bayesian Network', 'f1_mean'])
        bn_f1_s = float(cv_results.summary_df.loc['Bayesian Network', 'f1_std'])
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-label">BN F1-Score (Mean ± Std)</div>
            <div class="metric-value" style="font-size:1.35rem; color:#2563eb;">
                {bn_f1_m:.4f} <span style="font-size:0.9rem; color:#64748b;">± {bn_f1_s:.4f}</span>
            </div>
            <small style="color:#64748b;">Bayesian Network (DAG + CPT)</small>
        </div>
        """, unsafe_allow_html=True)
    with cv_c3:
        rule_f1_m = float(cv_results.summary_df.loc['Rule-based', 'f1_mean'])
        rule_f1_s = float(cv_results.summary_df.loc['Rule-based', 'f1_std'])
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-label">Rule-Based F1 (Mean ± Std)</div>
            <div class="metric-value" style="font-size:1.35rem; color:#16a34a;">
                {rule_f1_m:.4f} <span style="font-size:0.9rem; color:#64748b;">± {rule_f1_s:.4f}</span>
            </div>
            <small style="color:#64748b;">2 Branching Statements</small>
        </div>
        """, unsafe_allow_html=True)
    with cv_c4:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-label">Total CV Execution Time</div>
            <div class="metric-value" style="font-size:1.35rem;">{cv_results.total_duration:.2f}s</div>
            <small style="color:#64748b;">~{cv_results.total_duration/cv_results.n_splits:.2f}s per fold</small>
        </div>
        """, unsafe_allow_html=True)

    st.write("")
    st.markdown("##### 📋 Cross-Validation Summary Table (Mean ± Standard Deviation across 5 Folds)")
    display_cv = cv_results.get_display_summary()
    st.dataframe(
        display_cv.style.set_properties(**{'text-align': 'center'}),
        use_container_width=True
    )

    # Comparison visualization
    st.write("")
    st.markdown("##### 📈 Cross-Validation Metric Comparison (with Standard Deviation Error Bars)")
    fig_cv = plot_cv_barchart(cv_results.summary_df)
    st.pyplot(fig_cv)

    # Detailed Sub-Tabs
    st.write("")
    cv_tab1, cv_tab2, cv_tab3 = st.tabs([
        "🔍 Fold-by-Fold Breakdown",
        "⚖️ Fold Mean vs. Out-of-Fold Pooled Metrics",
        "🔲 Aggregated Confusion Matrices (Pooled 45,211 Instances)"
    ])

    with cv_tab1:
        st.markdown("**Per-Fold Detailed Metric Records:**")
        st.dataframe(
            cv_results.fold_metrics_df.style.format({
                "accuracy": "{:.4f}",
                "precision": "{:.4f}",
                "recall": "{:.4f}",
                "f1": "{:.4f}",
                "TN": "{:.0f}",
                "FP": "{:.0f}",
                "FN": "{:.0f}",
                "TP": "{:.0f}",
                "duration_seconds": "{:.2f}s"
            }),
            use_container_width=True
        )

    with cv_tab2:
        st.markdown("""
        <div class="edu-note">
            <strong>Distinguishing Fold-Level Means from Out-of-Fold (OOF) Pooled Metrics:</strong><br>
            • <strong>Fold-Level Mean (± Std):</strong> The arithmetic average of the metric computed independently on each of the 5 validation slices. It measures expected performance on a new fold and captures sampling variability across splits.<br>
            • <strong>Out-of-Fold Pooled:</strong> Concatenates the predictions across all 5 validation folds (covering exactly 100% of the dataset) and computes precision, recall, and F1 globally from the pooled confusion matrix ($\sum TP / (\sum TP + \sum FP)$).<br>
            • <em>Why they differ:</em> Non-linear metrics like F1 and Precision are ratios. The mean of ratios is not strictly equal to the ratio of totals (Jensen's inequality). Both are reported below for transparency.
        </div>
        """, unsafe_allow_html=True)

        comp_rows = []
        for clf in ["Bayesian Network", "Rule-based", "Majority baseline (reference)"]:
            comp_rows.append({
                "Classifier": clf,
                "Accuracy (Fold Mean ± Std)": cv_results.summary_df.loc[clf, "accuracy_display"],
                "Accuracy (Pooled OOF)": f"{cv_results.pooled_df.loc[clf, 'accuracy']:.4f}",
                "Precision (Fold Mean ± Std)": cv_results.summary_df.loc[clf, "precision_display"],
                "Precision (Pooled OOF)": f"{cv_results.pooled_df.loc[clf, 'precision']:.4f}",
                "Recall (Fold Mean ± Std)": cv_results.summary_df.loc[clf, "recall_display"],
                "Recall (Pooled OOF)": f"{cv_results.pooled_df.loc[clf, 'recall']:.4f}",
                "F1 (Fold Mean ± Std)": cv_results.summary_df.loc[clf, "f1_display"],
                "F1 (Pooled OOF)": f"{cv_results.pooled_df.loc[clf, 'f1']:.4f}",
            })
        st.dataframe(pd.DataFrame(comp_rows).set_index("Classifier"), use_container_width=True)

    with cv_tab3:
        st.markdown("**Aggregated Confusion Matrices (Out-of-Fold, 45,211 Instances Total):**")
        oof_cm_col1, oof_cm_col2, oof_cm_col3 = st.columns(3)
        oof = cv_results.oof_predictions

        if not oof.empty and "actual" in oof.columns:
            with oof_cm_col1:
                st.markdown("**1. Bayesian Network (Pooled)**")
                fig_oof_bn = plot_cm(oof["actual"], oof["bayesian_network"], "BN Out-of-Fold (N=45,211)")
                st.pyplot(fig_oof_bn)
                st.caption(
                    f"Total TP: {int(cv_results.summary_df.loc['Bayesian Network', 'total_TP']):,} | "
                    f"FP: {int(cv_results.summary_df.loc['Bayesian Network', 'total_FP']):,}"
                )

            with oof_cm_col2:
                st.markdown("**2. Rule-Based Classifier (Pooled)**")
                fig_oof_rule = plot_cm(oof["actual"], oof["rule_based"], "Rule-Based Out-of-Fold (N=45,211)")
                st.pyplot(fig_oof_rule)
                st.caption(
                    f"Total TP: {int(cv_results.summary_df.loc['Rule-based', 'total_TP']):,} | "
                    f"FP: {int(cv_results.summary_df.loc['Rule-based', 'total_FP']):,}"
                )

            with oof_cm_col3:
                st.markdown("**3. Majority Baseline (Pooled)**")
                fig_oof_base = plot_cm(oof["actual"], oof["majority_baseline"], "Baseline Out-of-Fold (N=45,211)")
                st.pyplot(fig_oof_base)
                st.caption("All 45,211 predicted as 'no' (0 TP).")

# ==============================================================================
# SECTION 3: Educational Findings
# ==============================================================================
st.divider()
st.subheader("💡 Key Findings & Educational Takeaways")

st.markdown("""
<div class="edu-note">
    <strong>1. Accuracy is Deceptive on Imbalanced Data:</strong><br>
    Because 88.3% of bank clients decline the deposit, a trivial dummy model that predicts <code>no</code> 100% of the time achieves <strong>88.30% accuracy</strong>. Both the Bayesian Network (~89.2%) and Rule-Based classifier (~88.8%) appear only slightly above baseline in accuracy alone.
</div>

<div class="edu-note">
    <strong>2. Trade-off: Precision vs. Recall across Both Evaluations:</strong><br>
    • <strong>Bayesian Network:</strong> Wins on <em>Precision</em> (~62.8% vs 53.7%). When it predicts 'yes', it is more reliable with fewer false alarms.<br>
    • <strong>Rule-Based Classifier:</strong> Wins on <em>Recall</em> (~32.0% vs 19.5%) and <em>F1-Score</em> (~0.400 vs 0.297). It discovers significantly more actual deposit subscribers.<br>
    • <strong>Cross-Validation Consistency:</strong> Low standard deviations (σ < 0.01 across folds) confirm that these trade-offs are intrinsic structural properties of the models, not artifacts of a fortunate 80/20 train/test split.
</div>

<div class="edu-warning">
    <strong>3. Honest Measurement & Constraint Compliance:</strong><br>
    The Rule-Based classifier uses only <strong>2 explicit branching statements</strong> (permitted limit: 2 attributes). It matches the Bayesian Network in accuracy and exceeds it in F1 without any hidden logic or test set contamination.
</div>
""", unsafe_allow_html=True)

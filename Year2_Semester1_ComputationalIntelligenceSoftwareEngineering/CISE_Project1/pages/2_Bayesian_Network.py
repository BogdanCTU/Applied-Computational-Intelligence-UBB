"""PAGE 2: BAYESIAN NETWORK CLASSIFIER

Interactive interface for configuring, training, visualizing, inspecting CPTs,
and performing exact probabilistic inference on the Bayesian Network.
"""

import time
import pandas as pd
import streamlit as st

from src import config
from src.model_service import ModelConfig, ModelService, model_service
from src.ui_helpers import (
    apply_custom_styles,
    create_record_input_form,
    init_session_state,
    plot_interactive_network,
    render_sidebar_info,
)

st.set_page_config(
    page_title="Bayesian Network | CISE Project",
    page_icon="🕸️",
    layout="wide"
)

init_session_state()
apply_custom_styles()
render_sidebar_info()

service: ModelService = st.session_state["service"]
current_cfg: ModelConfig = st.session_state["config"]

st.markdown("""
<div class="hero-card">
    <h1>🕸️ Bayesian Network Classifier (Part A)</h1>
    <p>Probabilistic Graphical Model: Directed Acyclic Graph (DAG) Structure Learning + Bayesian Parameter Estimation + Variable Elimination Inference.</p>
</div>
""", unsafe_allow_html=True)

tabs = st.tabs([
    "⚙️ A. Configuration & Training",
    "🗺️ B. Network Visualization & Node Inspector",
    "📋 C. Conditional Probability Tables (CPTs)",
    "🔮 D. Single Client Inference",
    "🔬 E. Execution Details & Internals"
])

# ==========================================
# TAB 1: Configuration & Training
# ==========================================
with tabs[0]:
    st.subheader("Model Configuration")
    st.caption("Adjust safe hyper-parameters below. Note: changing settings invalidates existing trained artifacts.")

    col1, col2, col3 = st.columns(3)
    with col1:
        new_test_size = st.slider("Test Set Fraction", 0.1, 0.4, float(current_cfg.test_size), 0.05)
        new_seed = st.number_input("Random Seed (reproducibility)", value=int(current_cfg.random_seed), step=1)
    with col2:
        new_max_indegree = st.slider(
            "Max In-Degree (Parents per Node)",
            min_value=1, max_value=5, value=int(current_cfg.max_indegree),
            help="Upper bound on number of parents per node to prevent exponential CPT growth."
        )
        new_sample_size = st.number_input(
            "BDeu Equivalent Sample Size (Prior)",
            min_value=1, max_value=50, value=int(current_cfg.equivalent_sample_size),
            help="Pseudo-count strength for Dirichlet/BDeu prior smoothing."
        )
    with col3:
        st.markdown("**Quantile Discretization Bins:**")
        n_age = st.slider("Age Bins", 2, 6, int(current_cfg.n_bins_age))
        n_bal = st.slider("Balance Bins", 2, 6, int(current_cfg.n_bins_balance))

    # Detect configuration changes
    temp_cfg = ModelConfig(
        test_size=new_test_size,
        random_seed=new_seed,
        max_indegree=new_max_indegree,
        equivalent_sample_size=new_sample_size,
        n_bins_age=n_age,
        n_bins_balance=n_bal
    )

    if temp_cfg.get_signature() != current_cfg.get_signature():
        st.session_state["config"] = temp_cfg
        current_cfg = temp_cfg
        service.invalidate_model(reason="Hyperparameters updated by user")
        st.warning("⚠️ Configuration changed! Existing trained model invalidated. Please retrain below.")

    st.write("")
    is_trained = service.is_trained(current_cfg)
    
    if is_trained:
        st.success("✅ Model is trained and ready with the current configuration.")
    else:
        st.info("ℹ️ Model needs training to update with current settings.")

    train_btn = st.button("🚀 Train Bayesian Network", type="primary")

    if train_btn:
        progress_bar = st.progress(0.0)
        status_box = st.empty()

        def on_progress(stage_title: str, frac: float):
            status_box.markdown(f"**Executing:** `{stage_title}`")
            progress_bar.progress(frac)

        try:
            with st.spinner("Training in progress..."):
                artifacts = service.train_models(current_cfg, progress_callback=on_progress)
            st.success(f"🎉 Bayesian Network trained successfully in {artifacts.training_duration:.2f} seconds!")
            st.rerun()
        except Exception as ex:
            st.error(f"❌ Training failed: {ex}")

# Fetch active artifacts
artifacts = service.get_artifacts()

# ==========================================
# TAB 2: Network Visualization
# ==========================================
with tabs[1]:
    st.subheader("Learned Network Structure (Directed Acyclic Graph)")
    
    if artifacts is None:
        st.warning("⚠️ Bayesian Network is not trained yet. Please train it in the Configuration tab.")
    else:
        st.markdown("""
        <div class="edu-note">
            <strong>How to read this graph:</strong><br>
            • <strong>Nodes:</strong> Random variables (15 attributes + target <code>y</code> in <span style="color:#ef4444; font-weight:bold;">Red</span>).<br>
            • <strong>Directed Edges (A → B):</strong> Direct conditional dependencies learned via <em>Hill Climb Search</em> with the <em>BIC score</em>.<br>
            • <strong>Absence of an edge:</strong> Represents conditional independence given other variables.
        </div>
        """, unsafe_allow_html=True)

        col_viz, col_inspect = st.columns([1.7, 1.0])
        
        with col_inspect:
            st.markdown("##### 🔍 Node Inspector")
            all_nodes = sorted(list(artifacts.model.nodes()))
            target_idx = all_nodes.index(config.TARGET) if config.TARGET in all_nodes else 0
            selected_node = st.selectbox("Select a node to inspect:", all_nodes, index=target_idx)
            
            parents = sorted(list(artifacts.model.predecessors(selected_node)))
            children = sorted(list(artifacts.model.successors(selected_node)))
            markov_blanket = sorted(list(artifacts.model.get_markov_blanket(selected_node)))
            
            st.write(f"• **In-Degree (Parents count):** {len(parents)}")
            st.write(f"• **Direct Parents:** {', '.join(parents) if parents else 'None (Root Node)'}")
            st.write(f"• **Out-Degree (Children count):** {len(children)}")
            st.write(f"• **Direct Children:** {', '.join(children) if children else 'None (Leaf Node)'}")
            st.write(f"• **Markov Blanket:** `{', '.join(markov_blanket)}`")
            st.caption(
                "The Markov Blanket shields the node: given all variables in its Markov blanket, "
                "this node is conditionally independent of all remaining nodes in the entire network."
            )

        with col_viz:
            fig = plot_interactive_network(artifacts.model, selected_node=selected_node)
            st.pyplot(fig)

# ==========================================
# TAB 3: Conditional Probability Tables (CPTs)
# ==========================================
with tabs[2]:
    st.subheader("Conditional Probability Tables (CPTs)")
    
    if artifacts is None:
        st.warning("⚠️ Bayesian Network is not trained yet. Please train it in the Configuration tab.")
    else:
        st.markdown("""
        <div class="edu-note">
            <strong>What is a CPT?</strong><br>
            A CPT quantifies the probabilistic relationship between a node and its parents: 
            <code>P(Node = state | Parents = parent_states)</code>.<br>
            Each column forms a complete probability distribution that sums strictly to <strong>1.0</strong>.<br>
            <em>BDeu Prior Smoothing:</em> Ensures zero-probability estimates never occur, preventing catastrophic inference failures on rare test cases.
        </div>
        """, unsafe_allow_html=True)

        nodes_list = sorted(list(artifacts.model.nodes()))
        target_idx = nodes_list.index(config.TARGET) if config.TARGET in nodes_list else 0
        cpt_node = st.selectbox("Choose Variable to Inspect CPT:", nodes_list, index=target_idx, key="cpt_select")

        parents = sorted(list(artifacts.model.predecessors(cpt_node)))
        st.markdown(f"**Variable:** `{cpt_node}` | **Parents ({len(parents)}):** `{', '.join(parents) if parents else 'None (Prior Table)'}`")
        
        try:
            cpt_df = service.get_cpt_table(cpt_node, artifacts=artifacts)
            st.dataframe(cpt_df.style.format("{:.4f}"), use_container_width=True)
            st.caption(f"Showing conditional probabilities for {len(cpt_df.columns)} combinations of parent states.")
        except Exception as e:
            st.error(f"Error formatting CPT: {e}")

# ==========================================
# TAB 4: Single Client Inference
# ==========================================
with tabs[3]:
    st.subheader("Probabilistic Inference on a Bank Client")
    
    if artifacts is None:
        st.warning("⚠️ Bayesian Network is not trained yet. Please train it in the Configuration tab.")
    else:
        st.markdown("""
        <div class="edu-note">
            <strong>Inference Mechanism:</strong><br>
            1. The raw client attributes below are discretized using the exact quantile boundaries learned from training data.<br>
            2. The discretized values are passed as evidence to the <strong>Variable Elimination</strong> exact inference algorithm.<br>
            3. The posterior probability distribution <code>P(y | evidence)</code> is computed by marginalizing over hidden nodes.
        </div>
        """, unsafe_allow_html=True)

        with st.form("bn_inference_form"):
            st.markdown("##### 📝 Client Profile Inputs")
            raw_input = create_record_input_form(key_prefix="bn")
            predict_btn = st.form_submit_button("🔮 Calculate Posterior Probabilities", type="primary")

        if predict_btn:
            with st.spinner("Computing exact inference via Variable Elimination..."):
                res = service.predict_single_bn(raw_input, artifacts=artifacts)
                
            pred_class = res["prediction"]
            p_yes = res["p_yes"]
            p_no = res["p_no"]
            
            res_col1, res_col2 = st.columns([1, 1.5])
            
            with res_col1:
                st.markdown("##### 🎯 Classification Output")
                if pred_class == "yes":
                    st.markdown("""
                    <div style="background-color:#dcfce7; padding:1.25rem; border-radius:10px; border:1px solid #86efac; text-align:center;">
                        <span style="font-size:1.85rem; font-weight:bold; color:#166534;">PREDICTION: YES</span><br>
                        <span style="color:#15803d;">Client is likely to subscribe to the term deposit.</span>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div style="background-color:#fee2e2; padding:1.25rem; border-radius:10px; border:1px solid #fca5a5; text-align:center;">
                        <span style="font-size:1.85rem; font-weight:bold; color:#991b1b;">PREDICTION: NO</span><br>
                        <span style="color:#b91c1c;">Client is unlikely to subscribe to the term deposit.</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                st.write("")
                st.write(f"• **P(y = 'yes' | evidence):** `{p_yes:.4f}` ({p_yes*100:.1f}%)")
                st.write(f"• **P(y = 'no' | evidence):** `{p_no:.4f}` ({p_no*100:.1f}%)")
                st.caption(f"Decision threshold: 0.50 (Maximum A Posteriori / MAP).")

            with res_col2:
                st.markdown("##### 🔍 Evidence Supplied to Network")
                evidence_items = res["evidence"]
                ev_df = pd.DataFrame([
                    {"Attribute": k, "Raw Value": raw_input.get(k), "Discretized State": v}
                    for k, v in evidence_items.items()
                ])
                st.dataframe(ev_df, height=220, use_container_width=True)
                
            st.markdown(f"""
            <div class="edu-warning">
                <strong>⚠️ Statistical Disclaimer:</strong> {res["disclaimer"]}
            </div>
            """, unsafe_allow_html=True)

# ==========================================
# TAB 5: Execution Details & Internals
# ==========================================
with tabs[4]:
    st.subheader("🔬 Internal Execution Details & Diagnostic Telemetry")
    
    if artifacts is None:
        st.info("No training details available yet. Train the model to inspect telemetry.")
    else:
        st.markdown("##### ⏱️ Execution Stage Durations")
        stage_df = pd.DataFrame([
            {"Stage": k.replace("_", " ").title(), "Duration (seconds)": f"{v:.3f}s"}
            for k, v in artifacts.stage_durations.items()
        ])
        st.dataframe(stage_df, use_container_width=True)
        st.write(f"**Total End-to-End Elapsed Time:** `{artifacts.training_duration:.2f} seconds`")

        st.divider()
        st.markdown("##### 📐 Learned Graph Edges (30 Directed Connections)")
        edge_text = ", ".join(f"{u} → {v}" for u, v in sorted(artifacts.edges))
        st.text_area("Edge List", edge_text, height=120)

        st.divider()
        st.markdown("##### 📏 Quantile Discretization Boundaries")
        bin_records = []
        for col in config.NUMERIC_FEATURES:
            states = artifacts.preprocessor.states(col)
            edges = artifacts.preprocessor.bin_edges_.get(col, [])
            bin_records.append({
                "Feature": col,
                "Bins Count": len(states),
                "Learned Cutoff Edges": str([round(e, 2) for e in edges]),
                "Discrete State Names": str(states)
            })
        st.dataframe(pd.DataFrame(bin_records), use_container_width=True)

        st.divider()
        st.markdown("##### 🔁 Cross-Validation Consistency")
        cv_res = service.get_cv_results()
        if cv_res is not None:
            bn_f1_m = float(cv_res.summary_df.loc["Bayesian Network", "f1_mean"])
            bn_f1_s = float(cv_res.summary_df.loc["Bayesian Network", "f1_std"])
            bn_p_m = float(cv_res.summary_df.loc["Bayesian Network", "precision_mean"])
            bn_p_s = float(cv_res.summary_df.loc["Bayesian Network", "precision_std"])
            st.markdown(f"""
            <div class="edu-note">
                <strong>Stratified 5-Fold Cross-Validation Performance:</strong><br>
                Across 5 independent folds with leak-free structure learning and parameter estimation:<br>
                • <strong>F1-Score:</strong> <code>{bn_f1_m:.4f} ± {bn_f1_s:.4f}</code><br>
                • <strong>Precision:</strong> <code>{bn_p_m:.4f} ± {bn_p_s:.4f}</code><br>
                See <a href="1_Overview" target="_self">Page 1 (Overview)</a> for comparative breakdowns against the Rule-Based classifier.
            </div>
            """, unsafe_allow_html=True)
        else:
            st.caption("Cross-validation has not been run yet. Execute 5-fold CV from Page 1 (Overview) or via `python -m src.main --cv`.")


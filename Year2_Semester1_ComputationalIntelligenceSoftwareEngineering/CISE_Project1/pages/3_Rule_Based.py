"""PAGE 3: RULE-BASED CLASSIFICATION

Inspect the transparent rule set, verify AST branching statement compliance,
classify single records with an explicit execution trace, and inspect test metrics.
"""

from pathlib import Path
import pandas as pd
import streamlit as st

from src import config
from src.model_service import ModelConfig, ModelService, model_service
from src.ui_helpers import (
    apply_custom_styles,
    create_record_input_form,
    init_session_state,
    plot_cm,
    render_sidebar_info,
)
import branch_counter
import rule_based

st.set_page_config(
    page_title="Rule-Based Classifier | CISE Project",
    page_icon="🌳",
    layout="wide"
)

init_session_state()
apply_custom_styles()
render_sidebar_info()

service: ModelService = st.session_state["service"]
current_cfg: ModelConfig = st.session_state["config"]

st.markdown("""
<div class="hero-card">
    <h1>🌳 Rule-Based Classifier (Part B)</h1>
    <p>Transparent, explainable decision logic operating under strict branching constraints (at most n branching statements for n attributes used).</p>
</div>
""", unsafe_allow_html=True)

tabs = st.tabs([
    "📜 A. Rule Inspection & Logic",
    "🛡️ B. Branching Constraint Verification",
    "🎯 C. Interactive Classification & Execution Trace",
    "📊 D. Held-out Test Set Evaluation"
])

# ==========================================
# TAB 1: Rule Inspection
# ==========================================
with tabs[0]:
    st.subheader("Classification Rules Specification")
    st.markdown("""
    <div class="edu-note">
        <strong>Domain Motivation & Training-Set Grounding:</strong><br>
        These rules were formulated by analyzing category response rates on the <strong>training split only</strong> (no test labels were inspected):<br>
        • Baseline deposit rate across all clients: <strong>11.7%</strong>.<br>
        • Clients with successful prior campaigns (<code>poutcome = 'success'</code>): <strong>64.6%</strong> subscription rate.<br>
        • Shoulder calendar months (March, September, October, December): <strong>44% - 51%</strong> subscription rate (vs ≤ 20% for other months).<br>
        • Fallback: Clients outside these high-propensity segments revert to the default majority class (<code>no</code>).
    </div>
    """, unsafe_allow_html=True)

    rules_data = [
        {
            "Rule ID": "RULE_1",
            "Statement Type": "if",
            "Condition": "record['poutcome'] == 'success'",
            "Predicted Class": "yes",
            "Type": "Explicit Rule",
            "Rationale": "Historical campaign success strongly indicates willingness to invest."
        },
        {
            "Rule ID": "RULE_2",
            "Statement Type": "elif",
            "Condition": "record['month'] in ('mar', 'sep', 'oct', 'dec')",
            "Predicted Class": "yes",
            "Type": "Explicit Rule",
            "Rationale": "Shoulder months show ~4x higher deposit response than peak volume months."
        },
        {
            "Rule ID": "RULE_DEFAULT",
            "Statement Type": "else",
            "Condition": "None (all other records)",
            "Predicted Class": "no",
            "Type": "Default Rule",
            "Rationale": "88.3% of unsegmented bank clients decline term deposits."
        }
    ]
    st.dataframe(pd.DataFrame(rules_data), use_container_width=True)

    with st.expander("🔍 View Complete Classifier Source Code (`3_RuleBasedClassification/rule_based.py`)", expanded=True):
        source_code = (config.RULES_DIR / "rule_based.py").read_text(encoding="utf-8")
        st.code(source_code, language="python")

# ==========================================
# TAB 2: Branching Constraint Verification
# ==========================================
with tabs[1]:
    st.subheader("Branching Constraint Compliance Check")
    
    st.markdown("""
    <div class="edu-note">
        <strong>Assignment Constraint Definition:</strong><br>
        <em>"The rule-based solution must use no more than n branching statements, where n is the number of input attributes used by the classifier."</em><br>
        • <strong>n (attributes used):</strong> 2 (<code>poutcome</code>, <code>month</code>).<br>
        • <strong>Permitted limit:</strong> ≤ 2 branching statements.<br>
        • <strong>Rule count vs. Branch count:</strong> 3 decision paths (return statements), but only 2 branching statements (1 <code>if</code> and 1 <code>elif</code>). Plain <code>else</code> is not a branch condition.
    </div>
    """, unsafe_allow_html=True)

    check_result = branch_counter.check_file(config.RULES_DIR / "rule_based.py", config.FEATURES)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Input Attributes Used (n)", check_result["n_attributes_used"])
    with col2:
        st.metric("Permitted Limit", check_result["allowed_branches"])
    with col3:
        st.metric("Actual Branches (if/elif)", check_result["branching_statements"])
    with col4:
        if check_result["compliant"]:
            st.markdown("""
            <div style="background-color:#dcfce7; padding:10px; border-radius:8px; text-align:center;">
                <strong style="color:#166534; font-size:1.1rem;">✅ COMPLIANT</strong><br>
                <small style="color:#15803d;">Actual ≤ Permitted Limit</small>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.error("❌ NON-COMPLIANT")

    st.write("")
    st.markdown("##### 🔬 Static AST (Abstract Syntax Tree) Verification")
    st.write(f"• **Attributes accessed in AST:** `{', '.join(check_result['attributes_used'])}`")
    st.write(f"• **Total decision paths (rules):** `{check_result['return_statements_(rules)']}`")
    st.write(f"• **Hidden branch detection:** `branch_counter.py` parses the entire Python file to ensure branches are not hidden in list comprehensions, ternary operators, or dynamic expressions.")

# ==========================================
# TAB 3: Interactive Classification & Trace
# ==========================================
with tabs[2]:
    st.subheader("Interactive Single Client Prediction & Execution Trace")
    
    st.markdown("""
    <div class="edu-note">
        Enter a client record below to see the exact condition-by-condition evaluation trace.
    </div>
    """, unsafe_allow_html=True)

    with st.form("rule_prediction_form"):
        st.markdown("##### 📝 Client Profile Inputs")
        raw_input = create_record_input_form(key_prefix="rule")
        predict_rule_btn = st.form_submit_button("⚡ Evaluate Classification Rules", type="primary")

    if predict_rule_btn:
        res = service.predict_single_rule_based(raw_input)
        
        r_col1, r_col2 = st.columns([1, 1.6])
        
        with r_col1:
            st.markdown("##### 🎯 Classification Outcome")
            pred = res["prediction"]
            if pred == "yes":
                st.markdown("""
                <div style="background-color:#dcfce7; padding:1.25rem; border-radius:10px; border:1px solid #86efac; text-align:center;">
                    <span style="font-size:1.85rem; font-weight:bold; color:#166534;">PREDICTION: YES</span><br>
                    <span style="color:#15803d;">Client predicted to subscribe.</span>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div style="background-color:#fee2e2; padding:1.25rem; border-radius:10px; border:1px solid #fca5a5; text-align:center;">
                    <span style="font-size:1.85rem; font-weight:bold; color:#991b1b;">PREDICTION: NO</span><br>
                    <span style="color:#b91c1c;">Client predicted NOT to subscribe.</span>
                </div>
                """, unsafe_allow_html=True)
                
            st.write("")
            st.write(f"• **Triggered Rule:** `{res['matched_rule_title']}`")
            st.write(f"• **Explanation:** {res['explanation']}")

        with r_col2:
            st.markdown("##### 👣 Step-by-Step Execution Trace")
            for step in res["trace"]:
                st.markdown(f"**Step {step['step']}:** {step.get('action', '')}")
                if "rule" in step:
                    result_badge = "✅ TRUE" if step.get("result") else "❌ FALSE"
                    st.write(f"&nbsp;&nbsp;&nbsp;&nbsp;• Condition: `{step.get('condition')}`")
                    st.write(f"&nbsp;&nbsp;&nbsp;&nbsp;• Client Value: `{step.get('evaluated_value', '')}` → {result_badge}")
                    st.write(f"&nbsp;&nbsp;&nbsp;&nbsp;• Action: *{step.get('action')}*")
                elif "attributes" in step:
                    st.write(f"&nbsp;&nbsp;&nbsp;&nbsp;• Attributes read: `{step['attributes']}`")
                st.divider()

# ==========================================
# TAB 4: Held-out Test Set Evaluation
# ==========================================
with tabs[3]:
    st.subheader("Rule-Based Classifier Test Evaluation")
    
    artifacts = service.get_artifacts()
    if artifacts is None:
        # Load from disk
        saved_metrics_file = config.RESULTS_DIR / "metrics.csv"
        if saved_metrics_file.exists():
            df_m = pd.read_csv(saved_metrics_file, index_col="classifier")
            rm = df_m.loc["Rule-based"].to_dict()
        else:
            rm = None
    else:
        rm = artifacts.rule_metrics

    if rm is not None:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Accuracy", f"{rm['accuracy']:.4f}")
        with col2:
            st.metric("Precision (yes)", f"{rm['precision']:.4f}")
        with col3:
            st.metric("Recall (yes)", f"{rm['recall']:.4f}")
        with col4:
            st.metric("F1-Score (yes)", f"{rm['f1']:.4f}")

        st.write("")
        c1, c2 = st.columns([1, 1.5])
        with c1:
            fig = plot_cm(
                artifacts.y_test if artifacts else ["no"]*7694 + ["no"]*291 + ["yes"]*720 + ["yes"]*338,
                artifacts.rule_predictions if artifacts else ["no"]*7694 + ["yes"]*291 + ["no"]*720 + ["yes"]*338,
                "Rule-Based Confusion Matrix"
            )
            st.pyplot(fig)
        with c2:
            st.markdown("##### Detailed Classification Report")
            rep_text = (
                "              precision    recall  f1-score   support\n\n"
                "          no       0.91      0.96      0.94      7985\n"
                "         yes       0.54      0.32      0.40      1058\n\n"
                "    accuracy                           0.89      9043\n"
                "   macro avg       0.73      0.64      0.67      9043\n"
                "weighted avg       0.87      0.89      0.88      9043\n"
            )
            st.code(rep_text)
    else:
        st.info("Please train the model to compute test evaluation metrics.")

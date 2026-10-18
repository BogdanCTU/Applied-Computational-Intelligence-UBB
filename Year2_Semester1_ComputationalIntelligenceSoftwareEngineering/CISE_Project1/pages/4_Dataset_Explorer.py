"""PAGE 4: DATASET EXPLORER

Interactive exploration of the UCI Bank Marketing dataset:
previews, data types, missing value analysis, target distribution,
feature inspection, and comparison of raw vs. transformed values.
"""

import pandas as pd
import streamlit as st

from src import config
from src.model_service import ModelService, model_service
from src.ui_helpers import apply_custom_styles, init_session_state, render_sidebar_info

st.set_page_config(
    page_title="Dataset Explorer | CISE Project",
    page_icon="🔍",
    layout="wide"
)

init_session_state()
apply_custom_styles()
render_sidebar_info()

service: ModelService = st.session_state["service"]

st.markdown("""
<div class="hero-card">
    <h1>🔍 Dataset Explorer: UCI Bank Marketing</h1>
    <p>Comprehensive inspection of raw records, data distributions, missing value markers, and transformed feature states.</p>
</div>
""", unsafe_allow_html=True)

df = service.get_raw_dataset()

# Top metric summary
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric("Total Records", f"{len(df):,}")
with m2:
    st.metric("Total Columns", f"{df.shape[1]}")
with m3:
    st.metric("Target Variable", f"'{config.TARGET}' (binary)")
with m4:
    st.metric("Excluded Attribute", f"'{config.EXCLUDED_FEATURES[0]}'")

st.divider()

# Tabs for structured exploration
tabs = st.tabs([
    "📋 Raw Dataset Preview",
    "🎯 Target Distribution ('y')",
    "📊 Single Feature Deep-Dive",
    "🔄 Raw vs. Discretized Representation",
    "❓ Missing & Special Values Analysis"
])

# ==========================================
# TAB 1: Preview
# ==========================================
with tabs[0]:
    st.subheader("Dataset Records Preview")
    st.caption("Showing 100 randomly sampled rows from the raw Bank Marketing dataset.")
    st.dataframe(df.sample(100, random_state=42), height=350, use_container_width=True)

    st.markdown("##### Attribute Data Types & Unique Values Count")
    meta_df = pd.DataFrame({
        "Attribute": df.columns,
        "Data Type": [str(df[col].dtype) for col in df.columns],
        "Non-Null Count": [int(df[col].notna().sum()) for col in df.columns],
        "Unique Values": [df[col].nunique() for col in df.columns],
        "Role": ["Target" if c == config.TARGET else ("Excluded (Leakage)" if c in config.EXCLUDED_FEATURES else "Input Feature") for c in df.columns]
    })
    st.dataframe(meta_df, use_container_width=True)

# ==========================================
# TAB 2: Target Distribution
# ==========================================
with tabs[1]:
    st.subheader("Target Variable ('y') Class Imbalance")
    counts = df[config.TARGET].value_counts()
    percentages = df[config.TARGET].value_counts(normalize=True) * 100

    col1, col2 = st.columns([1, 1.2])
    with col1:
        dist_df = pd.DataFrame({
            "Target Class": counts.index,
            "Count": counts.values,
            "Percentage (%)": percentages.values.round(2)
        })
        st.dataframe(dist_df, use_container_width=True)
        st.markdown("""
        <div class="edu-note">
            <strong>Severe Class Imbalance:</strong><br>
            Only <strong>11.7%</strong> of clients subscribed to the term deposit (5,289 clients).<br>
            The majority (<strong>88.3%</strong>, 39,922 clients) said 'no'.<br>
            This makes metrics like Precision and Recall essential, because a naive model predicting 'no' for all instances achieves 88.3% accuracy without learning any patterns.
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.bar_chart(counts)

# ==========================================
# TAB 3: Feature Deep-Dive
# ==========================================
with tabs[2]:
    st.subheader("Interactive Feature Distribution")
    feature_to_inspect = st.selectbox(
        "Choose an attribute to analyze:",
        config.FEATURES + ["duration"],
        index=0
    )

    series = df[feature_to_inspect]
    c1, c2 = st.columns([1, 1.5])

    with c1:
        st.markdown(f"##### Summary for `{feature_to_inspect}`")
        if pd.api.types.is_numeric_dtype(series):
            desc = series.describe().round(2).to_dict()
            st.json(desc)
        else:
            val_counts = series.value_counts()
            val_pct = (series.value_counts(normalize=True) * 100).round(1)
            cat_df = pd.DataFrame({"Count": val_counts, "Percentage (%)": val_pct})
            st.dataframe(cat_df, use_container_width=True)

    with c2:
        st.markdown(f"##### Distribution Plot: `{feature_to_inspect}`")
        if pd.api.types.is_numeric_dtype(series):
            # Hist / bar for numeric
            hist_counts, bin_edges = pd.cut(series, bins=20, retbins=True)
            st.bar_chart(hist_counts.value_counts(sort=False))
        else:
            st.bar_chart(series.value_counts())

    st.write("")
    st.markdown(f"##### Subscription Rate ('yes') by `{feature_to_inspect}`")
    grp = df.groupby(feature_to_inspect)[config.TARGET].apply(lambda s: (s == "yes").mean() * 100).round(2)
    st.bar_chart(grp)

# ==========================================
# TAB 4: Raw vs. Discretized
# ==========================================
with tabs[3]:
    st.subheader("Raw Data vs. Discrete Preprocessed Representation")
    st.markdown("""
    <div class="edu-note">
        <strong>Why Discretize?</strong><br>
        Exact Bayesian Networks using <code>DiscreteBayesianNetwork</code> require categorical states.<br>
        Continuous numerical attributes (age, balance, day, campaign, pdays, previous) are binned using quantile cuts computed on the <strong>training set only</strong>.<br>
        The table below shows how raw values are mapped to discrete states.
    </div>
    """, unsafe_allow_html=True)

    artifacts = service.get_artifacts()
    if artifacts is not None:
        sample_raw = artifacts.X_test.head(10)
        sample_disc = artifacts.preprocessor.transform(sample_raw)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("##### 📄 Raw Test Features")
            st.dataframe(sample_raw[["age", "balance", "month", "poutcome", "campaign"]], use_container_width=True)
        with c2:
            st.markdown("##### 🔲 Discretized Bayesian Network Input")
            st.dataframe(sample_disc[["age", "balance", "month", "poutcome", "campaign"]], use_container_width=True)
    else:
        st.info("Train the model in Page 2 or Overview to inspect the active fitted preprocessor.")

# ==========================================
# TAB 5: Missing & Special Values
# ==========================================
with tabs[4]:
    st.subheader("Missing Value Markers & Special Numerical Codes")
    
    st.markdown("""
    <div class="edu-warning">
        <strong>Domain Anomalies & Encodings:</strong><br>
        1. <strong>No standard <code>NaN</code> / null values:</strong> The raw CSV contains zero formal null entries.<br>
        2. <strong>'unknown' string marker:</strong> Several attributes encode missing values as the literal string <code>'unknown'</code>.<br>
        3. <strong><code>pdays = -1</code>:</strong> In 81.7% of records, <code>pdays == -1</code> indicates the client was never contacted before.<br>
        4. <strong>Negative bank balances:</strong> 3,766 clients have negative bank balances (overdrafts).
    </div>
    """, unsafe_allow_html=True)

    unknown_summary = []
    for col in config.CATEGORICAL_FEATURES:
        n_unk = int((df[col] == "unknown").sum())
        if n_unk > 0:
            unknown_summary.append({
                "Attribute": col,
                "Count of 'unknown'": n_unk,
                "Percentage of Dataset": f"{n_unk / len(df):.2%}"
            })
    st.table(pd.DataFrame(unknown_summary))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from validator_engine import DataQualityValidator

st.set_page_config(
    page_title="DataOps Agent - Quality & Schema Drift Validator",
    page_icon="🛡️",
    layout="wide"
)

# Header branding
st.markdown("""
    <div style="background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%); padding: 20px; border-radius: 12px; border: 1px solid #312e81; margin-bottom: 25px;">
        <h1 style="color: #38bdf8; margin: 0 0 6px 0; font-size: 26px;">
            🛡️ Production Data Quality & Schema Drift Validator
        </h1>
        <p style="color: #94a3b8; margin: 0; font-size: 14px;">
            Automated Auditing Engine for Snowflake, Databricks & Cloud Data Lakehouses
        </p>
    </div>
""", unsafe_allow_html=True)

def load_sample_datasets():
    np.random.seed(42)
    n = 2000

    # Baseline (Gold/Silver Table)
    baseline_df = pd.DataFrame({
        "order_id": [f"ORD_{1000 + i}" for i in range(n)],
        "customer_id": np.random.randint(100, 999, size=n),
        "amount": np.round(np.random.uniform(10.0, 500.0, size=n), 2),
        "payment_status": np.random.choice(["SUCCESS", "PENDING", "FAILED"], p=[0.85, 0.10, 0.05], size=n),
        "created_at": pd.date_range("2026-10-01", periods=n, freq="min")
    })

    # Drifting Current Batch
    current_df = baseline_df.copy()
    current_df["amount"] = current_df["amount"].astype(str)  # Type mismatch
    current_df.drop(columns=["payment_status"], inplace=True)  # Dropped column
    current_df["promo_code"] = np.random.choice(["SAVE10", "WELCOME", None], size=n)  # New column
    current_df.loc[0:200, "customer_id"] = np.nan  # Null spike

    return baseline_df, current_df

tab1, tab2 = st.tabs(["🚀 Live Interactive Audit", "⚙️ Data Source Config"])

with tab2:
    st.subheader("Data Warehouse Connection")
    data_mode = st.radio("Select Input Mode:", ["Use Simulated Snowflake/Databricks Feed", "Upload Custom CSVs"])

baseline_df, current_df = load_sample_datasets()

with tab1:
    validator = DataQualityValidator(baseline_df, current_df)
    score = validator.compute_health_score()
    drift = validator.check_schema_drift()
    null_spikes = validator.check_null_spikes()
    volume = validator.check_volume_anomalies()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Pipeline Health Score", f"{score} / 100", delta="-20% (Drift Detected)" if score < 100 else "Optimal")
    with col2:
        st.metric("Total Records Analyzed", f"{volume['current_rows']:,}", f"{volume['pct_change']}% change")
    with col3:
        st.metric("Missing Columns", f"{len(drift['missing_columns'])}", delta="Critical Alert" if drift['missing_columns'] else "Safe", delta_color="inverse")
    with col4:
        st.metric("Type Mismatches", f"{len(drift['type_mismatches'])}", delta="Schema Break" if drift['type_mismatches'] else "None", delta_color="inverse")

    st.markdown("---")

    left_col, right_col = st.columns([1.2, 1])

    with left_col:
        st.subheader("⚠️ Schema Drift Analysis")
        if drift["has_drift"]:
            if drift["missing_columns"]:
                st.error(f"❌ **Missing Columns (Downstream Impact):** `{', '.join(drift['missing_columns'])}`")
            if drift["type_mismatches"]:
                for c, t in drift["type_mismatches"].items():
                    st.warning(f"⚠️ **Type Mismatch on `{c}`:** Expected `{t['expected']}`, Received `{t['actual']}`")
            if drift["new_columns"]:
                st.info(f"ℹ️ **New Unmapped Columns:** `{', '.join(drift['new_columns'])}`")
        else:
            st.success("✓ Zero schema drift detected against production baseline.")

        st.subheader("💧 Null Rate Deviation Anomalies")
        if null_spikes:
            null_df = pd.DataFrame(null_spikes)
            st.dataframe(null_df, use_container_width=True)
        else:
            st.success("✓ Null rates within normal baseline tolerance limits.")

    with right_col:
        st.subheader("📊 Distribution & Volume Overview")
        fig = px.bar(
            x=["Baseline Count", "Current Batch"],
            y=[volume["baseline_rows"], volume["current_rows"]],
            color=["Baseline", "Current"],
            title="Batch Volume Comparison",
            labels={"x": "Batch", "y": "Rows"}
        )
        fig.update_layout(height=280, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("""
            <div style="background-color: #1e293b; padding: 15px; border-radius: 8px; border-left: 4px solid #38bdf8;">
                <h4 style="margin: 0 0 5px 0; color: #f8fafc;">Consultant Executive Assessment</h4>
                <p style="font-size: 13px; color: #94a3b8; margin: 0;">
                    High-priority structural failure detected. Recommending quarantine of the current batch to prevent downstream analytics corruption in the presentation layer.
                </p>
            </div>
        """, unsafe_allow_html=True)
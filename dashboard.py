import streamlit as st
import pandas as pd
from supabase import create_client, Client
import os
from dotenv import load_dotenv

# Institutional Config
load_dotenv()
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

st.set_page_config(page_title="Carrier Alpha Treasury", layout="wide", initial_sidebar_state="collapsed")

# Consolidated UI Styling
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 38px; color: #facc15; }
    .stDataFrame { border: 1px solid #374151; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Carrier Alpha Treasury")
st.caption("Sovereign Ledger | Live Connection")

def fetch_consolidated_ledger():
    # FIXED QUERY: Pulls from audit_results and explicitly joins shipment data
    res = supabase.table("audit_results").select("*, shipments(*)").execute()
    return pd.json_normalize(res.data)

try:
    df = fetch_consolidated_ledger()

    # --- 1. CONSOLIDATED KPI TIER ---
    col1, col2, col3, col4 = st.columns(4)
    
    # Detected Leakage: Sum of variance_amount where eligible
    leakage = df[df['is_eligible'] == True]['variance_amount'].sum()
    # Claimable Events: Count of eligible rows
    events = len(df[df['is_eligible'] == True])
    
    with col1:
        st.metric("DETECTED LEAKAGE", f"${leakage:,.2f}", help="Total capital identified for recovery")
        st.caption("↑ Recoverable")
    with col2:
        st.metric("CLAIMABLE EVENTS", f"{events}", help="Number of distinct service failures")
        st.caption("↑ Actionable Items")
    with col3:
        st.metric("AUDIT VELOCITY", "Real-time", delta="Active")
        st.caption("↑ Active")
    with col4:
        st.metric("LAST SYNC", "15:16:39", delta="UTC")
        st.caption("↑ UTC")

    st.divider()

    # --- 2. ACTIONABLE ROADMAP (Active Disputes) ---
    st.subheader("📍 Active Disputes")
    
    if not df.empty:
        # Clean data for institutional display
        roadmap = df[df['is_eligible'] == True][[
            "shipments.tracking_number", 
            "shipments.carrier", 
            "shipments.service_type",
            "variance_amount",
            "failure_reason"
        ]].copy()
        
        roadmap.columns = ["Tracking Asset", "Carrier", "Service", "Leakage ($)", "Detected Failure"]
        
        st.dataframe(roadmap, use_container_width=True, hide_index=True)
        
        if st.button("⬇️ Download Claim Artifact (CSV)"):
            roadmap.to_csv("carrier_alpha_claims.csv", index=False)
            st.success("Artifact generated for portal upload.")

    # --- 3. RAW DATA DRILLDOWN ---
    with st.expander("🔍 View Raw Ledger Data"):
        st.write(df)

except Exception as e:
    st.error(f"Ledger Sync Error: {e}")
    st.info("Ensure Supabase columns match the updated Python schema.")
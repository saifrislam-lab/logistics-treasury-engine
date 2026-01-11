import streamlit as st
import pandas as pd
from supabase import create_client, Client
import os
from dotenv import load_dotenv
import time

# --- CONFIGURATION ---
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("❌ API Keys missing. Please check .env file.")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- PAGE SETUP ---
st.set_page_config(
    page_title="Carrier Alpha | Treasury",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CUSTOM CSS (Institutional Dark Mode) ---
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    div[data-testid="stMetricValue"] { font-size: 2.8rem !important; color: #F4D03F !important; }
    .stDataFrame { border: 1px solid #30363d; border-radius: 5px; }
    </style>
""", unsafe_allow_html=True)

def fetch_treasury_data():
    """Fetches Shipments + Audit Results joined."""
    # 1. Fetch Audit Results (The Money)
    audit_response = supabase.table("audit_results").select("*").execute()
    audits = pd.DataFrame(audit_response.data)
    
    if audits.empty:
        return pd.DataFrame()

    # 2. Fetch Shipments (The Context)
    ship_response = supabase.table("shipments").select("*").execute()
    shipments = pd.DataFrame(ship_response.data)
    
    # 3. Merge on shipment_id
    if not shipments.empty:
        merged = pd.merge(
            audits, 
            shipments, 
            left_on='shipment_id', 
            right_on='id', 
            suffixes=('_audit', '_ship')
        )
        return merged
    return audits

# --- HEADER ---
c1, c2 = st.columns([4, 1])
with c1:
    st.title("🛡️ Carrier Alpha Treasury")
    st.caption("Sovereign Ledger | Live Connection")
with c2:
    if st.button("🔄 Refresh Ledger"):
        st.rerun()

# --- DATA LOADING ---
with st.spinner("Accessing Vault..."):
    df = fetch_treasury_data()

if df.empty:
    st.warning("Vault is empty. Run 'python3 loader.py' to ingest data.")
    st.stop()

# --- METRICS LAYER ---
# Calculate Leakage
total_leakage = df['variance_amount'].sum()
leakage_count = df[df['variance_amount'] > 0].shape[0]
latest_audit = pd.to_datetime(df['audited_at']).max().strftime("%H:%M:%S")

st.markdown("---")
m1, m2, m3, m4 = st.columns(4)

m1.metric("DETECTED LEAKAGE", f"${total_leakage:,.2f}", "Recoverable")
m2.metric("CLAIMABLE EVENTS", f"{leakage_count}", "Actionable Items")
m3.metric("AUDIT VELOCITY", "Real-time", "Active")
m4.metric("LAST SYNC", latest_audit, "UTC")

# --- ACTION LAYER ---
st.markdown("### 📍 Active Disputes")

# Clean up dataframe for display
display_df = df[df['variance_amount'] > 0].copy()

if not display_df.empty:
    # Select only readable columns
    grid_data = display_df[[
        'tracking_number', 
        'carrier', 
        'service_type', 
        'variance_amount', 
        'failure_reason', 
        'audited_at'
    ]]
    
    # Rename for professional look
    grid_data.columns = ['Tracking Asset', 'Carrier', 'Service', 'Leakage ($)', 'Detected Failure', 'Timestamp']

    st.dataframe(
        grid_data,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Leakage ($)": st.column_config.NumberColumn(format="$%.2f"),
            "Timestamp": st.column_config.DatetimeColumn(format="D MMM, HH:mm")
        }
    )
    
    # Export Button
    csv = grid_data.to_csv(index=False).encode('utf-8')
    st.download_button(
        "⬇️ Download Claim Artifact (CSV)",
        csv,
        "carrier_alpha_claims.csv",
        "text/csv",
        key='download-csv'
    )

else:
    st.info("No leakage detected. Carrier performance is 100% (or no data loaded).")

# --- DEBUG EXPANDER ---
with st.expander("🔍 View Raw Ledger Data"):
    st.dataframe(df)
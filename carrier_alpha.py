import streamlit as st
import pandas as pd
from supabase import create_client, Client

# --- CONFIGURATION ---
SUPABASE_URL = "https://zclwtzzzdzrjoxqkklyt.supabase.co"
SUPABASE_KEY = "REPLACE_WITH_ENV_OR_SECRET_MANAGER"  # <-- keep your existing approach
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Carrier Alpha | Treasury", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; }
    </style>
""", unsafe_allow_html=True)

def load_truth_view() -> pd.DataFrame:
    """
    Canonical source of truth: public.v_audit_truth
    """
    resp = supabase.table("v_audit_truth").select("*").execute()
    return pd.DataFrame(resp.data) if resp.data else pd.DataFrame()

def generate_fedex_dispute_csv(df: pd.DataFrame) -> bytes:
    """
    Minimal FedEx portal artifact (v1).
    Source rows: claims in DRAFT state (from v_audit_truth).
    """
    out = df[['tracking_number', 'claim_amount']].copy()
    out.columns = ['Tracking ID', 'Dispute Amount']
    out['Dispute Type'] = '5'  # FedEx Service Failure
    out['Comments'] = 'Guaranteed Service Refund - Late'
    return out.to_csv(index=False).encode("utf-8")

# --- HEADER ---
st.title("🛡️ Carrier Alpha")
st.caption("Institutional Logistics Treasury Terminal")

df = load_truth_view()

if df.empty:
    st.warning("Vault empty. No records found in v_audit_truth.")
    st.stop()

# Normalize for safety
df['total_charged'] = pd.to_numeric(df.get('total_charged', 0), errors='coerce').fillna(0)
df['variance_amount'] = pd.to_numeric(df.get('variance_amount', 0), errors='coerce').fillna(0)
df['claim_amount'] = pd.to_numeric(df.get('claim_amount', 0), errors='coerce').fillna(0)
df['recovery_amount'] = pd.to_numeric(df.get('recovery_amount', 0), errors='coerce').fillna(0)

# --- KPI LAYER (Treasury Metrics) ---
total_spend = df['total_charged'].sum()

# Eligible refundable delta (from audit ledger)
total_refundable = df[df['is_eligible'] == True]['variance_amount'].sum()

# Lifecycle buckets (claims-led)
draft_df = df[df['claim_status'] == 'DRAFT']
submitted_df = df[df['claim_status'] == 'SUBMITTED']
disputed_df = df[df['claim_status'] == 'DISPUTED']
recovered_df = df[df['claim_status'] == 'RECOVERED']
denied_df = df[df['claim_status'] == 'DENIED']

draft_val = draft_df['claim_amount'].sum()
submitted_val = submitted_df['claim_amount'].sum()
disputed_val = disputed_df['claim_amount'].sum()
recovered_val = recovered_df['recovery_amount'].sum()
denied_val = denied_df['claim_amount'].sum()

leakage_rate = (total_refundable / total_spend * 100) if total_spend > 0 else 0.0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Analyzed Spend", f"${total_spend:,.2f}")
c2.metric("Refundable Delta", f"${total_refundable:,.2f}", delta=f"{leakage_rate:.2f}% leakage", delta_color="inverse")
c3.metric("In Progress", f"${(submitted_val + disputed_val):,.2f}", delta="Submitted+Disputed", delta_color="off")
c4.metric("Recovered", f"${recovered_val:,.2f}", delta="Credited", delta_color="normal")

st.divider()

# --- RECOVERY ROADMAP (Claims-led operational table) ---
st.write("### 📍 Recovery Roadmap (Claims Lifecycle)")

roadmap = df[df['claim_status'].isin(['DRAFT', 'SUBMITTED', 'DISPUTED', 'RECOVERED', 'DENIED'])].copy()
roadmap_cols = [
    'carrier', 'tracking_number', 'service_type',
    'promised_delivery', 'actual_delivery',
    'is_eligible', 'variance_amount',
    'claim_status', 'claim_amount', 'recovery_amount',
    'failure_reason', 'rule_id',
    'timezone_assumption', 'timezone_confidence',
    'exception_category', 'exception_signal',
    'carrier_case_number'
]
roadmap_cols = [c for c in roadmap_cols if c in roadmap.columns]

st.dataframe(
    roadmap[roadmap_cols].sort_values(by=['claim_status'], ascending=True),
    use_container_width=True
)

st.divider()

# --- EXECUTION: Export DRAFT claims for FedEx (v1) ---
st.write("### ⚡ Execution")

if not draft_df.empty:
    st.warning(f"⚠️ {len(draft_df)} DRAFT claims ready for export (${draft_val:,.2f}).")

    csv_data = generate_fedex_dispute_csv(draft_df)
    st.download_button(
        label="⬇️ Download FedEx Dispute Artifact (.csv)",
        data=csv_data,
        file_name=f"fedex_dispute_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        help="Upload this CSV to FedEx Billing Online to initiate disputes."
    )
else:
    st.info("No DRAFT claims ready for export.")

st.divider()

# --- FULL LEDGER (Truth view) ---
with st.expander("View Full Canonical Ledger (v_audit_truth)"):
    st.dataframe(df, use_container_width=True)

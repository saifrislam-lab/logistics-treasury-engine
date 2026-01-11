import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime, timezone

# --- CONFIGURATION ---
SUPABASE_URL = "https://zclwtzzzdzrjoxqkklyt.supabase.co"
SUPABASE_KEY = "REPLACE_WITH_ENV_OR_SECRET_MANAGER"  # keep your existing approach
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Carrier Alpha | Treasury", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; }
    </style>
""", unsafe_allow_html=True)

def load_truth_view() -> pd.DataFrame:
    resp = supabase.table("v_audit_truth").select("*").execute()
    return pd.DataFrame(resp.data) if resp.data else pd.DataFrame()

def generate_fedex_dispute_csv(df: pd.DataFrame) -> bytes:
    out = df[['tracking_number', 'claim_amount']].copy()
    out.columns = ['Tracking ID', 'Dispute Amount']
    out['Dispute Type'] = '5'
    out['Comments'] = 'Guaranteed Service Refund - Late'
    return out.to_csv(index=False).encode("utf-8")

def mark_claims_submitted(claim_ids: list[str]) -> None:
    if not claim_ids:
        return
    now_iso = datetime.now(timezone.utc).isoformat()
    for cid in claim_ids:
        supabase.table("claims").update({
            "status": "SUBMITTED",
            "submitted_at": now_iso
        }).eq("id", cid).execute()

def reconcile_claim(claim_id: str, status: str, carrier_case_number: str | None, recovery_amount: float | None) -> None:
    """
    Minimal operator reconciliation:
    - Set status to RECOVERED or DENIED
    - Set settled_at
    - Set recovery_amount for RECOVERED
    - Optionally set carrier_case_number
    """
    if status not in ["RECOVERED", "DENIED"]:
        raise ValueError("Invalid reconciliation status")

    now_iso = datetime.now(timezone.utc).isoformat()
    payload = {
        "status": status,
        "settled_at": now_iso
    }

    if carrier_case_number:
        payload["carrier_case_number"] = carrier_case_number.strip()

    if status == "RECOVERED":
        if recovery_amount is None:
            raise ValueError("recovery_amount required for RECOVERED")
        payload["recovery_amount"] = float(recovery_amount)

    supabase.table("claims").update(payload).eq("id", claim_id).execute()

# --- HEADER ---
st.title("🛡️ Carrier Alpha")
st.caption("Institutional Logistics Treasury Terminal")

df = load_truth_view()

if df.empty:
    st.warning("Vault empty. No records found in v_audit_truth.")
    st.stop()

# Normalize numeric columns
df['total_charged'] = pd.to_numeric(df.get('total_charged', 0), errors='coerce').fillna(0)
df['variance_amount'] = pd.to_numeric(df.get('variance_amount', 0), errors='coerce').fillna(0)
df['claim_amount'] = pd.to_numeric(df.get('claim_amount', 0), errors='coerce').fillna(0)
df['recovery_amount'] = pd.to_numeric(df.get('recovery_amount', 0), errors='coerce').fillna(0)

# --- KPI LAYER ---
total_spend = df['total_charged'].sum()
total_refundable = df[df['is_eligible'] == True]['variance_amount'].sum()

draft_df = df[df['claim_status'] == 'DRAFT']
submitted_df = df[df['claim_status'] == 'SUBMITTED']
disputed_df = df[df['claim_status'] == 'DISPUTED']
recovered_df = df[df['claim_status'] == 'RECOVERED']
denied_df = df[df['claim_status'] == 'DENIED']

draft_val = draft_df['claim_amount'].sum()
submitted_val = submitted_df['claim_amount'].sum()
disputed_val = disputed_df['claim_amount'].sum()
recovered_val = recovered_df['recovery_amount'].sum()

leakage_rate = (total_refundable / total_spend * 100) if total_spend > 0 else 0.0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Analyzed Spend", f"${total_spend:,.2f}")
c2.metric("Refundable Delta", f"${total_refundable:,.2f}", delta=f"{leakage_rate:.2f}% leakage", delta_color="inverse")
c3.metric("In Progress", f"${(submitted_val + disputed_val):,.2f}", delta="Submitted+Disputed", delta_color="off")
c4.metric("Recovered", f"${recovered_val:,.2f}", delta="Credited", delta_color="normal")

st.divider()

# --- RECOVERY ROADMAP ---
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
    'carrier_case_number',
    'claim_id'
]
roadmap_cols = [c for c in roadmap_cols if c in roadmap.columns]

st.dataframe(
    roadmap[roadmap_cols].sort_values(by=['claim_status'], ascending=True),
    use_container_width=True
)

st.divider()

# --- EXECUTION: Export & lifecycle transition ---
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

    st.caption("After you download and submit the CSV to FedEx, mark these claims as SUBMITTED.")

    if st.button("✅ Mark exported DRAFT claims as SUBMITTED"):
        claim_ids = [str(x) for x in draft_df['claim_id'].dropna().tolist()]
        mark_claims_submitted(claim_ids)
        st.success(f"Marked {len(claim_ids)} claims as SUBMITTED.")
        st.rerun()

else:
    st.info("No DRAFT claims ready for export.")

st.divider()

# --- RECONCILIATION (Operator) ---
st.write("### 🧾 Reconciliation (Operator)")

with st.form("reconcile_form"):
    claim_id = st.text_input("Claim ID (UUID)", help="Copy claim_id from the Recovery Roadmap table above.")
    new_status = st.selectbox("Set Status", ["RECOVERED", "DENIED"])
    carrier_case_number = st.text_input("Carrier Case Number (optional)")
    recovery_amount = None
    if new_status == "RECOVERED":
        recovery_amount = st.number_input("Recovered Amount ($)", min_value=0.0, value=0.0, step=0.01)

    submitted = st.form_submit_button("Apply Reconciliation")

    if submitted:
        try:
            if not claim_id.strip():
                st.error("Claim ID is required.")
            else:
                reconcile_claim(
                    claim_id=claim_id.strip(),
                    status=new_status,
                    carrier_case_number=carrier_case_number.strip() if carrier_case_number else None,
                    recovery_amount=recovery_amount if new_status == "RECOVERED" else None
                )
                st.success(f"Claim {claim_id.strip()} updated to {new_status}.")
                st.rerun()
        except Exception as e:
            st.error(str(e))

st.divider()

with st.expander("View Full Canonical Ledger (v_audit_truth)"):
    st.dataframe(df, use_container_width=True)

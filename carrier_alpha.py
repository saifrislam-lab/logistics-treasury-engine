import os
import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime, timezone
from typing import Optional, List

# =========================
# Carrier Alpha — Treasury Platform UI
# Category: Logistics Treasury Intelligence
# =========================

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Missing SUPABASE_URL or SUPABASE_KEY environment variables.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Carrier Alpha | Treasury Platform", layout="wide")

st.markdown("""
<style>
.main { background-color: #0e1117; color: white; }
.stMetric { background-color: #161b22; border: 1px solid #30363d; }
.small-muted { color: #9aa4af; font-size: 0.9rem; }
.section-title { margin-top: 0.25rem; }
</style>
""", unsafe_allow_html=True)

# -------------------------
# Data access (canonical truth)
# -------------------------
def load_truth_view() -> pd.DataFrame:
    """
    Canonical source of truth: public.v_audit_truth
    This is the Treasury Platform’s read model.
    """
    resp = supabase.table("v_audit_truth").select("*").execute()
    return pd.DataFrame(resp.data) if resp.data else pd.DataFrame()

# -------------------------
# Artifact export (v1)
# -------------------------
def generate_fedex_dispute_csv(df: pd.DataFrame) -> bytes:
    """
    Minimal FedEx portal artifact (v1).
    Inputs: DRAFT claims from v_audit_truth.
    """
    out = df[['tracking_number', 'claim_amount']].copy()
    out.columns = ['Tracking ID', 'Dispute Amount']
    out['Dispute Type'] = '5'
    out['Comments'] = 'Guaranteed Service Refund - Late'
    return out.to_csv(index=False).encode("utf-8")

# -------------------------
# Lifecycle actions (v1)
# -------------------------
def mark_claims_submitted(claim_ids: List[str]) -> None:
    if not claim_ids:
        return
    now_iso = datetime.now(timezone.utc).isoformat()
    for cid in claim_ids:
        supabase.table("claims").update({
            "status": "SUBMITTED",
            "submitted_at": now_iso
        }).eq("id", cid).execute()

def reconcile_claim(
    claim_id: str,
    status: str,
    carrier_case_number: Optional[str],
    recovery_amount: Optional[float]
) -> None:
    """
    Settlement & reconciliation (v1):
    - RECOVERED: write recovery_amount + settled_at
    - DENIED: write settled_at
    """
    if status not in ["RECOVERED", "DENIED"]:
        raise ValueError("Invalid reconciliation status")

    now_iso = datetime.now(timezone.utc).isoformat()
    payload = {"status": status, "settled_at": now_iso}

    if carrier_case_number:
        payload["carrier_case_number"] = carrier_case_number.strip()

    if status == "RECOVERED":
        if recovery_amount is None:
            raise ValueError("Recovered Amount is required for RECOVERED")
        payload["recovery_amount"] = float(recovery_amount)

    supabase.table("claims").update(payload).eq("id", claim_id).execute()

# =========================
# UI: Header
# =========================
st.title("Carrier Alpha")
st.markdown('<div class="small-muted">Logistics Treasury Intelligence • Treasury Platform</div>', unsafe_allow_html=True)

df = load_truth_view()

if df.empty:
    st.warning("No ledger rows found. (v_audit_truth returned 0 records.)")
    st.stop()

# Normalize numeric columns safely
for col in ["total_charged", "variance_amount", "claim_amount", "recovery_amount"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
    else:
        df[col] = 0.0

# =========================
# Treasury summary metrics (executive layer)
# =========================
total_spend = float(df["total_charged"].sum())
total_refundable = float(df[df["is_eligible"] == True]["variance_amount"].sum())

draft_df = df[df["claim_status"] == "DRAFT"]
submitted_df = df[df["claim_status"] == "SUBMITTED"]
disputed_df = df[df["claim_status"] == "DISPUTED"]
recovered_df = df[df["claim_status"] == "RECOVERED"]

draft_val = float(draft_df["claim_amount"].sum())
in_progress_val = float(submitted_df["claim_amount"].sum() + disputed_df["claim_amount"].sum())
recovered_val = float(recovered_df["recovery_amount"].sum())

leakage_rate = (total_refundable / total_spend * 100.0) if total_spend > 0 else 0.0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Analyzed Spend", f"${total_spend:,.2f}")
c2.metric("Refundable Delta", f"${total_refundable:,.2f}", delta=f"{leakage_rate:.2f}% leakage", delta_color="inverse")
c3.metric("In Progress", f"${in_progress_val:,.2f}", delta="Submitted + Disputed", delta_color="off")
c4.metric("Recovered", f"${recovered_val:,.2f}", delta="Credited", delta_color="normal")

st.divider()

# =========================
# Recovery Roadmap (Claims Ledger)
# =========================
st.subheader("Recovery Roadmap")
st.markdown('<div class="small-muted">Claims ledger derived from deterministic Treasury Engine decisions.</div>', unsafe_allow_html=True)

roadmap = df[df["claim_status"].isin(["DRAFT", "SUBMITTED", "DISPUTED", "RECOVERED", "DENIED"])].copy()

# User-friendly label mapping (UI only)
LABELS = {
    "carrier": "Carrier",
    "tracking_number": "Tracking #",
    "service_type": "Service",
    "promised_delivery": "Promised",
    "actual_delivery": "Delivered",
    "claim_status": "Status",
    "claim_amount": "Claim Amount ($)",
    "recovery_amount": "Recovered ($)",
    "variance_amount": "Refundable Delta ($)",
    "failure_reason": "Finding",
    "carrier_case_number": "Carrier Case #",
    "timezone_assumption": "Time Basis",
    "timezone_confidence": "Time Confidence",
    "exception_category": "Exception Category",
    "exception_signal": "Exception Signal",
    "rule_id": "Rule ID",
    "claim_id": "Claim ID"
}

# What we show by default (clean view)
DEFAULT_COLS = [
    "carrier",
    "tracking_number",
    "service_type",
    "promised_delivery",
    "actual_delivery",
    "claim_status",
    "claim_amount",
    "recovery_amount",
    "variance_amount",
    "failure_reason",
    "carrier_case_number",
    "claim_id"
]
DEFAULT_COLS = [c for c in DEFAULT_COLS if c in roadmap.columns]

display_df = roadmap[DEFAULT_COLS].rename(columns=LABELS)

# Sort: actionable first
status_order = {"DRAFT": 0, "SUBMITTED": 1, "DISPUTED": 2, "RECOVERED": 3, "DENIED": 4}
display_df["_sort"] = display_df["Status"].map(status_order).fillna(99)
display_df = display_df.sort_values(by=["_sort"]).drop(columns=["_sort"])

st.dataframe(display_df, use_container_width=True)

with st.expander("Audit Details (evidence + rule trace)"):
    detail_cols = [
        "tracking_number",
        "rule_id",
        "timezone_assumption",
        "timezone_confidence",
        "exception_category",
        "exception_signal",
    ]
    detail_cols = [c for c in detail_cols if c in roadmap.columns]
    if detail_cols:
        st.dataframe(roadmap[detail_cols].rename(columns=LABELS), use_container_width=True)
    else:
        st.info("No audit detail fields available.")

st.divider()

# =========================
# Actions (Claim Actions)
# =========================
st.subheader("Actions")
st.markdown('<div class="small-muted">Export DRAFT claims and progress them through the lifecycle.</div>', unsafe_allow_html=True)

if not draft_df.empty:
    st.warning(f"{len(draft_df)} DRAFT claims ready for export (${draft_val:,.2f}).")

    csv_data = generate_fedex_dispute_csv(draft_df)
    st.download_button(
        label="Download FedEx Dispute CSV",
        data=csv_data,
        file_name=f"fedex_dispute_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        help="Upload to FedEx Billing Online to initiate disputes."
    )

    st.caption("After submitting to FedEx, mark exported claims as SUBMITTED.")
    if st.button("Mark exported DRAFT claims as SUBMITTED"):
        claim_ids = [str(x) for x in draft_df["claim_id"].dropna().tolist()]
        mark_claims_submitted(claim_ids)
        st.success(f"Marked {len(claim_ids)} claims as SUBMITTED.")
        st.rerun()
else:
    st.info("No DRAFT claims ready for export.")

st.divider()

# =========================
# Settlement & Reconciliation
# =========================
st.subheader("Settlement & Reconciliation")
st.markdown('<div class="small-muted">Record carrier outcomes to close the loop (RECOVERED / DENIED).</div>', unsafe_allow_html=True)

with st.form("reconcile_form"):
    claim_id = st.text_input("Claim ID", help="Copy from Recovery Roadmap.")
    new_status = st.selectbox("Outcome", ["RECOVERED", "DENIED"])
    carrier_case_number = st.text_input("Carrier Case # (optional)")

    recovery_amount = None
    if new_status == "RECOVERED":
        recovery_amount = st.number_input("Recovered Amount ($)", min_value=0.0, value=0.0, step=0.01)

    submitted = st.form_submit_button("Apply")

    if submitted:
        try:
            if not claim_id.strip():
                st.error("Claim ID is required.")
            else:
                reconcile_claim(
                    claim_id=claim_id.strip(),
                    status=new_status,
                    carrier_case_number=carrier_case_number.strip() if carrier_case_number else None,
                    recovery_amount=float(recovery_amount) if new_status == "RECOVERED" else None
                )
                st.success(f"Updated claim {claim_id.strip()} → {new_status}.")
                st.rerun()
        except Exception as e:
            st.error(str(e))

st.divider()

with st.expander("Internal Ledger View (v_audit_truth)"):
    st.dataframe(df, use_container_width=True)

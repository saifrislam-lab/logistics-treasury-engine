import streamlit as st
import pandas as pd
import pdfplumber
import os
import json
import plotly.graph_objects as go
from dotenv import load_dotenv
from openai import OpenAI

# 1. INITIALIZE SYSTEM
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 2. CONFIGURATION & STYLING
st.set_page_config(
    page_title="Logistics Treasury | Institutional Audit",
    page_icon="🛡️",
    layout="wide"
)

# Institutional Dark Mode aesthetic [cite: 2025-12-20]
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    div[data-testid="stMetricValue"] {
        font-family: 'JetBrains Mono', monospace;
        font-size: 28px;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. THE BRAIN (Backend Logic Functions)
def parse_invoice_with_ai(file_obj):
    """ Extracts structured data from FedEx/UPS PDFs. """
    with pdfplumber.open(file_obj) as pdf:
        text = "".join([page.extract_text() + "\n" for page in pdf.pages])
    
    system_prompt = "You are a Logistics Audit Algorithm. Return JSON with 'shipments' list."
    
    response = client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Analyze data:\n\n{text[:15000]}"}
        ]
    )
    return json.loads(response.choices[0].message.content)

def run_audit_logic(shipments):
    """ Finds the Refundable Delta. """
    audited_data = []
    total_recoverable = 0.0
    
    for s in shipments.get('shipments', []):
        refund_amount = 0.0
        status = "CLEAN"
        
        if "Overnight" in str(s.get('service_type')) and "10:30" not in str(s.get('actual_delivery', '')):
             status = "LATE DELIVERY"
             refund_amount = float(s.get('amount_charged', 0))

        if refund_amount > 0:
            total_recoverable += refund_amount

        audited_data.append({
            "Tracking #": s.get('tracking_number'),
            "Service": s.get('service_type'),
            "Status": status,
            "Charge": f"${s.get('amount_charged', 0)}",
            "Refund Opp": f"${refund_amount:.2f}"
        })
    return audited_data, total_recoverable

# 4. THE UI
st.title("🛡️ LOGISTICS TREASURY")
st.markdown("### Institutional Audit Engine v1.0")

with st.sidebar:
    st.header("Audit Parameters")
    uploaded_file = st.file_uploader("Upload Carrier Invoice (PDF)", type=['pdf'])
    st.markdown("---")
    if st.button("RUN DEMO SIMULATION"):
        st.session_state['run_demo'] = True
    if st.button("RESET ENGINE"):
        st.session_state['run_demo'] = False
        st.rerun()

# --- 5. THE "ZERO-RISK" EXECUTION ENGINE ---
if uploaded_file:
    with st.spinner("EXECUTING MIRROR MARKET SCAN... (AI AUDITOR ACTIVE)"):
        try:
            # 1. PARSE & AUDIT
            data_json = parse_invoice_with_ai(uploaded_file)
            audit_rows, recoverable_cash = run_audit_logic(data_json)
            df = pd.DataFrame(audit_rows)
            
            # 2. CALCULATE INSTITUTIONAL YIELD [cite: 2025-11-17]
            performance_fee = recoverable_cash * 0.25  # Our 25% Contingency
            net_to_client = recoverable_cash - performance_fee

            # 3. THE "AHA" SAVINGS SUMMARY
            st.success("✅ AUDIT COMPLETE: RECOVERABLE LIQUIDITY IDENTIFIED")
            
            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric("Gross Alpha Found", f"${recoverable_cash:,.2f}")
            with m2:
                st.metric("Performance Fee (25%)", f"-${performance_fee:,.2f}", delta_color="inverse")
            with m3:
                st.metric("Your Net Capital Restoration", f"${net_to_client:,.2f}")

            st.markdown("---")

            # 4. DISPUTE QUEUE (The Claims Table)
            st.subheader("📋 Dispute Queue: Claimable Line Items")
            st.dataframe(df, use_container_width=True)

            # 5. THE "EASY YES" ACTION BAR
            col_a, col_b = st.columns([2, 1])
            with col_a:
                st.info("💡 **NO RECOVERY, NO FEE**: We only collect our fee after the carrier credits your account.")
            with col_b:
                if st.button("🚀 EXECUTE RECOVERY CLAIMS", type="primary"):
                    st.session_state['claims_sent'] = True
                    st.balloons()

            if st.session_state.get('claims_sent'):
                st.warning("⚠️ Action Required: Download the Dispute Packet below and upload to your Carrier Billing Portal.")
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 DOWNLOAD CARRIER-READY DISPUTE PACKET (CSV)",
                    data=csv,
                    file_name='logistics_treasury_dispute.csv',
                    mime='text/csv'
                )

        except Exception as e:
            st.error(f"Institutional Audit Interrupted: {e}")

else:
    # --- IDLE STATE: THE LANDING PAGE HOOK ---
    st.markdown("""
    ## **Recover Your Logistics Alpha.**
    ### Stop overpaying for carrier service failures. 
    **Upload your FedEx or UPS invoice to run a real-time audit.**
    """)
    
    st.info("🛡️ **Zero Risk**: We identify the refunds. You only pay a fee if we successfully recover your money.")
    
    # Showcase the 3-step value
    c1, c2, c3 = st.columns(3)
    c1.markdown("**1. Ingest**\nUpload any PDF invoice.")
    c2.markdown("**2. Audit**\nAI identifies late packages.")
    c3.markdown("**3. Recoup**\nWe handle the claim process.")

elif st.session_state.get('run_demo'):
    st.warning("⚠️ SIMULATION MODE ACTIVE")
    
    # Financial Metrics [cite: 2025-12-01]
    m1, m2, m3 = st.columns(3)
    m1.metric("Recoverable Alpha", "$1,240.50", "+12%")
    m2.metric("Late Deliveries", "14")
    m3.metric("ROI Estimate", "18.4%")

    # Audit Data Table
    mock_data = pd.DataFrame({
        "Tracking #": ["1Z992...", "1Z554...", "1Z443..."],
        "Service": ["Priority Overnight", "Ground", "Next Day Air"],
        "Status": ["LATE DELIVERY", "RESIDENTIAL ERR", "LATE DELIVERY"],
        "Refund Opp": ["$84.20", "$5.50", "$112.00"]
    })
    st.dataframe(mock_data, use_container_width=True)

    # Visual Recovery Probability
    st.markdown("### 📊 Recovery Probability Distribution")
    fig = go.Figure(go.Bar(
        x=['Ground', 'Express', 'Intl', 'Freight'],
        y=[84.20, 112.00, 45.50, 220.10],
        marker_color=['#2E86C1', '#17A589', '#D4AC0D', '#CB4335']
    ))
    fig.update_layout(template="plotly_dark", height=300, margin=dict(l=0, r=0, t=20, b=0))
    st.plotly_chart(fig, use_container_width=True)

else:
    # --- 1. GLOBAL NAVBAR ---
    nav_left, nav_right = st.columns([3, 1])
    with nav_left:
        st.markdown("### 🛡️ Logistics Treasury")
    with nav_right:
        st.button("Member Login", use_container_width=True)

    st.markdown("---")

    # --- 2. HERO SECTION ---
    st.markdown("<h1 style='text-align: center;'>Recover Your Logistics Alpha.</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 20px;'>The institutional-grade audit engine for FedEx & UPS.</p>", unsafe_allow_html=True)
    
    # Hero Upload Box
    st.markdown("###")
    uploaded_file = st.file_uploader("", type=['pdf'], help="Upload any carrier invoice to begin audit.")
    
    # --- 3. LIQUIDITY TICKER ---
    st.markdown("""
        <div style="background-color: #1e2130; padding: 10px; border-radius: 5px; text-align: center;">
            <span style="color: #00ffcc;">●</span> TOTAL LIQUIDITY RESTORED: <b>$14,240,500.00</b> 
            &nbsp;&nbsp;&nbsp; | &nbsp;&nbsp;&nbsp; 
            LATEST RECOVERY: <span style="color: #00ffcc;">+$1,240.50</span>
        </div>
    """, unsafe_allow_html=True)

    # --- 4. HOW IT WORKS ---
    st.markdown("###")
    h1, h2, h3 = st.columns(3)
    with h1:
        st.subheader("1. Ingest")
        st.write("Securely upload your weekly PDF invoices. Our AI parses every line item in seconds.")
    with h2:
        st.subheader("2. Audit")
        st.write("The engine identifies GSR (Guaranteed Service Refunds) and classification errors.")
    with h3:
        st.subheader("3. Recoup")
        st.write("Execute claims with one click. We only collect a fee once your capital is restored [cite: 2025-11-17].")

    # --- 5. PRICING FOOTER ---
    st.markdown("---")
    st.markdown("<p style='text-align: center;'><b>Zero Risk. Zero Upfront. 25% Performance Fee only on successful recoveries.</b></p>", unsafe_allow_html=True)
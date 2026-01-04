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

# 5. MAIN EXECUTION FLOW
if uploaded_file:
    with st.spinner("Executing Mirror Market Scan..."):
        try:
            data_json = parse_invoice_with_ai(uploaded_file)
            audit_rows, recoverable_cash = run_audit_logic(data_json)
            df = pd.DataFrame(audit_rows)
            st.metric("Recoverable Alpha", f"${recoverable_cash:.2f}")
            st.dataframe(df, use_container_width=True)
        except Exception as e:
            st.error(f"Error: {e}")

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
    st.info("Awaiting Input... Initialize scan to find Profit Leakage.")
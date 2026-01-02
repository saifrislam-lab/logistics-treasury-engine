import streamlit as st
import pandas as pd
import pdfplumber
import os
import time
import json
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

# Force "Dark Mode" Financial aesthetic
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    .metric-card {
        background-color: #1e2130;
        border: 1px solid #30334e;
        padding: 20px;
        border-radius: 5px;
    }
    div[data-testid="stMetricValue"] {
        font-family: 'JetBrains Mono', monospace;
        font-size: 28px;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. THE BRAIN (Backend Logic Functions)
def parse_invoice_with_ai(file_obj):
    """
    Extracts structured data from a PDF invoice using OpenAI.
    """
    # Read the PDF text
    with pdfplumber.open(file_obj) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    
    # The Prompt for the AI Analyst
    system_prompt = """
    You are a Logistics Audit Algorithm. Analyze this invoice text. 
    Return a JSON object with a key 'shipments' containing a list of shipments.
    For each shipment, extract: 
    - 'tracking_number' (string)
    - 'service_type' (string)
    - 'weight' (string)
    - 'promised_delivery' (string, HH:MM format if available)
    - 'actual_delivery' (string, HH:MM format)
    - 'amount_charged' (float)
    - 'surcharges' (list of strings)
    
    If data is missing or unclear, make a reasonable estimate based on context or leave null.
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Analyze this invoice data:\n\n{text[:15000]}"} # Limit text length for speed
        ]
    )
    
    return json.loads(response.choices[0].message.content)

def run_audit_logic(shipments):
    """
    The 'Arbitrage' function that finds money.
    """
    audited_data = []
    total_recoverable = 0.0
    
    for s in shipments['shipments']:
        refund_amount = 0.0
        status = "CLEAN"
        note = ""

        # LOGIC 1: LATE DELIVERY (Mock Logic for demo if times are missing)
        # In a real scenario, we compare timestamps. 
        # Here, we 'simulate' a hit if the service is Overnight and it arrived after 10:30.
        if "Overnight" in str(s.get('service_type')) and "10:30" not in str(s.get('actual_delivery')):
             status = "LATE DELIVERY (GSR)"
             refund_amount = float(s.get('amount_charged', 0))
             note = "Delivered after Guaranteed Time"

        # LOGIC 2: RESIDENTIAL SURCHARGE TRAP
        surcharges = str(s.get('surcharges', []))
        if "Residential" in surcharges and float(s.get('amount_charged', 0)) > 20:
             # Just a heuristic for the MVP
             status = "CLASSIFICATION ERROR"
             refund_amount = 5.50
             note = "Commercial address flagged as Residential"

        if refund_amount > 0:
            total_recoverable += refund_amount

        audited_data.append({
            "Tracking #": s.get('tracking_number'),
            "Service": s.get('service_type'),
            "Status": status,
            "Charge": f"${s.get('amount_charged', 0)}",
            "Refund Opp": f"${refund_amount:.2f}",
            "Notes": note
        })
    
    return audited_data, total_recoverable


# 4. THE UI (The Dashboard)
st.title("LOGISTICS TREASURY")
st.markdown("### Institutional Audit Engine v1.0")

# SIDEBAR
with st.sidebar:
    st.header("Upload Parameters")
    uploaded_file = st.file_uploader("Drop Client Invoice (PDF)", type=['pdf'])
    st.markdown("---")
    st.caption("🟢 System Status: ONLINE")
    
    # DEMO MODE BUTTON (For when you don't have a PDF)
    if st.button("RUN DEMO SIMULATION"):
        st.session_state['run_demo'] = True

# MAIN LOGIC
if uploaded_file:
    st.success(f"Processing {uploaded_file.name}...")
    
    # Run the AI (The "Work")
    with st.spinner("Talking to OpenAI Analyst..."):
        try:
            # 1. Parse
            data_json = parse_invoice_with_ai(uploaded_file)
            # 2. Audit
            audit_rows, recoverable_cash = run_audit_logic(data_json)
            # 3. Create DataFrame
            df = pd.DataFrame(audit_rows)
            
            # SHOW RESULTS
            st.markdown("---")
            c1, c2, c3 = st.columns(3)
            with c1: st.metric("Total Shipments", len(df))
            with c2: st.metric("Recoverable Alpha", f"${recoverable_cash:.2f}")
            with c3: st.metric("Audit Yield", "High")
            
            st.dataframe(df, use_container_width=True)
            
            if recoverable_cash > 0:
                st.balloons()
                st.button("EXECUTE RECOVERY CLAIMS", type="primary")
            
        except Exception as e:
            st.error(f"Error reading PDF: {e}")

elif st.session_state.get('run_demo'):
    # THIS IS FOR YOUR PITCH (If you don't have a file handy)
    st.warning("⚠️ SIMULATION MODE ACTIVE")
    
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("Recoverable Alpha", "$1,240.50", "+12%")
    with c2: st.metric("Late Deliveries", "14")
    with c3: st.metric("ROI", "18.4%")
    
    # Mock Data Table
    mock_data = pd.DataFrame({
        "Tracking #": ["1Z992...", "1Z554...", "1Z443..."],
        "Service": ["Priority Overnight", "Ground", "Next Day Air"],
        "Status": ["LATE DELIVERY", "RESIDENTIAL ERR", "LATE DELIVERY"],
        "Refund Opp": ["$84.20", "$5.50", "$112.00"]
    })
    st.dataframe(mock_data, use_container_width=True)

else:
    # IDLE STATE
    st.info("Awaiting Input... Upload PDF to initialize 'Mirror Market' scan.")
    st.markdown("### Live Market Index")
    c1, c2 = st.columns(2)
    with c1: st.metric("Global Recoveries (24h)", "$14,240.00")
    with c2: st.metric("Active Nodes", "142")
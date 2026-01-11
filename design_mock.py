import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time

# --- UI CONFIGURATION (The Canvas) ---
st.set_page_config(
    page_title="NanoBanana Logistics Treasury",
    page_icon="🍌",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CUSTOM CSS (The Brand Styling) ---
st.markdown("""
<style>
    /* Global Background & Font */
    .stApp {
        background-color: #0E1117; /* Institutional Dark */
        color: #FAFAFA;
    }
    
    /* Hero Typography */
    .hero-title {
        font-family: 'Helvetica Neue', sans-serif;
        font-size: 4rem !important;
        font-weight: 800;
        text-align: center;
        background: -webkit-linear-gradient(45deg, #FFFFFF, #E0E0E0);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0px;
        padding-bottom: 0px;
    }
    .hero-sub {
        font-size: 1.5rem !important;
        font-weight: 300;
        text-align: center;
        color: #9E9E9E;
        margin-top: 10px;
        margin-bottom: 40px;
    }
    
    /* Upload Zone Styling */
    .upload-container {
        border: 2px dashed #333;
        border-radius: 12px;
        padding: 40px;
        text-align: center;
        background-color: #161B22;
        margin-bottom: 30px;
    }
    
    /* Metric Cards */
    div[data-testid="stMetricValue"] {
        font-size: 2.5rem !important;
        color: #F4D03F !important; /* Nano Yellow */
    }
    
    /* Button Styling */
    .stButton button {
        background-color: #F4D03F;
        color: black;
        font-weight: bold;
        border-radius: 4px;
        height: 50px;
        width: 100%;
        border: none;
    }
    .stButton button:hover {
        background-color: #D4B020;
        color: black;
    }
</style>
""", unsafe_allow_html=True)

# --- STATE ---
if 'view' not in st.session_state:
    st.session_state['view'] = 'landing'

# --- VIEW 1: LANDING PAGE (The Hook) ---
def render_landing():
    # 1. NAVBAR
    c1, c2 = st.columns([1, 10])
    with c1:
        st.write("🍌 **NanoBanana**")
    
    st.write("---")
    
    # 2. HERO SECTION
    st.markdown('<p class="hero-title">RECOVER YOUR<br>LOGISTICS ALPHA.</p>', unsafe_allow_html=True)
    st.markdown('<p class="hero-sub">Turn Shipping Inefficiency into Working Capital.<br>Institutional-grade audit for FedEx & UPS.</p>', unsafe_allow_html=True)
    
    # 3. THE UPLOAD ZONE (Central Visual)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.info("🔒 Secure Treasury Gateway")
        with st.container(border=True):
            st.markdown("### 📤 Drop Invoice Here")
            st.caption("Supports .PDF (FedEx/UPS) | Max 200MB")
            uploaded = st.file_uploader("", label_visibility="collapsed")
            
            if uploaded:
                st.success(f"Verified: {uploaded.name}")
                if st.button("RUN SIMULATION (AUDIT)"):
                    with st.spinner("Calculating recoverable alpha..."):
                        time.sleep(1.5)
                        st.session_state['view'] = 'dashboard'
                        st.rerun()

    # 4. HOW IT WORKS (3-Step)
    st.write("")
    st.write("")
    st.write("")
    h1, h2, h3 = st.columns(3)
    with h1:
        st.markdown("### 1. Ingest 📥")
        st.caption("Securely upload raw carrier invoices. We parse line-item data in milliseconds.")
    with h2:
        st.markdown("### 2. Audit 🧠")
        st.caption("Our algorithm cross-references 50+ service guarantees to detect contract breaches.")
    with h3:
        st.markdown("### 3. Recoup 💸")
        st.caption("We generate the claim artifacts. You recover the capital. Zero friction.")

    # 5. ABOUT SECTION (Brand Trust)
    st.markdown("---")
    st.markdown("### Why NanoBanana?")
    st.write("""
    Logistics carriers profit from complexity. We profit from clarity. 
    **NanoBanana** was built to give shippers the same algorithmic advantage that carriers use against them. 
    
    * **Tiny Tech:** Lightweight, browser-based, zero integration.
    * **Tasty Yields:** Average recovery of 12-18% per invoice.
    """)

# --- VIEW 2: DASHBOARD (The Product) ---
def render_dashboard():
    # HEADER
    st.markdown("### 🍌 Logistics Treasury Dashboard")
    st.markdown("---")
    
    # TOP METRICS
    m1, m2, m3 = st.columns(3)
    m1.metric("RECOVERABLE ALPHA", "$1,240.50", "+12.4%")
    m2.metric("ROI / YIELD", "18.4%", "Annualized")
    m3.metric("LATE DELIVERIES", "14", "Actionable")
    
    # MAIN GRID
    st.subheader("Audit Findings")
    df = pd.DataFrame({
        "Tracking #": ["1Z992...", "1Z554...", "1Z443...", "1Z112..."],
        "Service": ["Priority Overnight", "Ground", "Next Day Air", "Ground"],
        "Status": ["LATE (14min)", "WRONG ADDRESS", "LATE (45min)", "DAMAGED"],
        "Value": ["$84.20", "$15.50", "$112.00", "$45.00"],
        "Action": ["CLAIM READY", "REVIEW", "CLAIM READY", "CLAIM READY"]
    })
    
    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "Status": st.column_config.TextColumn("Audit Status", help="Red = Late"),
            "Action": st.column_config.Column("Recommendation"),
        },
        hide_index=True
    )
    
    # BOTTOM ACTION BAR
    st.write("")
    st.write("")
    c1, c2 = st.columns([3, 1])
    with c1:
        st.progress(100, text="Audit Complete. 14 Claims prepared.")
    with c2:
        if st.button("PROCESS RECOUP ➔"):
            st.balloons()
            st.success("Claims transmitted to carrier treasury.")
    
    if st.button("← Back to Upload"):
        st.session_state['view'] = 'landing'
        st.rerun()

# --- MAIN ROUTER ---
if st.session_state['view'] == 'landing':
    render_landing()
else:
    render_dashboard()
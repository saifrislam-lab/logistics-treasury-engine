import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="NanoBanana Logistics Treasury",
    page_icon="🍌",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CUSTOM CSS FOR MOCK ALIGNMENT ---
# This forces the "Hero" section to look like the design (Centered, Big Fonts)
st.markdown("""
<style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    h1 {
        text-align: center; 
        font-size: 3.5rem !important;
        font-weight: 800 !important;
        color: #0E1117;
    }
    h3 {
        text-align: center;
        font-weight: 400 !important;
        color: #555;
        margin-bottom: 2rem;
    }
    .stButton button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        font-weight: bold;
    }
    /* Dark mode adjustment helper */
    @media (prefers-color-scheme: dark) {
        h1 { color: #FAFAFA !important; }
        h3 { color: #CCCCCC !important; }
    }
</style>
""", unsafe_allow_html=True)

# --- SESSION STATE MANAGEMENT ---
if 'page' not in st.session_state:
    st.session_state['page'] = 'landing' # Options: 'landing', 'dashboard'
if 'audit_data' not in st.session_state:
    st.session_state['audit_data'] = None

# --- SIDEBAR CONTROLS ---
with st.sidebar:
    st.header("Logistics Treasury")
    if st.button("Reset Application"):
        st.session_state['page'] = 'landing'
        st.session_state['audit_data'] = None
        st.rerun()
    st.markdown("---")
    st.caption("NanoBanana Internal v1.0")

# =========================================================
#  LOGIC ROUTING
# =========================================================

def show_landing_page():
    # --- HERO SECTION ---
    # Centered Header
    st.markdown("<h1>RECOVER YOUR<br>LOGISTICS ALPHA.</h1>", unsafe_allow_html=True)
    st.markdown("<h3>Turn Shipping Inefficiency into Working Capital.<br>Instant, automated audit for FedEx & UPS.</h3>", unsafe_allow_html=True)

    # --- THE UPLOAD BOX (The Mock's Central Feature) ---
    col_spacer_l, col_center, col_spacer_r = st.columns([1, 2, 1])
    
    with col_center:
        # We use a container with a border to mimic the mock's "Upload Box" look
        with st.container(border=True):
            st.markdown("##### 📤 Upload Invoice (PDF)")
            uploaded_file = st.file_uploader("", type=['pdf', 'csv'], label_visibility="collapsed")
            
            if uploaded_file is not None:
                st.success(f"File verified: {uploaded_file.name}")
                
                # The Bridge to the Dashboard
                if st.button("RUN AUDIT ANALYSIS ⚡"):
                    with st.spinner("AI Auditor extracting line items..."):
                        time.sleep(1.5) # UX Delay for realism
                        st.session_state['page'] = 'dashboard'
                        st.rerun()

    # --- SOCIAL PROOF / TICKER ---
    st.write("")
    st.write("")
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.info("✅ **+ $14.2M Restored to date** /// Latest recovery: +$1,240.50 (2 mins ago)")

def show_dashboard():
    # --- HEADER ---
    st.markdown("### 🍌 Logistics Treasury Dashboard")
    st.markdown("---")

    # --- TOP ROW: METRICS (The Mock's Top Bar) ---
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Recoverable Alpha", "$1,240.50", "+12%", delta_color="normal")
    m2.metric("Yield / ROI", "18.4%", "+2.1%")
    m3.metric("Late Packages", "14", "-2")
    m4.metric("Audit Coverage", "100%", "UPS & FDX")

    # --- MIDDLE ROW: THE AUDIT GRID ---
    st.write("")
    st.subheader("Active Audit Claims")
    
    # Mock Data matching the design
    data = {
        "Tracking #": ["1Z99283...", "1Z55419...", "1Z44321...", "1Z99110...", "1Z33211..."],
        "Service": ["Priority Overnight", "Ground", "Next Day Air", "Priority Overnight", "Ground"],
        "Status": ["LATE DELIVERY", "RESIDENTIAL ERR", "LATE DELIVERY", "LATE DELIVERY", "LATE DELIVERY"],
        "Charge": ["$84.20", "$15.50", "$112.00", "$92.10", "$14.50"],
        "Refund Opp": ["$84.20", "$5.50", "$112.00", "$92.10", "$14.50"],
        "Action": ["CLAIM READY", "CLAIM READY", "CLAIM READY", "CLAIM READY", "CLAIM READY"]
    }
    df = pd.DataFrame(data)

    # Using Column Config to make it look "App-like"
    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "Status": st.column_config.TextColumn("Audit Status", help="AI Detection"),
            "Refund Opp": st.column_config.TextColumn("Potential Refund"),
            "Action": st.column_config.Column("Action", help="Click to file claim"),
        },
        hide_index=True
    )

    # --- BOTTOM ROW: ACTION & INSIGHTS ---
    c_left, c_right = st.columns([2, 1])
    
    with c_left:
        st.caption("AI Auditor at work: Identifying Contractual Breach...")
        st.progress(100)
        
        # Primary Call to Action
        if st.button("Process All Claims (Recoup)", type="primary"):
            st.toast("Claims submitted to carrier portals successfully!", icon="💸")
            st.balloons()

    with c_right:
        st.markdown("##### Recovery Probability")
        # Simple Chart matching the mock's aesthetic
        fig = go.Figure(data=[go.Bar(
            x=['Ground', 'Express', 'Intl'],
            y=[85, 95, 60],
            marker_color=['#00CC96', '#EF553B', '#636EFA']
        )])
        fig.update_layout(height=200, margin=dict(t=0, b=0, l=0, r=0), paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)

# =========================================================
#  MAIN APP CONTROLLER
# =========================================================

if st.session_state['page'] == 'landing':
    show_landing_page()
elif st.session_state['page'] == 'dashboard':
    show_dashboard()
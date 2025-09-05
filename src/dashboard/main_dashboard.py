import streamlit as st
import sys
import os

# Add the dashboard directory to the path
sys.path.append(os.path.dirname(__file__))

# Import dashboard modules
try:
    from scm_dashboard import main as scm_main
    from okr_dashboard import main as okr_main
except ImportError as e:
    st.error(f"Error importing dashboard modules: {e}")
    st.stop()

def main():
    st.set_page_config(
        page_title="Analytics Dashboard Hub",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS for better styling
    st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
        background: linear-gradient(90deg, #1f77b4, #ff7f0e);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: bold;
    }
    .dashboard-selector {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 2rem;
    }
    .nav-button {
        display: block;
        width: 100%;
        padding: 0.75rem;
        margin: 0.5rem 0;
        border: none;
        border-radius: 0.5rem;
        background-color: #1f77b4;
        color: white;
        font-size: 1.1rem;
        font-weight: bold;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    .nav-button:hover {
        background-color: #0f5f94;
        transform: translateY(-2px);
    }
    .nav-button.active {
        background-color: #ff7f0e;
    }
    .sidebar-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    if 'selected_dashboard' not in st.session_state:
        st.session_state.selected_dashboard = 'SCM'
    
    # Sidebar navigation
    st.sidebar.markdown('<div class="sidebar-header">📊 Dashboard Hub</div>', unsafe_allow_html=True)
    st.sidebar.markdown("---")
    
    # Dashboard selection
    st.sidebar.subheader("Select Dashboard")
    
    # SCM Dashboard button
    if st.sidebar.button("🏭 SCM Analytics", key="scm_btn", help="Supply Chain Management Analytics"):
        st.session_state.selected_dashboard = 'SCM'
        st.rerun()
    
    # OKR Dashboard button  
    if st.sidebar.button("🎯 OKR Analytics", key="okr_btn", help="Objectives and Key Results Analytics"):
        st.session_state.selected_dashboard = 'OKR'
        st.rerun()
    
    st.sidebar.markdown("---")
    
    # Current selection indicator
    st.sidebar.info(f"Current: {st.session_state.selected_dashboard} Dashboard")
    
    # Dashboard info
    st.sidebar.markdown("### Dashboard Info")
    if st.session_state.selected_dashboard == 'SCM':
        st.sidebar.markdown("""
        **SCM Analytics Features:**
        - Real-time data processing
        - Request monitoring
        - Inventory tracking
        - Performance metrics
        - Kafka stream analysis
        """)
    else:
        st.sidebar.markdown("""
        **OKR Analytics Features:**
        - Objectives tracking
        - Key results monitoring
        - Progress analytics
        - Department insights
        - Trend analysis
        """)
    
    # Main content area
    if st.session_state.selected_dashboard == 'SCM':
        display_scm_dashboard()
    elif st.session_state.selected_dashboard == 'OKR':
        display_okr_dashboard()

def display_scm_dashboard():
    """Display the SCM dashboard"""
    try:
        # Clear the main area and run SCM dashboard
        scm_main()
    except Exception as e:
        st.error(f"Error loading SCM dashboard: {e}")
        st.markdown("""
        ### SCM Dashboard Error
        
        There was an error loading the SCM dashboard. This might be due to:
        - Kafka connection issues
        - Missing data
        - Configuration problems
        
        Please check the logs and ensure all services are running properly.
        """)

def display_okr_dashboard():
    """Display the OKR dashboard"""
    try:
        # Clear the main area and run OKR dashboard
        okr_main()
    except Exception as e:
        st.error(f"Error loading OKR dashboard: {e}")
        st.markdown("""
        ### OKR Dashboard Error
        
        There was an error loading the OKR dashboard. This might be due to:
        - Oracle database connection issues
        - Kafka connection issues
        - Missing OKR data
        - Configuration problems
        
        Please check the logs and ensure all services are running properly.
        """)

if __name__ == "__main__":
    main()
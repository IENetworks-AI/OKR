import os
import json
import time
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from kafka import KafkaConsumer
from datetime import datetime, timedelta
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
def load_environment():
    candidate_paths = [
        "/opt/airflow/configs/.env",
        os.path.join(os.path.dirname(__file__), "..", "..", "configs", ".env"),
        os.path.join(os.path.dirname(__file__), "..", "..", "configs", "env.vars"),
        os.path.join(os.getcwd(), ".env"),
    ]
    
    for env_path in candidate_paths:
        try:
            if os.path.exists(env_path):
                load_dotenv(env_path)
                logger.info(f"Loaded environment from {env_path}")
                break
        except Exception as e:
            logger.warning(f"Failed to load {env_path}: {e}")
            continue

load_environment()

# Kafka configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
TOPIC_OBJECTIVES = "okr_objectives_transformed"
TOPIC_KEY_RESULTS = "okr_key_results_transformed"
TOPIC_INSIGHTS = "okr_insights"
TOPIC_TRENDS = "okr_trends"
TOPIC_DEPARTMENT_STATS = "okr_department_stats"

# Initialize Kafka consumers
def create_kafka_consumer(topic):
    try:
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS.split(','),
            value_deserializer=lambda x: json.loads(x.decode('utf-8')),
            auto_offset_reset='earliest',
            consumer_timeout_ms=5000,
            enable_auto_commit=True
        )
        return consumer
    except Exception as e:
        logger.error(f"Error creating Kafka consumer for topic {topic}: {e}")
        return None

# Fetch data from Kafka topics
def fetch_okr_data():
    """Fetch OKR data from all relevant Kafka topics"""
    data = {
        'objectives': [],
        'key_results': [],
        'insights': [],
        'trends': [],
        'department_stats': []
    }
    
    topics = {
        'objectives': TOPIC_OBJECTIVES,
        'key_results': TOPIC_KEY_RESULTS,
        'insights': TOPIC_INSIGHTS,
        'trends': TOPIC_TRENDS,
        'department_stats': TOPIC_DEPARTMENT_STATS
    }
    
    for data_type, topic in topics.items():
        try:
            consumer = create_kafka_consumer(topic)
            if consumer:
                messages = []
                for message in consumer:
                    messages.append(message.value)
                    if len(messages) >= 1000:  # Limit messages to prevent memory issues
                        break
                
                data[data_type] = messages
                consumer.close()
                logger.info(f"Fetched {len(messages)} messages from {topic}")
        except Exception as e:
            logger.error(f"Error fetching data from {topic}: {e}")
            data[data_type] = []
    
    return data

def main():
    st.set_page_config(
        page_title="OKR Analytics Dashboard",
        page_icon="🎯",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS
    st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
        margin: 0.5rem 0;
    }
    .success-metric {
        border-left-color: #2ca02c;
    }
    .warning-metric {
        border-left-color: #ff7f0e;
    }
    .danger-metric {
        border-left-color: #d62728;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown('<h1 class="main-header">🎯 OKR Analytics Dashboard</h1>', unsafe_allow_html=True)
    
    # Sidebar
    st.sidebar.title("🎯 OKR Dashboard")
    st.sidebar.markdown("---")
    
    # Auto-refresh toggle
    auto_refresh = st.sidebar.checkbox("Auto-refresh (30s)", value=False)
    if auto_refresh:
        time.sleep(30)
        st.rerun()
    
    # Manual refresh button
    if st.sidebar.button("🔄 Refresh Data"):
        st.rerun()
    
    # Fetch data
    with st.spinner("Loading OKR data..."):
        okr_data = fetch_okr_data()
    
    # Main content tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Overview", "🎯 Objectives", "🔑 Key Results", "📈 Trends", "🏢 Departments"])
    
    with tab1:
        display_overview(okr_data)
    
    with tab2:
        display_objectives(okr_data)
    
    with tab3:
        display_key_results(okr_data)
    
    with tab4:
        display_trends(okr_data)
    
    with tab5:
        display_departments(okr_data)

def display_overview(okr_data):
    """Display OKR overview metrics"""
    st.subheader("📊 OKR Overview")
    
    # Calculate summary metrics
    objectives = okr_data.get('objectives', [])
    key_results = okr_data.get('key_results', [])
    insights = okr_data.get('insights', [])
    
    if objectives:
        obj_df = pd.DataFrame(objectives)
        total_objectives = len(obj_df)
        completed_objectives = len(obj_df[obj_df['status'] == 'completed']) if 'status' in obj_df.columns else 0
        completion_rate = (completed_objectives / total_objectives * 100) if total_objectives > 0 else 0
        
        high_risk_count = len(obj_df[obj_df.get('risk_level', '') == 'high']) if 'risk_level' in obj_df.columns else 0
    else:
        total_objectives = completed_objectives = completion_rate = high_risk_count = 0
    
    if key_results:
        kr_df = pd.DataFrame(key_results)
        total_key_results = len(kr_df)
        avg_progress = kr_df['progress_percentage'].mean() if 'progress_percentage' in kr_df.columns else 0
        on_track_count = len(kr_df[kr_df.get('is_on_track', False) == True]) if 'is_on_track' in kr_df.columns else 0
    else:
        total_key_results = avg_progress = on_track_count = 0
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card success-metric">
            <h3>Total Objectives</h3>
            <h2>{total_objectives}</h2>
            <p>Completion Rate: {completion_rate:.1f}%</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card {'success-metric' if avg_progress >= 70 else 'warning-metric' if avg_progress >= 50 else 'danger-metric'}">
            <h3>Avg Progress</h3>
            <h2>{avg_progress:.1f}%</h2>
            <p>Key Results Progress</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <h3>Key Results</h3>
            <h2>{total_key_results}</h2>
            <p>On Track: {on_track_count}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card {'danger-metric' if high_risk_count > 0 else 'success-metric'}">
            <h3>High Risk</h3>
            <h2>{high_risk_count}</h2>
            <p>Objectives at Risk</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Progress distribution chart
    if key_results:
        st.subheader("📈 Progress Distribution")
        
        progress_bins = pd.cut(kr_df['progress_percentage'], 
                             bins=[0, 25, 50, 75, 100], 
                             labels=['0-25%', '26-50%', '51-75%', '76-100%'])
        progress_counts = progress_bins.value_counts()
        
        fig = px.bar(x=progress_counts.index, y=progress_counts.values,
                    title="Key Results Progress Distribution",
                    labels={'x': 'Progress Range', 'y': 'Number of Key Results'},
                    color=progress_counts.values,
                    color_continuous_scale='RdYlGn')
        st.plotly_chart(fig, use_container_width=True)

def display_objectives(okr_data):
    """Display objectives analysis"""
    st.subheader("🎯 Objectives Analysis")
    
    objectives = okr_data.get('objectives', [])
    if not objectives:
        st.warning("No objectives data available")
        return
    
    obj_df = pd.DataFrame(objectives)
    
    # Status distribution
    col1, col2 = st.columns(2)
    
    with col1:
        if 'status' in obj_df.columns:
            status_counts = obj_df['status'].value_counts()
            fig = px.pie(values=status_counts.values, names=status_counts.index,
                        title="Objectives by Status")
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        if 'priority' in obj_df.columns:
            priority_counts = obj_df['priority'].value_counts()
            fig = px.bar(x=priority_counts.index, y=priority_counts.values,
                        title="Objectives by Priority",
                        color=priority_counts.values,
                        color_continuous_scale='Reds')
            st.plotly_chart(fig, use_container_width=True)
    
    # Risk assessment
    if 'risk_level' in obj_df.columns:
        st.subheader("⚠️ Risk Assessment")
        risk_counts = obj_df['risk_level'].value_counts()
        
        colors = {'high': '#d62728', 'medium': '#ff7f0e', 'low': '#2ca02c'}
        fig = px.bar(x=risk_counts.index, y=risk_counts.values,
                    title="Objectives by Risk Level",
                    color=risk_counts.index,
                    color_discrete_map=colors)
        st.plotly_chart(fig, use_container_width=True)
    
    # Objectives table
    st.subheader("📋 Objectives Details")
    display_columns = ['title', 'department', 'status', 'priority', 'days_remaining']
    available_columns = [col for col in display_columns if col in obj_df.columns]
    
    if available_columns:
        st.dataframe(obj_df[available_columns], use_container_width=True)

def display_key_results(okr_data):
    """Display key results analysis"""
    st.subheader("🔑 Key Results Analysis")
    
    key_results = okr_data.get('key_results', [])
    if not key_results:
        st.warning("No key results data available")
        return
    
    kr_df = pd.DataFrame(key_results)
    
    # Progress vs Target analysis
    if 'current_value' in kr_df.columns and 'target_value' in kr_df.columns:
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.scatter(kr_df, x='target_value', y='current_value',
                           title="Current vs Target Values",
                           hover_data=['title'] if 'title' in kr_df.columns else None)
            # Add diagonal line for target achievement
            max_val = max(kr_df['target_value'].max(), kr_df['current_value'].max())
            fig.add_shape(type="line", x0=0, y0=0, x1=max_val, y1=max_val,
                         line=dict(color="red", dash="dash"))
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            if 'achievement_rate' in kr_df.columns:
                fig = px.histogram(kr_df, x='achievement_rate',
                                 title="Achievement Rate Distribution",
                                 nbins=20)
                st.plotly_chart(fig, use_container_width=True)
    
    # Progress tracking
    if 'progress_percentage' in kr_df.columns:
        st.subheader("📊 Progress Tracking")
        
        # On track vs needs attention
        if 'is_on_track' in kr_df.columns and 'needs_attention' in kr_df.columns:
            on_track = len(kr_df[kr_df['is_on_track'] == True])
            needs_attention = len(kr_df[kr_df['needs_attention'] == True])
            normal = len(kr_df) - on_track - needs_attention
            
            fig = px.pie(values=[on_track, needs_attention, normal],
                        names=['On Track', 'Needs Attention', 'Normal'],
                        title="Key Results Status",
                        color_discrete_map={
                            'On Track': '#2ca02c',
                            'Needs Attention': '#d62728',
                            'Normal': '#1f77b4'
                        })
            st.plotly_chart(fig, use_container_width=True)
    
    # Key Results table
    st.subheader("📋 Key Results Details")
    display_columns = ['title', 'current_value', 'target_value', 'progress_percentage', 'status']
    available_columns = [col for col in display_columns if col in kr_df.columns]
    
    if available_columns:
        st.dataframe(kr_df[available_columns], use_container_width=True)

def display_trends(okr_data):
    """Display trends analysis"""
    st.subheader("📈 Trends Analysis")
    
    trends = okr_data.get('trends', [])
    if not trends:
        st.warning("No trends data available")
        return
    
    trends_df = pd.DataFrame(trends)
    
    # Velocity distribution
    if 'velocity' in trends_df.columns:
        fig = px.histogram(trends_df, x='velocity',
                         title="Progress Velocity Distribution",
                         nbins=20,
                         labels={'velocity': 'Progress Velocity (% per day)'})
        st.plotly_chart(fig, use_container_width=True)
    
    # Trend direction analysis
    if 'trend_direction' in trends_df.columns:
        col1, col2 = st.columns(2)
        
        with col1:
            direction_counts = trends_df['trend_direction'].value_counts()
            fig = px.pie(values=direction_counts.values, names=direction_counts.index,
                        title="Trend Directions",
                        color_discrete_map={
                            'positive': '#2ca02c',
                            'negative': '#d62728',
                            'stable': '#ff7f0e'
                        })
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            if 'update_frequency' in trends_df.columns:
                fig = px.scatter(trends_df, x='update_frequency', y='velocity',
                               color='trend_direction',
                               title="Update Frequency vs Velocity",
                               color_discrete_map={
                                   'positive': '#2ca02c',
                                   'negative': '#d62728',
                                   'stable': '#ff7f0e'
                               })
                st.plotly_chart(fig, use_container_width=True)

def display_departments(okr_data):
    """Display department-wise analysis"""
    st.subheader("🏢 Department Analysis")
    
    department_stats = okr_data.get('department_stats', [])
    objectives = okr_data.get('objectives', [])
    
    if department_stats:
        dept_df = pd.DataFrame(department_stats)
        
        # Department completion rates
        if 'completion_rate' in dept_df.columns:
            fig = px.bar(dept_df, x='department', y='completion_rate',
                        title="Completion Rate by Department",
                        color='completion_rate',
                        color_continuous_scale='RdYlGn')
            st.plotly_chart(fig, use_container_width=True)
        
        # Department objectives count
        if 'total_objectives' in dept_df.columns:
            fig = px.bar(dept_df, x='department', y='total_objectives',
                        title="Total Objectives by Department")
            st.plotly_chart(fig, use_container_width=True)
    
    elif objectives:
        # Fallback to objectives data if department stats not available
        obj_df = pd.DataFrame(objectives)
        if 'department' in obj_df.columns:
            dept_counts = obj_df['department'].value_counts()
            fig = px.bar(x=dept_counts.index, y=dept_counts.values,
                        title="Objectives by Department")
            st.plotly_chart(fig, use_container_width=True)
    
    else:
        st.warning("No department data available")

if __name__ == "__main__":
    main()
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
PLAN_TASKS_TOPIC = os.getenv("KAFKA_TOPIC", "plan_tasks_topic")

def create_kafka_consumer(topic):
    """Create Kafka consumer for the specified topic"""
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

def fetch_plan_tasks_data():
    """Fetch plan tasks data from Kafka"""
    try:
        consumer = create_kafka_consumer(PLAN_TASKS_TOPIC)
        if not consumer:
            return []
        
        messages = []
        for message in consumer:
            messages.append(message.value)
            if len(messages) >= 1000:  # Limit messages
                break
        
        consumer.close()
        logger.info(f"Fetched {len(messages)} plan tasks messages")
        return messages
        
    except Exception as e:
        logger.error(f"Error fetching plan tasks data: {e}")
        return []

def display_plan_tasks_overview(data):
    """Display overview metrics for plan tasks"""
    if not data:
        st.warning("No plan tasks data available")
        return
    
    df = pd.DataFrame(data)
    
    # Calculate metrics
    total_plans = df['weekly_plan_id'].nunique() if 'weekly_plan_id' in df.columns else 0
    total_weekly_tasks = df['weekly_task_id'].nunique() if 'weekly_task_id' in df.columns else 0
    total_daily_tasks = df['daily_task_id'].nunique() if 'daily_task_id' in df.columns else 0
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Plans", total_plans)
    
    with col2:
        st.metric("Weekly Tasks", total_weekly_tasks)
    
    with col3:
        st.metric("Daily Tasks", total_daily_tasks)
    
    with col4:
        st.metric("Total Records", len(df))

def display_task_priorities(data):
    """Display task priority distribution"""
    if not data:
        return
    
    df = pd.DataFrame(data)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if 'weekly_task_priority' in df.columns:
            priority_counts = df['weekly_task_priority'].value_counts()
            fig = px.pie(
                values=priority_counts.values, 
                names=priority_counts.index,
                title="Weekly Task Priority Distribution"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        if 'daily_task_priority' in df.columns:
            daily_priority = df['daily_task_priority'].dropna().value_counts()
            if not daily_priority.empty:
                fig = px.pie(
                    values=daily_priority.values, 
                    names=daily_priority.index,
                    title="Daily Task Priority Distribution"
                )
                st.plotly_chart(fig, use_container_width=True)

def display_task_weights(data):
    """Display task weight analysis"""
    if not data:
        return
    
    df = pd.DataFrame(data)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if 'weekly_task_weight' in df.columns:
            weights = df['weekly_task_weight'].dropna()
            if not weights.empty:
                fig = px.histogram(
                    weights, 
                    title="Weekly Task Weight Distribution",
                    nbins=20
                )
                st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        if 'daily_task_weight' in df.columns:
            daily_weights = df['daily_task_weight'].dropna()
            if not daily_weights.empty:
                fig = px.histogram(
                    daily_weights, 
                    title="Daily Task Weight Distribution",
                    nbins=20
                )
                st.plotly_chart(fig, use_container_width=True)

def display_task_status(data):
    """Display task status information"""
    if not data:
        return
    
    df = pd.DataFrame(data)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if 'weekly_task_status' in df.columns:
            status_counts = df['weekly_task_status'].value_counts()
            if not status_counts.empty:
                fig = px.bar(
                    x=status_counts.index, 
                    y=status_counts.values,
                    title="Weekly Task Status"
                )
                st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        if 'daily_task_status' in df.columns:
            daily_status = df['daily_task_status'].dropna().value_counts()
            if not daily_status.empty:
                fig = px.bar(
                    x=daily_status.index, 
                    y=daily_status.values,
                    title="Daily Task Status"
                )
                st.plotly_chart(fig, use_container_width=True)

def display_recent_tasks(data):
    """Display recent tasks table"""
    if not data:
        return
    
    df = pd.DataFrame(data)
    
    # Show recent tasks
    st.subheader("Recent Tasks")
    
    display_columns = [
        'weekly_plan_desc', 'weekly_task_name', 'daily_task_name',
        'weekly_task_priority', 'weekly_task_weight', 'weekly_task_status'
    ]
    
    available_columns = [col for col in display_columns if col in df.columns]
    
    if available_columns:
        # Sort by extraction timestamp if available
        if 'extraction_timestamp' in df.columns:
            df = df.sort_values('extraction_timestamp', ascending=False)
        
        # Show top 20 records
        st.dataframe(df[available_columns].head(20), use_container_width=True)
    else:
        st.warning("No task details available to display")

def main():
    """Main function for plan tasks dashboard"""
    st.subheader("📋 Plan Tasks Analytics")
    
    # Auto-refresh toggle
    col1, col2 = st.columns([3, 1])
    with col2:
        auto_refresh = st.checkbox("Auto-refresh (30s)", value=False)
        if auto_refresh:
            time.sleep(30)
            st.rerun()
    
    # Manual refresh button
    if st.button("🔄 Refresh Plan Tasks Data"):
        st.rerun()
    
    # Fetch data
    with st.spinner("Loading plan tasks data..."):
        plan_tasks_data = fetch_plan_tasks_data()
    
    if not plan_tasks_data:
        st.error("No plan tasks data available. Please check:")
        st.markdown("""
        - Kafka connection to topic: `plan_tasks_topic`
        - Plan tasks DAG execution status
        - Network connectivity to Kafka
        """)
        return
    
    # Display analytics
    st.markdown("---")
    display_plan_tasks_overview(plan_tasks_data)
    
    st.markdown("---")
    st.subheader("📊 Task Analysis")
    
    # Tabs for different analyses
    tab1, tab2, tab3, tab4 = st.tabs(["Priorities", "Weights", "Status", "Recent Tasks"])
    
    with tab1:
        display_task_priorities(plan_tasks_data)
    
    with tab2:
        display_task_weights(plan_tasks_data)
    
    with tab3:
        display_task_status(plan_tasks_data)
    
    with tab4:
        display_recent_tasks(plan_tasks_data)
    
    # Data freshness info
    st.markdown("---")
    st.info(f"📊 Showing data from {len(plan_tasks_data)} records from Kafka topic: `{PLAN_TASKS_TOPIC}`")

if __name__ == "__main__":
    main()
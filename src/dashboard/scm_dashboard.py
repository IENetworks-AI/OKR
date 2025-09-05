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
TOPIC_REQUESTS = "scm_requests"
TOPIC_INVENTORY = "scm_inventory"

# Initialize Kafka consumers
def create_kafka_consumer(topic):
    try:
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS.split(','),
            value_deserializer=lambda x: json.loads(x.decode('utf-8')),
            auto_offset_reset='latest',  # Start from latest messages
            group_id=f'streamlit_{topic}_group_{int(time.time())}',  # Unique group ID
            enable_auto_commit=True,
            consumer_timeout_ms=1000,  # 1 second timeout
        )
        return consumer
    except Exception as e:
        logger.error(f"Error creating Kafka consumer for {topic}: {e}")
        st.error(f"Failed to connect to Kafka for {topic}: {e}")
        return None

# Fetch data from Kafka with timeout
def fetch_kafka_data(consumer, max_messages=100, timeout=5):
    data = []
    start_time = time.time()
    try:
        while len(data) < max_messages and (time.time() - start_time) < timeout:
            messages = consumer.poll(timeout_ms=1000)  # Poll for 1 second
            for topic_partition, partition_messages in messages.items():
                for message in partition_messages:
                    data.append(message.value)
                    if len(data) >= max_messages:
                        break
        return data
    except Exception as e:
        logger.error(f"Error fetching data from Kafka: {e}")
        st.error(f"Error fetching data from Kafka: {e}")
        return []

# Streamlit app
def main():
    st.set_page_config(
        page_title="SCM Real-Time Dashboard",
        page_icon="📊",
        layout="wide",
    )

    st.title("SCM Real-Time Dashboard")
    st.markdown("Real-time monitoring of SCM inventory and requests from Kafka topics.")
    
    # Display connection status
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"Kafka Servers: {KAFKA_BOOTSTRAP_SERVERS}")
    with col2:
        st.info(f"Topics: {TOPIC_REQUESTS}, {TOPIC_INVENTORY}")

    # Initialize session state for data storage
    if 'requests_data' not in st.session_state:
        st.session_state.requests_data = []
    if 'inventory_data' not in st.session_state:
        st.session_state.inventory_data = []
    if 'last_update' not in st.session_state:
        st.session_state.last_update = datetime.now()

    # Create Kafka consumers
    requests_consumer = create_kafka_consumer(TOPIC_REQUESTS)
    inventory_consumer = create_kafka_consumer(TOPIC_INVENTORY)

    # Auto-refresh toggle
    auto_refresh = st.sidebar.checkbox("Auto Refresh", value=True)
    refresh_interval = st.sidebar.slider("Refresh Interval (seconds)", 5, 60, 10)
    
    # Manual refresh button
    if st.sidebar.button("Refresh Now"):
        st.session_state.last_update = datetime.now()
        st.rerun()

    # Data fetching section
    with st.spinner("Fetching data from Kafka..."):
        # Fetch data from Kafka
        if requests_consumer:
            new_requests = fetch_kafka_data(requests_consumer, max_messages=50)
            if new_requests:
                st.session_state.requests_data.extend(new_requests)
                # Limit to last 1000 records to prevent memory issues
                st.session_state.requests_data = st.session_state.requests_data[-1000:]

        if inventory_consumer:
            new_inventory = fetch_kafka_data(inventory_consumer, max_messages=50)
            if new_inventory:
                st.session_state.inventory_data.extend(new_inventory)
                st.session_state.inventory_data = st.session_state.inventory_data[-1000:]

    # Convert to DataFrames
    requests_df = pd.DataFrame(st.session_state.requests_data)
    inventory_df = pd.DataFrame(st.session_state.inventory_data)

    # Display last update time
    st.sidebar.markdown(f"**Last Update:** {st.session_state.last_update.strftime('%Y-%m-%d %H:%M:%S')}")

    # Display metrics
    st.subheader("Key Metrics")
    col1, col2, col3, col4 = st.columns(4)
    
    if not requests_df.empty:
        total_requests = len(requests_df)
        pending_requests = len(requests_df[requests_df['is_approved'].isna() | (requests_df['is_approved'] == 0)])
        approved_requests = len(requests_df[requests_df['is_approved'] == 1])
        fulfilled_requests = len(requests_df[requests_df['is_requester_received'] == 1])
        
        with col1:
            st.metric("Total Requests", total_requests)
        with col2:
            st.metric("Pending Requests", pending_requests)
        with col3:
            st.metric("Approved Requests", approved_requests)
        with col4:
            st.metric("Fulfilled Requests", fulfilled_requests)
    else:
        st.warning("No request data available yet. Make sure the SCM pipeline is running and producing data to Kafka.")

    if not inventory_df.empty:
        total_items = len(inventory_df)
        total_stock = inventory_df['current_stock'].sum() if 'current_stock' in inventory_df.columns else inventory_df['quantity'].sum()
        low_stock_items = len(inventory_df[inventory_df['current_stock'] < 10]) if 'current_stock' in inventory_df.columns else 0
        total_value = (inventory_df['price'] * inventory_df['quantity']).sum() if 'price' in inventory_df.columns else 0
        
        with col1:
            st.metric("Total Inventory Items", total_items)
        with col2:
            st.metric("Total Stock Quantity", f"{total_stock:.0f}")
        with col3:
            st.metric("Low Stock Items (<10)", low_stock_items)
        with col4:
            st.metric("Total Value", f"${total_value:,.2f}")
    else:
        st.warning("No inventory data available yet. Make sure the SCM pipeline is running and producing data to Kafka.")

    # Visualizations
    st.subheader("Visualizations")
    
    if not inventory_df.empty:
        # Stock by Source
        if 'source' in inventory_df.columns:
            stock_by_source = inventory_df.groupby('source')['current_stock'].sum().reset_index() if 'current_stock' in inventory_df.columns else inventory_df.groupby('source')['quantity'].sum().reset_index()
            stock_column = 'current_stock' if 'current_stock' in inventory_df.columns else 'quantity'
            
            fig_stock = px.bar(
                stock_by_source,
                x='source',
                y=stock_column,
                title="Current Stock by Source",
                labels={stock_column: 'Stock Quantity', 'source': 'Source'},
                color='source'
            )
            st.plotly_chart(fig_stock, use_container_width=True)

        # Department distribution
        if 'department_id' in inventory_df.columns:
            dept_dist = inventory_df['department_id'].value_counts().head(10).reset_index()
            dept_dist.columns = ['Department', 'Count']
            
            fig_dept = px.pie(
                dept_dist,
                names='Department',
                values='Count',
                title="Top 10 Departments by Item Count"
            )
            st.plotly_chart(fig_dept, use_container_width=True)

    if not requests_df.empty:
        # Request Status Distribution
        if 'is_approved' in requests_df.columns:
            status_counts = requests_df['is_approved'].fillna('Pending').value_counts().reset_index()
            status_counts.columns = ['Status', 'Count']
            
            # Map numeric values to readable labels
            status_mapping = {0: 'Pending', 1: 'Approved', 'Pending': 'Pending'}
            status_counts['Status'] = status_counts['Status'].map(status_mapping)
            
            fig_status = px.pie(
                status_counts,
                names='Status',
                values='Count',
                title="Request Status Distribution"
            )
            st.plotly_chart(fig_status, use_container_width=True)

        # Requests over time
        if 'requested_date' in requests_df.columns:
            requests_df['requested_date'] = pd.to_datetime(requests_df['requested_date'], errors='coerce')
            daily_requests = requests_df.groupby(requests_df['requested_date'].dt.date).size().reset_index()
            daily_requests.columns = ['Date', 'Count']
            
            fig_timeline = px.line(
                daily_requests,
                x='Date',
                y='Count',
                title="Daily Request Trends"
            )
            st.plotly_chart(fig_timeline, use_container_width=True)

    # Data Tables
    st.subheader("Raw Data")
    
    # Tabs for different data views
    tab1, tab2 = st.tabs(["Requests Data", "Inventory Data"])
    
    with tab1:
        if not requests_df.empty:
            # Select columns to display
            display_columns = ['id', 'item_name', 'requested_quantity', 'is_approved', 'is_requester_received', 'last_updated']
            available_columns = [col for col in display_columns if col in requests_df.columns]
            
            st.write("**Recent Requests**")
            st.dataframe(
                requests_df[available_columns].tail(20),
                use_container_width=True
            )
            
            # Download button
            csv_requests = requests_df.to_csv(index=False)
            st.download_button(
                label="Download Requests Data as CSV",
                data=csv_requests,
                file_name=f"scm_requests_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        else:
            st.info("No request data available")
    
    with tab2:
        if not inventory_df.empty:
            # Select columns to display
            display_columns = ['id', 'item_name', 'current_stock', 'quantity', 'source', 'last_updated']
            available_columns = [col for col in display_columns if col in inventory_df.columns]
            
            st.write("**Inventory Items**")
            st.dataframe(
                inventory_df[available_columns].tail(20),
                use_container_width=True
            )
            
            # Download button
            csv_inventory = inventory_df.to_csv(index=False)
            st.download_button(
                label="Download Inventory Data as CSV",
                data=csv_inventory,
                file_name=f"scm_inventory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        else:
            st.info("No inventory data available")

    # Auto-refresh logic
    if auto_refresh:
        time.sleep(refresh_interval)
        st.rerun()

    # Close consumers
    if requests_consumer:
        requests_consumer.close()
    if inventory_consumer:
        inventory_consumer.close()

if __name__ == "__main__":
    main()

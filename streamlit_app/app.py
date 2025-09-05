import os
import streamlit as st

kafka_bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

st.set_page_config(page_title="OKR Kafka Dashboard", layout="wide")

st.title("OKR Streamlit Dashboard")
st.write("This dashboard runs at the server root and proxies via Nginx.")

st.subheader("Kafka Configuration")
st.code(f"Bootstrap servers: {kafka_bootstrap}")

st.info("Use /kafka for Kafdrop UI and /airflow for Airflow UI.")

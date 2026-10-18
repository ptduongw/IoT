import streamlit as st
import pandas as pd
from influxdb_client import InfluxDBClient
import plotly.graph_objects as go
from config import *

st.set_page_config(page_title="IoT Dashboard", layout="wide")

st.title("📊 IoT Lab 2 Dashboard")
st.markdown(f"**Student:** B23DCCN224 | **Status:** Live Monitoring")

# Connect InfluxDB
@st.cache_resource
def get_client():
    return InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)

client = get_client()
query_api = client.query_api()

# Query data
@st.cache_data(ttl=5)
def get_data():
    query = f'''
from(bucket:"{INFLUXDB_BUCKET_RAW}")
  |> range(start: -1h)
  |> filter(fn:(r) => r._measurement == "environment")
  |> pivot(rowKey:["_time"], columnKey:["_field"], valueColumn:"_value")
'''
    return query_api.query_data_frame(query)

df = get_data()

if df.empty:
    st.warning("⚠️ No data. Run generate_data.py first!")
else:
    # Metrics
    st.subheader("📊 Latest Values")
    latest = df.iloc[-1]
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🌡️ Temperature", f"{latest['temperature']:.1f}°C")
    col2.metric("💧 Humidity", f"{latest['humidity']:.1f}%")
    col3.metric("📏 Distance", f"{latest['distance_cm']:.1f}cm")
    col4.metric("📡 RSSI", f"{latest['rssi']:.0f}dBm")
    
    # Charts
    st.subheader("📈 Data Trends")
    
    # Chart 1: Temp & Humidity
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=df['_time'], y=df['temperature'], 
                              name='Temperature', line=dict(color='red')))
    fig1.add_trace(go.Scatter(x=df['_time'], y=df['humidity'],
                              name='Humidity', line=dict(color='blue'), yaxis='y2'))
    fig1.update_layout(
        title="Temperature & Humidity",
        yaxis=dict(title="Temp (°C)"),
        yaxis2=dict(title="Humidity (%)", overlaying='y', side='right'),
        hovermode='x unified', height=400
    )
    st.plotly_chart(fig1, use_container_width=True)
    
    # Chart 2: Distance
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=df['_time'], y=df['distance_cm'],
                              name='Distance', line=dict(color='green')))
    fig2.update_layout(title="Distance", hovermode='x unified', height=400)
    st.plotly_chart(fig2, use_container_width=True)
    
    # Data Table
    st.subheader("📋 Raw Data")
    display_cols = ['_time', 'temperature', 'humidity', 'distance_cm', 'rssi']
    st.dataframe(df[display_cols].tail(20), use_container_width=True)
    
    st.success(f"✅ Total records: {len(df)}")

st.divider()
st.caption("🔄 Updates every 5 seconds | IoT Lab 2")
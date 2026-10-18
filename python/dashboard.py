import streamlit as st
import pandas as pd
from influxdb_client import InfluxDBClient
import plotly.graph_objects as go
from datetime import datetime
from config import *

# ========== PAGE CONFIG ==========
st.set_page_config(
    page_title="IoT Lab2 Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("🌡️ IoT Lab 2 Dashboard")
st.markdown(f"**Student:** B23DCCN224 | **Group:** N11")

# ========== CONNECT INFLUXDB ==========
@st.cache_resource
def connect_influxdb():
    return InfluxDBClient(
        url=INFLUXDB_URL, 
        token=INFLUXDB_TOKEN, 
        org=INFLUXDB_ORG
    )

try:
    client = connect_influxdb()
    query_api = client.query_api()
    st.success("✅ Connected to InfluxDB")
except Exception as e:
    st.error(f"❌ Failed to connect: {e}")
    st.stop()

# ========== QUERY FUNCTIONS ==========
@st.cache_data(ttl=10)
def get_raw_data(hours=1):
    """Query raw data from bucket 'iot'"""
    query = f'''
from(bucket:"{INFLUXDB_BUCKET_RAW}")
  |> range(start: -{hours}h)
  |> filter(fn:(r) => r._measurement == "environment")
  |> pivot(rowKey:["_time"], columnKey:["_field"], valueColumn:"_value")
'''
    try:
        res = query_api.query_data_frame(query)
        if isinstance(res, list):
            res = pd.concat(res, ignore_index=True) if res else pd.DataFrame()
        return res
    except Exception as e:
        st.error(f"Query error: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=10)
def get_processed_data(hours=1):
    """Query processed data from bucket 'processed'"""
    query = f'''
from(bucket:"{INFLUXDB_BUCKET_PROCESSED}")
  |> range(start: -{hours}h)
  |> filter(fn:(r) => r._measurement == "environment_clean")
  |> pivot(rowKey:["_time"], columnKey:["_field"], valueColumn:"_value")
'''
    try:
        res = query_api.query_data_frame(query)
        if isinstance(res, list):
            res = pd.concat(res, ignore_index=True) if res else pd.DataFrame()
        return res
    except Exception as e:
        return pd.DataFrame()

# ========== SIDEBAR ==========
with st.sidebar:
    st.header("⚙️ Settings")
    time_range = st.selectbox(
        "Time Range",
        ["1h", "6h", "24h"]
    )
    hours_map = {"1h": 1, "6h": 6, "24h": 24}
    hours = hours_map[time_range]
    
    st.divider()
    st.write("**Status:**")
    st.info("🔄 Data updates every 10 seconds")

# ========== LOAD DATA ==========
df_raw = get_raw_data(hours)
df_proc = get_processed_data(hours)

# ========== CHECK DATA ==========
if df_raw.empty:
    st.warning("⚠️ No raw data. Please run:")
    st.code("python subscriber.py")
    st.code("python generate_data.py")
    st.stop()

# ========== METRICS ROW ==========
st.subheader("📊 Latest Readings")

latest = df_raw.iloc[-1]

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    temp_val = latest.get('temperature', 'N/A')
    st.metric("🌡️ Temperature", 
              f"{temp_val:.1f}°C" if temp_val != 'N/A' else temp_val)

with col2:
    hum_val = latest.get('humidity', 'N/A')
    st.metric("💧 Humidity",
              f"{hum_val:.1f}%" if hum_val != 'N/A' else hum_val)

with col3:
    dist_val = latest.get('distance_cm', 'N/A')
    st.metric("📏 Distance",
              f"{dist_val:.1f} cm" if dist_val != 'N/A' else dist_val)

with col4:
    rssi_val = latest.get('rssi', 'N/A')
    st.metric("📡 RSSI",
              f"{rssi_val:.0f} dBm" if rssi_val != 'N/A' else rssi_val)

with col5:
    seq_val = latest.get('sequence', 'N/A')
    st.metric("📦 Sequence",
              f"{int(seq_val)}" if seq_val != 'N/A' else seq_val)

# ========== CHARTS ==========
st.subheader("📈 Raw Data Charts")

# Chart 1: Temperature & Humidity
fig1 = go.Figure()

fig1.add_trace(go.Scatter(
    x=df_raw['_time'],
    y=df_raw['temperature'],
    mode='lines+markers',
    name='Temperature (°C)',
    line=dict(color='red')
))

fig1.add_trace(go.Scatter(
    x=df_raw['_time'],
    y=df_raw['humidity'],
    mode='lines+markers',
    name='Humidity (%)',
    line=dict(color='blue'),
    yaxis='y2'
))

fig1.update_layout(
    title="Temperature & Humidity",
    xaxis_title="Time",
    yaxis_title="Temperature (°C)",
    yaxis2=dict(
        title="Humidity (%)",
        overlaying='y',
        side='right'
    ),
    hovermode='x unified',
    height=400
)

st.plotly_chart(fig1, use_container_width=True)

# Chart 2: Distance
fig2 = go.Figure()

fig2.add_trace(go.Scatter(
    x=df_raw['_time'],
    y=df_raw['distance_cm'],
    mode='lines+markers',
    name='Distance (cm)',
    line=dict(color='green', width=2)
))

fig2.update_layout(
    title="Distance Measurement",
    xaxis_title="Time",
    yaxis_title="Distance (cm)",
    hovermode='x unified',
    height=400
)

st.plotly_chart(fig2, use_container_width=True)

# Chart 3: RSSI
fig3 = go.Figure()

fig3.add_trace(go.Scatter(
    x=df_raw['_time'],
    y=df_raw['rssi'],
    mode='lines+markers',
    name='RSSI (dBm)',
    line=dict(color='purple')
))

fig3.update_layout(
    title="Signal Strength",
    xaxis_title="Time",
    yaxis_title="RSSI (dBm)",
    hovermode='x unified',
    height=400
)

st.plotly_chart(fig3, use_container_width=True)

# Chart 4: Latency
if 'latency_ms' in df_raw.columns:
    fig_latency = go.Figure()
    fig_latency.add_trace(go.Scatter(
        x=df_raw['_time'],
        y=df_raw['latency_ms'],
        mode='lines+markers',
        name='Latency (ms)',
        line=dict(color='orange')
    ))
    fig_latency.update_layout(
        title="End-to-End Latency",
        xaxis_title="Time",
        yaxis_title="Latency (ms)",
        hovermode='x unified',
        height=400
    )
    st.plotly_chart(fig_latency, use_container_width=True)

# ========== PROCESSED DATA SECTION ==========
if not df_proc.empty:
    st.subheader("✨ Processed Data (After Preprocessing)")
    
    fig4 = go.Figure()
    
    if 'temperature_norm' in df_proc.columns:
        fig4.add_trace(go.Scatter(
            x=df_proc['_time'],
            y=df_proc['temperature_norm'],
            mode='lines',
            name='Temperature (normalized)',
            line=dict(color='red')
        ))
    
    if 'humidity_norm' in df_proc.columns:
        fig4.add_trace(go.Scatter(
            x=df_proc['_time'],
            y=df_proc['humidity_norm'],
            mode='lines',
            name='Humidity (normalized)',
            line=dict(color='blue')
        ))
    
    if 'distance_cm_norm' in df_proc.columns:
        fig4.add_trace(go.Scatter(
            x=df_proc['_time'],
            y=df_proc['distance_cm_norm'],
            mode='lines',
            name='Distance (normalized)',
            line=dict(color='green')
        ))
    
    fig4.update_layout(
        title="Normalized Features (MinMax Scaling [0,1])",
        xaxis_title="Time",
        yaxis_title="Value",
        hovermode='x unified',
        height=400
    )
    
    st.plotly_chart(fig4, use_container_width=True)

# ========== STATISTICS TABLE ==========
st.subheader("📊 Data Statistics")

col_stat1, col_stat2 = st.columns(2)

with col_stat1:
    st.write("**Raw Data Summary**")
    summary = df_raw[['temperature', 'humidity', 'distance_cm']].describe().round(2)
    st.dataframe(summary, use_container_width=True)

with col_stat2:
    st.write("**Data Quality**")
    quality = {
        'Metric': ['Total Records', 'NaN Values', 'Time Span'],
        'Value': [
            len(df_raw),
            df_raw[['temperature', 'humidity', 'distance_cm']].isnull().sum().sum(),
            f"{(df_raw['_time'].max() - df_raw['_time'].min()).total_seconds() / 60:.1f} min"
        ]
    }
    st.dataframe(pd.DataFrame(quality), use_container_width=True, hide_index=True)

# ========== DATA TABLE ==========
st.subheader("📋 Recent Data")

view_tab = st.radio("View", ["Raw Data", "Processed Data"], horizontal=True)

if view_tab == "Raw Data":
    display_cols = ['_time', 'temperature', 'humidity', 'distance_cm', 'rssi', 'sequence']
    display_cols = [col for col in display_cols if col in df_raw.columns]
    st.dataframe(
        df_raw[display_cols].tail(20),
        use_container_width=True,
        hide_index=True
    )
else:
    if not df_proc.empty:
        display_cols = ['_time', 'temperature_norm', 'humidity_norm', 'distance_cm_norm']
        display_cols = [col for col in display_cols if col in df_proc.columns]
        st.dataframe(
            df_proc[display_cols].tail(20),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("⏳ Run preprocess.py to see processed data")

# ========== FOOTER ==========
st.divider()
col_f1, col_f2, col_f3 = st.columns([1, 2, 1])

with col_f1:
    st.metric("Records", len(df_raw))

with col_f2:
    st.write(f"🕐 Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

with col_f3:
    st.metric("Status", "OK" if len(df_raw) > 0 else "Error")

st.caption("Made with ❤️ for IoT Lab 2")
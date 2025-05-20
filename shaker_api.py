import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import base64
import altair as alt
import time
import requests
from streamlit_extras.colored_header import colored_header
from streamlit_extras.let_it_rain import rain

st.set_page_config(page_title="🛠️ Shaker Intelligence Dashboard", layout="wide", page_icon="🔧")

colored_header("Shaker Intelligence Dashboard", description="Live monitoring and ML alerts for shaker screen performance", color_name="blue-70")

uploaded_file = st.file_uploader("📂 Upload drilling sensor CSV file", type=["csv"])

@st.cache_data(show_spinner=False)
def load_data(file):
    df = pd.read_csv(file, low_memory=False)
    df.replace(-999.25, np.nan, inplace=True)
    return df

def create_download_link(df):
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="shaker_report.csv">📥 Download Analysis Report as CSV</a>'
    return href

if uploaded_file:
    df_full = load_data(uploaded_file)
    st.sidebar.header("⚙️ Settings")
    reset_life = st.sidebar.checkbox("🔄 Reset Shaker Life After Maintenance")
    failure_threshold = st.sidebar.slider("🚨 Failure Threshold (%)", 0, 100, 30)
    simulate_live = st.sidebar.toggle("📡 Simulate Live Monitoring", value=True)
    hours_to_simulate = st.sidebar.slider("🕒 Hours to Simulate", 1, 24, 1)

    df_full['SHAKER Output'] = df_full.get('SHAKER #1 (Units)', 0).fillna(0) + df_full.get('SHAKER #2 (Units)', 0).fillna(0)
    df_full['Timestamp'] = pd.to_datetime(df_full['YYYY/MM/DD'] + ' ' + df_full['HH:MM:SS'], errors='coerce')

    if simulate_live:
        st.subheader("📊 Simulated Live Shaker Output (per hour)")
        chart_placeholder = st.empty()
        status_placeholder = st.empty()
        chart_df = pd.DataFrame(columns=['SHAKER Output'])

        total_points = len(df_full)
        chunk_size = int(total_points / hours_to_simulate)

        for i in range(chunk_size, total_points + chunk_size, chunk_size):
            batch_df = df_full.iloc[:i].copy()
            chart_df = batch_df[['Timestamp', 'SHAKER Output']].copy().dropna()
            chart_df = chart_df.set_index('Timestamp')

            # Add warning status by threshold check (e.g., low output)
            recent_output = batch_df['SHAKER Output'].iloc[-1] if not batch_df['SHAKER Output'].empty else 0
            status_msg = "🟢 Normal"
            if recent_output < 100:
                status_msg = "🟡 Moderate Load"
            if recent_output < 50:
                status_msg = "🔴 Low Output Alert"

            chart_placeholder.line_chart(chart_df)
            status_placeholder.markdown(f"### ⏱️ Latest Status: {status_msg} — Output = {recent_output:.1f} units")
            time.sleep(1.5)

        rain(emoji="💧", font_size=24, falling_speed=4, animation_length="medium")
        st.success("✅ Hour-wise simulation complete")

    if st.button("🚀 Run ML Analysis via API"):
        st.info("📨 Sending data to backend API for analysis...")
        try:
            api_url = "http://localhost:8000/analyze"
            files = {"file": uploaded_file.getvalue()}
            params = {"reset_life": reset_life, "failure_threshold": failure_threshold}
            response = requests.post(api_url, files={"file": uploaded_file}, params=params)

            if response.status_code == 200:
                result = response.json()
                st.success("✅ Analysis Complete")

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("📊 Screen Utilization", f"{result['Screen Utilization (%)']:.1f}%")
                with col2:
                    st.metric("⏳ Screen Life Remaining", f"{result['Screen Life Remaining (%)']:.1f}%")
                with col3:
                    st.metric("📉 G-Force Alert", result['G-Force Drop Alert'])
                with col4:
                    st.metric("⚙️ Shaker Life Left", f"{result['Shaker Life Remaining (%)']:.1f}%", delta=result['Shaker Status'])
            else:
                st.error(f"❌ API Error {response.status_code}: {response.text}")
        except Exception as e:
            st.error(f"⚠️ Backend communication failed: {str(e)}")

    st.markdown("---")
    st.subheader("📋 Data Snapshot")
    st.dataframe(df_full.tail(50), use_container_width=True)
    st.markdown(create_download_link(df_full), unsafe_allow_html=True)
else:
    st.info("🛠️ Please upload a CSV file to begin monitoring.")

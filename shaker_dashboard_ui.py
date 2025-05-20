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
    batch_size = st.sidebar.slider("📈 Live Update Interval (rows)", 10, 1000, 100, step=10)

    df_full['SHAKER Output'] = df_full.get('SHAKER #1 (Units)', 0).fillna(0) + df_full.get('SHAKER #2 (Units)', 0).fillna(0)

    if simulate_live:
        st.subheader("📊 Simulated Live Shaker Output")
        progress_chart = st.empty()
        chart_df = pd.DataFrame(columns=['SHAKER Output'])
        for i in range(batch_size, len(df_full), batch_size):
            batch_df = df_full.iloc[:i].copy()
            chart_df = batch_df[['SHAKER Output']].copy().reset_index(drop=True)
            progress_chart.line_chart(chart_df)
            time.sleep(1)
        rain(emoji="💧", font_size=24, falling_speed=4, animation_length="medium")
        st.success("✅ Live feed simulation complete")

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

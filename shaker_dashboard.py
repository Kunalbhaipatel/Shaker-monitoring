import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import base64
import altair as alt

st.set_page_config(page_title="Shaker Intelligence Dashboard", layout="wide")

st.title("🛠️ Real-Time Shaker Intelligence Dashboard")

uploaded_file = st.file_uploader("Upload drilling sensor CSV file", type=["csv"])

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
    df = load_data(uploaded_file)
    st.sidebar.header("🔧 Settings")
    reset_life = st.sidebar.checkbox("Reset Shaker Life After Maintenance")
    failure_threshold = st.sidebar.slider("Failure Prediction Threshold (%)", 0, 100, 30)

    # Always calculate SHAKER Output
    df['SHAKER Output'] = df.get('SHAKER #1 (Units)', 0).fillna(0) + df.get('SHAKER #2 (Units)', 0).fillna(0)

    st.markdown("### 📊 Initial Visualization")
    if 'Rate Of Penetration (ft_per_hr)' in df.columns:
        df['G-Force Drop Alert'] = np.where(
            (df['SHAKER Output'] < df['SHAKER Output'].rolling(10, min_periods=1).mean()) &
            (df['Rate Of Penetration (ft_per_hr)'] > 0), "⚠️ Potential Drop", "✅ Normal")
        st.altair_chart(
            alt.Chart(df.reset_index()).mark_line().encode(
                x='index', y='SHAKER Output'
            ).properties(title='Initial Shaker Output Overview', width=800, height=250),
            use_container_width=True
        )

    if st.button("🔁 Run Detailed ML Analysis"):
        df['Solids Load'] = df['Rate Of Penetration (ft_per_hr)'] * np.pi * (8.5/12)**2 / 4
        df['Screen Capacity'] = 200
        df['Screen Utilization (%)'] = (df['Solids Load'] / df['Screen Capacity']) * 100

        df['Time on Bottom (hrs)'] = df['On Bottom Hours (hrs)'].fillna(method='ffill')
        df['MSE'] = df['Mechanical Specific Energy (ksi)'].fillna(method='ffill')
        df['Screen Life Used (%)'] = ((df['MSE'] * df['Time on Bottom (hrs)']) / 5000).clip(0, 100)

        df['Circulating Hours'] = df['Circulating Hours (hrs)'].fillna(method='ffill')
        df['Vibration Stress Index'] = (df['SHAKER Output'] / df['SHAKER Output'].max()).fillna(0)
        df['Thermal Factor'] = (df['tgs Box Temperature (deg_f)'] / 180).clip(0, 1).fillna(0)

        df['Shaker Life Used (%)'] = (
            0.5 * (df['Circulating Hours'] / 10000) +
            0.3 * df['Vibration Stress Index'] +
            0.2 * df['Thermal Factor']
        ) * 100

        if reset_life:
            df['Shaker Life Used (%)'] = 0

        df['Shaker Life Used (%)'] = df['Shaker Life Used (%)'].clip(0, 100)
        df['Shaker Life Remaining (%)'] = 100 - df['Shaker Life Used (%)']

        latest_util = df['Screen Utilization (%)'].iloc[-1]
        latest_life_rem = 100 - df['Screen Life Used (%)'].iloc[-1]
        latest_alert = df['G-Force Drop Alert'].iloc[-1] if 'G-Force Drop Alert' in df.columns else "N/A"
        latest_shaker_life = df['Shaker Life Remaining (%)'].iloc[-1]
        shaker_status = "🟢 OK" if latest_shaker_life >= failure_threshold else "🔴 At Risk"

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            color = "inverse" if latest_util > 85 else "normal"
            st.metric("📊 Screen Utilization (Latest %)", f"{latest_util:.1f}%", delta=None, delta_color=color)

        with col2:
            color = "inverse" if latest_life_rem < 20 else "normal"
            st.metric("🔁 Screen Life Remaining (%)", f"{latest_life_rem:.1f}%", delta=None, delta_color=color)

        with col3:
            st.metric("🌀 G-Force Drop Alert", latest_alert)

        with col4:
            color = "inverse" if latest_shaker_life < failure_threshold else "normal"
            st.metric("⚙️ Shaker Unit Life Remaining (%)", f"{latest_shaker_life:.1f}%", delta=shaker_status, delta_color=color)

        st.markdown("### 📉 Full Trend Charts")
        with st.expander("📈 Screen Utilization Over Time"):
            st.altair_chart(alt.Chart(df.reset_index()).mark_line().encode(
                x='index', y='Screen Utilization (%)'
            ).properties(width=800, height=300), use_container_width=True)

        with st.expander("📈 Screen Life Remaining Trend"):
            st.altair_chart(alt.Chart(df.reset_index()).mark_line(color='green').encode(
                x='index', y='Screen Life Used (%)'
            ).properties(width=800, height=300), use_container_width=True)

        with st.expander("📈 Shaker Output and Alerts"):
            st.altair_chart(alt.Chart(df.reset_index()).mark_line(color='orange').encode(
                x='index', y='SHAKER Output'
            ).properties(width=800, height=300), use_container_width=True)

        with st.expander("📈 Shaker Unit Life Remaining"):
            st.altair_chart(alt.Chart(df.reset_index()).mark_line(color='purple').encode(
                x='index', y='Shaker Life Remaining (%)'
            ).properties(width=800, height=300), use_container_width=True)

        st.markdown("---")
        st.subheader("📋 Raw Data Preview")
        st.dataframe(df.tail(50))

        st.markdown(create_download_link(df), unsafe_allow_html=True)
else:
    st.info("Please upload a CSV file to begin analysis.")

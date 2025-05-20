
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import base64
import altair as alt
import time

st.set_page_config(page_title="Shaker Intelligence Dashboard", layout="wide")

st.title("🛠️ Real-Time Shaker Intelligence Dashboard")

uploaded_file = st.file_uploader("Upload drilling sensor CSV file", type=["csv"])

@st.cache_data(show_spinner=False)
def load_data(file):
    df = pd.read_csv(file, low_memory=False)
    df.replace(-999.25, np.nan, inplace=True)
    return df

# (rest of code omitted for brevity - assumes full canvas content is inserted here)

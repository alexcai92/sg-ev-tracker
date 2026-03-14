import streamlit as st
import requests
import pandas as pd
import folium
from streamlit_folium import st_folium

# 1. Setup Page Config
st.set_page_config(page_title="SG EV Live", layout="wide")
st.title("⚡ Singapore Live EV Charger Tracker")

# 2. Securely get your API Key (We will set this up in Step 4)
LTA_KEY = st.secrets["LTA_ACCOUNT_KEY"]

# 3. Fetch Data from LTA
@st.cache_data(ttl=300) # Refreshes every 5 minutes
def get_lta_data():
    url = "https://datamall2.mytransport.sg/ltaodataservice/EVCBatch"
    headers = {'AccountKey': LTA_KEY, 'accept': 'application/json'}
    response = requests.get(url, headers=headers)
    return response.json()['value']

try:
    data = get_lta_data()
    df = pd.DataFrame(data)

    # 4. Create Sidebar Filters
    st.sidebar.header("Filters")
    provider = st.sidebar.multiselect("Select Provider", options=df['Operator'].unique())
    
    if provider:
        df = df[df['Operator'].isin(provider)]

    # 5. Display Map
    st.subheader("Charger Map")
    m = folium.Map(location=[1.3521, 103.8198], zoom_start=12)
    
    for _, row in df.iterrows():
        folium.Marker(
            location=[row['Latitude'], row['Longitude']],
            popup=f"Operator: {row['Operator']}<br>Address: {row['Address']}",
            icon=folium.Icon(color="green", icon="flash", prefix="fa")
        ).add_to(m)

    st_folium(m, width=1000, height=500)

    # 6. Display Data Table
    st.subheader("Raw Data")
    st.dataframe(df)

except Exception as e:
    st.error(f"Could not load data. Did you set your API Key? Error: {e}")

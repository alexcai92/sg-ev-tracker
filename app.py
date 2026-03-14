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
@st.cache_data(ttl=300)
def get_lta_data():
    # Step 1: Request the temporary download link
    url = "https://datamall2.mytransport.sg/ltaodataservice/EVCBatch"
    headers = {'AccountKey': LTA_KEY, 'accept': 'application/json'}
    
    response = requests.get(url, headers=headers)
    res_json = response.json()
    
    # Step 2: Extract the link from the response
    # EVCBatch returns a dictionary like: {"Link": "https://dm-traffic...s3.amazonaws..."}
    data_url = res_json.get('Link')
    
    if not data_url:
        st.error("LTA did not return a download link. Check your API Key.")
        return []

    # Step 3: Follow the link to get the actual JSON data
    actual_data_res = requests.get(data_url)
    actual_data = actual_data_res.json()
    
    # Step 4: Access the list inside the file
    # Even in the batch file, LTA usually wraps the list in a 'value' key
    return actual_data.get('value', [])

# Temporary debug lines
raw_data = get_lta_data()
st.write("First item in the data:", raw_data[0] if raw_data else "Empty list")

df = pd.DataFrame(raw_data)
st.write("Columns found by Python:", df.columns.tolist())
# End of temporary

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

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
# 3.1 Get the link from LTA
@st.cache_data(ttl=300) # Refreshes every 5 minutes
def get_lta_data():
    url = "https://datamall2.mytransport.sg/ltaodataservice/EVCBatch"
    headers = {'AccountKey': LTA_KEY, 'accept': 'application/json'}
    
    response = requests.get(url, headers=headers)
    res_json = response.json()

    # 3.2 Extract the URL from the response
    data_url = res_json.get('Link') or res_json.get('value')
    
    if not data_url or not isinstance(data_url, str):
        st.error("Could not find a valid data link in the API response.")
        return []

    # 3.3 Download the actual JSON file from that link
    actual_data_res = requests.get(data_url)
    actual_data = actual_data_res.json()
    
    # 3.4 Access the 'value' inside that downloaded file
    # Most LTA JSON files still wrap the list in a 'value' key
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

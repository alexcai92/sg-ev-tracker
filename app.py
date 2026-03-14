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
    url = "https://datamall2.mytransport.sg/ltaodataservice/EVCBatch"
    headers = {'AccountKey': LTA_KEY, 'accept': 'application/json'}
    
    try:
        # Step 1: Get the Link
        res = requests.get(url, headers=headers)
        res_json = res.json()
        
        # Step 2: Unpack the link carefully
        # Based on your JSON: it's in value[0]['Link']
        data_url = res_json['value'][0]['Link']
        
        # Step 3: Fetch the actual data from the S3 link
        actual_res = requests.get(data_url)
        actual_data = actual_res.json()
        
        # Step 4: The final data list is usually inside 'value' in the S3 file too
        if isinstance(actual_data, dict) and 'value' in actual_data:
            return actual_data['value']
        return actual_data # If it's already a list, return it
    except Exception as e:
        st.error(f"Function Error: {e}")
        return []

# --- MAIN APP LOGIC ---
raw_list = get_lta_data()

if not raw_list:
    st.error("No data found. Check your LTA_ACCOUNT_KEY in Streamlit Secrets.")
else:
    df = pd.DataFrame(raw_list)
    
    # DEBUG: This will show you exactly what the column names are
    st.write("Columns found in your data:", df.columns.tolist())
    
    # Check if Operator exists (it might be 'operator' or 'Provider')
    if 'Operator' in df.columns:
        st.success("Operator column found!")
        st.dataframe(df.head(5)) # This is your 5-row preview
    else:
        st.warning("'Operator' column missing. Look at the column list above and find the right name!")

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

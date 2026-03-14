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
    # Step 1: Call EVCBatch to get the temporary download link
    url = "https://datamall2.mytransport.sg/ltaodataservice/EVCBatch"
    headers = {'AccountKey': LTA_KEY, 'accept': 'application/json'}
    
    response = requests.get(url, headers=headers)
    res_json = response.json()
    
    # Step 2: Navigate the JSON structure: value -> first item [0] -> Link
    try:
        # Get the 'value' list
        value_list = res_json.get('value', [])
        
        if not value_list:
            st.error("The 'value' list is empty. Check your API Key.")
            return []
            
        # Get the 'Link' string from the first item
        data_url = value_list[0].get('Link')
        
        if not data_url:
            st.error("Could not find 'Link' inside the value list.")
            return []

        # Step 3: Use the Link to download the actual JSON file
        # This link points to the S3 bucket shown in your response
        actual_data_res = requests.get(data_url)
        actual_data = actual_data_res.json()
        
        # Step 4: Access the final list of chargers
        # Note: Even in the downloaded file, LTA usually puts data in a 'value' key
        return actual_data.get('value', [])

    except Exception as e:
        st.error(f"Error parsing API response: {e}")
        return []

# Execution
data = get_lta_data()

if data:
    df = pd.DataFrame(data)
    st.success(f"Successfully downloaded {len(df)} chargers from S3!")
    
    # Check if Operator exists now
    if 'Operator' in df.columns:
        st.write("Operator column found! Ready for filtering.")
    else:
        st.warning(f"Operator not found. Available columns: {df.columns.tolist()}")
        
    st.dataframe(df.head()) # Preview the first 5 rows

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

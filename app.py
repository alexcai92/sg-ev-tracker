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
        # Step 1: Get S3 Link
        res = requests.get(url, headers=headers)
        data_url = res.json()['value'][0]['Link']
        
        # Step 2: Get the actual File
        actual_res = requests.get(data_url)
        full_data = actual_res.json()
        
        # Step 3: Flatten the nested data
        flattened_rows = []
        locations = full_data.get('evLocationsData', [])
        
        for loc in locations:
            # Extract location-level info
            base_info = {
                "Address": loc.get('address'),
                "Name": loc.get('name'),
                "Latitude": loc.get('latitude'),
                "Longitude": loc.get('longtitude'), # Note the spelling in your JSON!
                "PostalCode": loc.get('postalCode')
            }
            
            # Drill into chargingPoints
            for cp in loc.get('chargingPoints', []):
                # Create a copy of base info and add point-level info
                row = base_info.copy()
                row["Operator"] = cp.get('operator')
                row["Status"] = cp.get('status')
                row["Position"] = cp.get('position')
                
                # Optionally drill into plugTypes for price
                plugs = cp.get('plugTypes', [])
                if plugs:
                    row["Price"] = plugs[0].get('price')
                    row["Power"] = plugs[0].get('powerRating')
                
                flattened_rows.append(row)
                
        return flattened_rows
        
    except Exception as e:
        st.error(f"Error flattening data: {e}")
        return []

# --- Main App ---
data = get_lta_data()
if data:
    df = pd.DataFrame(data)
    st.success(f"Successfully mapped {len(df)} charging points!")
    
    # Now 'Operator' exists because we manually created it in the loop above!
    st.dataframe(df.head())
    
    # Update Map logic to use 'Longitude' (correcting the LTA typo 'longtitude')
    # ... your folium code here ...

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

#except Exception as e:
#    st.error(f"Could not load data. Did you set your API Key? Error: {e}")

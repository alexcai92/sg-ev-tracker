import streamlit as st
import requests
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster

# 1. Setup Page Config
st.set_page_config(page_title="SG EV Chargers", layout="wide")
st.title("⚡ Singapore EV Chargers Live Status")

# 2. Securely get your API Key
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
                    row["PowerType"] = plugs[0].get('current') # Captures 'AC' or 'DC'
                    row["PowerRating"] = plugs[0].get('powerRating')
                
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

# Display Data Table
    st.subheader("Chargers Table")
    st.dataframe(df)
    
# Display Map
    st.subheader("Chargers Map")

    # 1. Create the base map
    m = folium.Map(location=[1.3521, 103.8198], zoom_start=12)
    
    # 2. Initialize the Cluster Layer
    marker_cluster = MarkerCluster().add_to(m)

    # Helper function for colors
    def get_marker_color(power_type):
        if power_type == "DC":
            return "orange" # Fast Charger
        return "green"      # Standard AC Charger
    
    # 3. Add markers to the CLUSTER instead of the MAP
    for _, row in df.iterrows():
        # Use the spelling from your JSON ('latitude' and 'longtitude')
        lat, lon = row['Latitude'], row['Longitude']
        p_type = row.get('PowerType', 'AC')
        p_rating = row.get('PowerRating', 'Unknown')
        
        if pd.notnull(lat) and pd.notnull(lon):
            color = get_marker_color(p_type)
            
            popup_text = f"""
            <b>{row['Operator']}</b><br>
            {row['Address']}<br>
            <b>Type:</b> {p_type} ({p_rating}kW)
            """
            
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(popup_text, max_width=300),
                icon=folium.Icon(color=color, icon="bolt", prefix="fa") #icon='flash'
            ).add_to(marker_cluster) # <--- Add to cluster here!
    
    # 4. Display the map using streamlit-folium
    st_folium(m, width=1000, height=500, returned_objects=[])
    
    st.sidebar.markdown("### 🗺️ Map Legend")
    st.sidebar.markdown("🟠 **Orange**: DC Fast Charging")
    st.sidebar.markdown("🟢 **Green**: AC Standard Charging")


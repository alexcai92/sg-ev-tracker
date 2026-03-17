import streamlit as st
import requests
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster

# Define App Links
APP_LINKS = {
    "SP MOBILITY PTE. LTD.": {
        "ios": "https://apps.apple.com/sg/app/sp-utilities-ev-charging/id596749130",
        "android": "https://play.google.com/store/apps/details?id=sg.com.singaporepower.spservices"
    },
    "COMFORTDELGRO ENGIE PTE. LTD.": {
        "ios": "https://apps.apple.com/sg/app/cdg-engie/id1604169726",
        "android": "https://play.google.com/store/apps/details?id=com.cdgengiepilot.evc"
    },
    "SHELL SINGAPORE PTE. LTD.": {
        "ios": "https://apps.apple.com/sg/app/shell-recharge-asia/id6458189524",
        "android": "https://play.google.com/store/apps/details?id=com.zecosystems.shellrechargeasia"
    },
    "CHARGE+ PTE. LTD.": {
        "ios": "https://apps.apple.com/sg/app/charge/id1481750244",
        "android": "https://play.google.com/store/apps/details?id=com.chargeplus.chargeapp"
    },
    "STRIDES YTL PTE. LTD.": {
        "ios": "https://apps.apple.com/sg/app/chargeco/id1664718768",
        "android": "https://play.google.com/store/apps/details?id=com.strides.chargeco"
    },
    "VOLT SINGAPORE PTE. LTD.": {
        "ios": "https://apps.apple.com/sg/app/volt-ev-charging/id1606309147",
        "android": "https://play.google.com/store/apps/details?id=com.evvolt.voltapp"
    }
}

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
        update_timestamp = full_data.get('LastUpdatedTime', 'Unknown')
        
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
                
        return flattened_rows, update_timestamp
        
    except Exception as e:
        st.error(f"Error flattening data: {e}")
        return [], "Unknown"

# --- Main App ---
data, update_timestamp = get_lta_data()
if data:
    df = pd.DataFrame(data)
    st.success(f"Successfully mapped {len(df)} charging points!")
    
# Display Map
    st.subheader("⚡ Charger Map")
    st.info("Pro-tip: Markers are clustered for speed. Double-click a cluster to zoom into that neighborhood.")
    st.caption(f"Data is refreshed every 5 minutes from the LTA DataMall EVCBatch API. Last Updated on **{update_timestamp}**. Allow some time for initial loading of data.")

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
        lat, lon = row['Latitude'], row['Longitude']
        p_type = row.get('PowerType', 'AC')
        p_rating = row.get('PowerRating', 'Unknown')
        
        # Status Mapping Logic
        status_raw = str(row.get('Status', ''))
        if status_raw == "1":
            status_text = "Available"
        elif status_raw == "0":
            status_text = "Occupied"
        else:
            status_text = "Not Available/Faulty"

        # --- LOGIC FOR HYPERLINKED OPERATOR ---
        raw_op = row['Operator']
        display_op = raw_op # Default if not in our list

        if raw_op in APP_LINKS:
            ios_url = APP_LINKS[raw_op]['ios']
            android_url = APP_LINKS[raw_op]['android']
            # Create the hyperlinked version: Name (<a href='ios'>iOS</a> / <a href='android'>Android</a>)
            display_op = f"{raw_op} (<a href='{ios_url}' target='_blank'>iOS</a> / <a href='{android_url}' target='_blank'>Android</a>)"

        if pd.notnull(lat) and pd.notnull(lon):
            color = get_marker_color(p_type)
            
            # --- UPDATED POPUP TEXT ---
            popup_text = f"""
            <b>{row['Name']}</b><br>
            {row['Address']}<br>
            <b>Operator:</b> {display_op}<br>
            <b>Type:</b> {p_type} ({p_rating}kW)<br>
            <b>Price:</b> S$ {row.get('Price', 'N/A')} /kWh<br>
            <b>Location:</b> {row.get('Position', 'N/A')}<br>
            <br>
            <b>Status:</b> {status_text}
            """
            
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(popup_text, max_width=300),
                icon=folium.Icon(color=color, icon="bolt", prefix="fa")
            ).add_to(marker_cluster)
    
    # 4. Display the map using streamlit-folium
    st_folium(m, width=1000, height=500, returned_objects=[])
    
    st.sidebar.markdown("### 🗺️ Map Legend")
    st.sidebar.markdown("🟠 **Orange**: DC Fast Charging")
    st.sidebar.markdown("🟢 **Green**: AC Standard Charging")

# Display Data Table
    st.subheader("Chargers Table")
    st.dataframe(df)
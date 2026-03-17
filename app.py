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
    st.info("INSTRUCTIONS: Input estimated energy (kWh) and parking duration in the sidebar to see estimated costs for each charger. Click on markers to zoom-in for details.")
    st.caption(f"Data is refreshed every 5 minutes from the LTA DataMall EVCBatch API. Last Updated on **{update_timestamp}**. Allow some time for initial loading of data.")

    # 1. Create the base map
    m = folium.Map(location=[1.3521, 103.8198], zoom_start=12)
    
    # 2. Initialize the Cluster Layer
    marker_cluster = MarkerCluster().add_to(m)
    
    # 3. Add markers to the CLUSTER instead of the MAP
    # --- STEP 1: GROUP BY NAME AND POWER TYPE ---
    # We group by both so AC and DC points at the same mall are handled separately
    grouped_df = df.groupby(['Name', 'PowerType']).agg({
        'Address': 'first',
        'Latitude': 'first',
        'Longitude': 'first',
        'Operator': 'first',
        'PowerRating': 'first',
        'Price': 'first',
        'Position': 'first',
        'Status': lambda x: list(x)
    }).reset_index()

    # --- STEP 1A: ADD COST CALCULATOR IN SIDEBAR ---
    st.sidebar.markdown("### 💰 Cost Calculator")

    # kWh Input
    est_kwh = st.sidebar.number_input("Estimated Energy (kWh):", min_value=0.0, value=20.0, step=1.0)

    # Parking Fee Type
    park_type = st.sidebar.radio("Parking Fee Type:", ["Per Hour", "Fixed Fee"])
    park_value = st.sidebar.number_input(f"Enter {park_type} (S$):", min_value=0.0, value=1.20 if park_type == "Per Hour" else 5.00)

    # Duration Input in hh:mm
    duration_str = st.sidebar.text_input("Parking Duration (hh:mm):", value="01:00")

    # --- CONVERT HH:MM TO TOTAL HOURS ---
    try:
        hours, minutes = map(int, duration_str.split(':'))
        total_hours = hours + (minutes / 60.0)
    except ValueError:
        st.sidebar.error("Please use hh:mm format (e.g. 01:30)")
        total_hours = 1.0 # Fallback

    # --- STEP 2: DRAW PINS ---
    for _, row in grouped_df.iterrows():
        lat, lon = row['Latitude'], row['Longitude']
        p_type = row['PowerType']
        p_rating = row.get('PowerRating', 'N/A')
        
        # Calculate availability for this specific group (e.g., all DC points at Mall X)
        statuses = row['Status']
        total_points = len(statuses)
        available_points = statuses.count("1")
        
        # Use your existing color logic: Orange for DC, Green for AC
        # But we change to Red if 0 chargers are available in that group
        if available_points == 0:
            marker_color = "red"
        else:
            marker_color = "orange" if p_type == "DC" else "green"

        # --- STEP 1: CALCULATE PARKING COST ---
        if park_type == "Per Hour":
            parking_cost = park_value * total_hours
        else:
            parking_cost = park_value # Fixed fee

        # --- STEP 2: CALCULATE CHARGING COST ---
        # Ensure Price is a number; LTA sometimes sends empty strings or N/A
        try:
            price_val = float(row.get('Price', 0))
        except (ValueError, TypeError):
            price_val = 0.0

        charging_cost = price_val * est_kwh

        # --- STEP 3: TOTAL COST ---
        total_cost = parking_cost + charging_cost

        # --- LOGIC FOR HYPERLINKED OPERATOR ---
        raw_op = row['Operator']
        display_op = raw_op
        if raw_op in APP_LINKS:
            ios_url = APP_LINKS[raw_op]['ios']
            android_url = APP_LINKS[raw_op]['android']
            display_op = f"{raw_op} (<a href='{ios_url}' target='_blank'>iOS</a> / <a href='{android_url}' target='_blank'>Android</a>)"

        # --- UPDATED POPUP TEXT ---
        if pd.notnull(lat) and pd.notnull(lon):
            popup_text = f"""
            <b>{row['Name']}</b><br>
            {row['Address']}<br>
            <b>Operator:</b> {display_op}<br>
            <hr>
            <b>Type:</b> {p_type} ({row.get('PowerRating', 'N/A')}kW)<br>
            <b>Price:</b> S$ {price_val:.4f} /kWh<br>
            <br>
            <div style="background-color: #f9f9f9; border: 1px solid #ddd; padding: 10px; border-radius: 5px;">
                <b>Total Est. Cost: S$ {total_cost:.2f}</b><br>
                <small>
                    - Charge: ${charging_cost:.2f} ({est_kwh}kWh)<br>
                    - Parking: ${parking_cost:.2f} ({duration_str})
                </small>
            </div>
            <hr>
            <b>Available {p_type} Points: {available_points}/{total_points}</b>
            """
            
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(popup_text, max_width=300),
                icon=folium.Icon(color=marker_color, icon="bolt", prefix="fa")
            ).add_to(marker_cluster)

    # 4. Display the map using streamlit-folium
    st_folium(m, width=1000, height=500, returned_objects=[])

# Display Data Table
    st.subheader("Chargers Table")
    st.dataframe(df)
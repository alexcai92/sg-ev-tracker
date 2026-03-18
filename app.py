import streamlit as st
import requests
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster

# --- 1. Setup Page Config ---
st.set_page_config(page_title="SG EV Chargers", layout="wide")
st.title("⚡ Singapore EV Chargers Live Status")

# Securely get LTA API Key
LTA_KEY = st.secrets["LTA_ACCOUNT_KEY"]

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

# --- 2. Helper Functions ---

@st.cache_data(ttl=300)
def get_lta_data():
    url = "https://datamall2.mytransport.sg/ltaodataservice/EVCBatch"
    headers = {'AccountKey': LTA_KEY, 'accept': 'application/json'}
    try:
        # Step 1: Get S3 Link
        res = requests.get(url, headers=headers)
        data_url = res.json()['value'][0]['Link']
        
        # Step 2: Get the actual File
        full_data = requests.get(data_url).json()
        
        # Step 3: Flatten the nested data
        flattened_rows = []
        locations = full_data.get('evLocationsData', [])
        update_timestamp = full_data.get('LastUpdatedTime', 'Unknown')
        
        for loc in locations:
            base_info = {
                "Address": loc.get('address'),
                "Name": loc.get('name'),
                "Latitude": loc.get('latitude'),
                "Longitude": loc.get('longtitude'),
                "PostalCode": loc.get('postalCode')
            }
            for cp in loc.get('chargingPoints', []):
                row = base_info.copy()
                row["Operator"] = cp.get('operator')
                row["Status"] = cp.get('status')
                row["Position"] = cp.get('position')
                plugs = cp.get('plugTypes', [])
                if plugs:
                    row["Price"] = plugs[0].get('price')
                    row["PowerType"] = plugs[0].get('current')
                    row["PowerRating"] = plugs[0].get('powerRating')
                flattened_rows.append(row)
        return flattened_rows, update_timestamp
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return [], "Unknown"

# --- 3. Sidebar UI (Cost Calculator) ---
st.sidebar.markdown("### 💰 Cost Calculator")
est_kwh = st.sidebar.number_input("Estimated Energy (kWh):", min_value=0.0, value=20.0, step=1.0)
park_type = st.sidebar.radio("Parking Fee Type:", ["Per Hour", "Fixed Fee"])
park_value = st.sidebar.number_input(f"Enter {park_type} (S$):", min_value=0.0, value=1.20 if park_type == "Per Hour" else 5.00)
duration_str = st.sidebar.text_input("Parking Duration (hh:mm):", value="01:00")

try:
    hours, minutes = map(int, duration_str.split(':'))
    total_hours = hours + (minutes / 60.0)
except ValueError:
    st.sidebar.error("Use hh:mm format (e.g. 01:30)")
    total_hours = 1.0

# --- 4. Main App Logic ---
data, update_timestamp = get_lta_data()

if data:
    df = pd.DataFrame(data)
    
    # Grouping logic for map pins
    grouped_df = df.groupby(['Name', 'PowerType']).agg({
        'Address': 'first', 'Latitude': 'first', 'Longitude': 'first',
        'Operator': 'first', 'PowerRating': 'first', 'Price': 'first',
        'Position': 'first', 'Status': lambda x: list(x)
    }).reset_index()

    st.subheader("⚡ Charger Map")
    st.caption(f"Data refreshed every 5 mins. Last Updated: **{update_timestamp}**.")
    st.caption(f"I drive an EV (Tesla Model 3 Highland) and face two common issues: 1. There are no apps or websites that show all charging points in Singapore and their live availability. Tesla’s UI only shows partial third-party chargers without live availability. 2. Sometimes, cheaper electricity pricing is outweighed by higher parking costs. To address these issues, I built a simple web app that aggregates all EV charging points in Singapore, shows their live availability (refreshed every 5 minutes), and provides a calculator to calculate total charging costs, factoring in parking fees. I’m doing this in my free time, so it may not be as polished or bug-free as a professional app. ")

    m = folium.Map(location=[1.3521, 103.8198], zoom_start=12)
    marker_cluster = MarkerCluster().add_to(m)

    for _, row in grouped_df.iterrows():
        lat, lon = row['Latitude'], row['Longitude']
        statuses = row['Status']
        available_points = statuses.count("1")
        total_points = len(statuses)
        
        # Color Logic
        if available_points == 0: 
            marker_color = "red"
        else: 
            marker_color = "orange" if row['PowerType'] == "DC" else "green"

        # Cost Calculations
        parking_cost = park_value * total_hours if park_type == "Per Hour" else park_value
        try: 
            price_val = float(row.get('Price', 0))
        except: 
            price_val = 0.0
        total_cost = parking_cost + (price_val * est_kwh)

        # Operator Hyperlinks
        display_op = row['Operator']
        if display_op in APP_LINKS:
            links = APP_LINKS[display_op]
            display_op += f" (<a href='{links['ios']}' target='_blank'>iOS</a> / <a href='{links['android']}' target='_blank'>Android</a>)"

        if pd.notnull(lat) and pd.notnull(lon):
            popup_html = f"""
            <b>{row['Name']}</b><br>{row['Address']}<br>
            <b>Operator:</b> {display_op}<br><hr>
            <b>Type:</b> {row['PowerType']} ({row.get('PowerRating', 'N/A')}kW)<br>
            <b>Price:</b> S$ {price_val:.4f} /kWh<br>
            <div style="background-color: #f9f9f9; padding: 8px; border-radius: 5px; border: 1px solid #ddd;">
                <b>Total Est. Cost: S$ {total_cost:.2f}</b><br>
                <small>Charge: ${price_val*est_kwh:.2f} | Park: ${parking_cost:.2f}</small>
            </div><hr>
            <b>Available: {available_points}/{total_points}</b>
            """
            folium.Marker(
                [lat, lon], 
                popup=folium.Popup(popup_html, max_width=300),
                icon=folium.Icon(color=marker_color, icon="bolt", prefix="fa")
            ).add_to(marker_cluster)

    st_folium(m, width=1000, height=500, returned_objects=[])

    st.subheader("Chargers Table")
    st.dataframe(df)

import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium
import glob

# Set dashboard layout
st.set_page_config(page_title="GIS Weather Dashboard", layout="wide")
st.title("GIS Weather Data Dashboard")

@st.cache_data
def load_data():
    """Loads and merges the station metadata with the hourly weather data."""
    # 1. Load Station Metadata
    try:
        stations = pd.read_csv("Data1/Station_List_WCOO.csv")
    except FileNotFoundError:
        st.error("Could not find Station_List_WCOO.csv. Please check the 'Data1' folder.")
        return pd.DataFrame()

    # 2. Load Weather Data (Combines all hourly files in Data2)
    weather_files = glob.glob("Data2/Hourly_PMSS_*.csv")
    if not weather_files:
        st.error("No weather data files found in the 'Data2' folder.")
        return pd.DataFrame()
        
    weather_list = [pd.read_csv(f) for f in weather_files]
    weather_data = pd.concat(weather_list, ignore_index=True)
    
    # 3. Merge datasets
    # IMPORTANT: Change 'Station_Name' to match the exact column header in your CSV files
    df = pd.merge(weather_data, stations, on='Station_Name', how='inner')
    
    # 4. Parse datetime
    # IMPORTANT: Change 'Date' and 'Hour' to match your actual column headers
    if 'Date' in df.columns and 'Hour' in df.columns:
        # Create UTC datetime
        df['Datetime_UTC'] = pd.to_datetime(df['Date'].astype(str) + ' ' + df['Hour'].astype(str) + ':00:00')
        # Create MYT datetime (UTC + 8)
        df['Datetime_MYT'] = df['Datetime_UTC'] + pd.Timedelta(hours=8)
        
    return df

# Load the data
df = load_data()

if not df.empty:
    # --- SIDEBAR CONTROLS ---
    st.sidebar.header("Dashboard Controls")
    
    # Timezone Selection
    timezone = st.sidebar.radio("Select Timezone", ["UTC", "MYT"])
    time_col = 'Datetime_UTC' if timezone == "UTC" else 'Datetime_MYT'
    
    # Date Filters (Start/End Year, Month, Date)
    st.sidebar.subheader("Time Range")
    min_date = df[time_col].min().date()
    max_date = df[time_col].max().date()
    
    start_date = st.sidebar.date_input("Start Date", min_date, min_value=min_date, max_value=max_date)
    end_date = st.sidebar.date_input("End Date", max_date, min_value=min_date, max_value=max_date)
    
    # Hour Filters (Start/End Hour)
    start_hour = st.sidebar.slider("Start Hour", 0, 23, 0)
    end_hour = st.sidebar.slider("End Hour", 0, 23, 23)
    
    # Parameter Selection
    st.sidebar.subheader("Parameters")
    # IMPORTANT: Ensure these names exactly match the column headers in your weather CSVs
    available_params = [
        "Rainfall", "Minimum Temperature", "Average Temperature", 
        "Maximum Temperature", "Pressure", "Wind Speed", "Wind Direction"
    ]
    selected_params = st.sidebar.multiselect("Select Data to Plot", available_params, default=["Rainfall"])
    
    # Filter the DataFrame based on user inputs
    mask = (df[time_col].dt.date >= start_date) & \
           (df[time_col].dt.date <= end_date) & \
           (df[time_col].dt.hour >= start_hour) & \
           (df[time_col].dt.hour <= end_hour)
    filtered_df = df.loc[mask]

    # --- GIS MAP ---
    st.subheader("Station Map")
    # IMPORTANT: Change 'Latitude' and 'Longitude' if your CSV headers are different (e.g., 'Lat', 'Lon')
    lat_col, lon_col = 'Latitude', 'Longitude' 
    
    if lat_col in filtered_df.columns and lon_col in filtered_df.columns:
        # Center map on the average coordinates
        center_lat = filtered_df[lat_col].mean()
        center_lon = filtered_df[lon_col].mean()
        m = folium.Map(location=[center_lat, center_lon], zoom_start=6)
        
        # Add markers for each unique station
        unique_stations = filtered_df.drop_duplicates(subset=['Station_Name'])
        for idx, row in unique_stations.iterrows():
            folium.Marker(
                [row[lat_col], row[lon_col]], 
                popup=row['Station_Name'],
                tooltip=row['Station_Name']
            ).add_to(m)
            
        st_folium(m, width=1000, height=400)
    else:
        st.warning("Map cannot be generated: 'Latitude' or 'Longitude' columns not found in your data.")

    # --- DYNAMIC CHARTS ---
    st.subheader("Parameter Analysis")
    
    timeline_params = ["Rainfall", "Minimum Temperature", "Average Temperature", "Maximum Temperature", "Pressure"]
    
    # Generate timeline graphs for selected continuous variables
    for param in selected_params:
        if param in timeline_params:
            if param in filtered_df.columns:
                st.markdown(f"#### {param} Timeline")
                fig = px.line(filtered_df, x=time_col, y=param, color='Station_Name')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.error(f"Column '{param}' not found in your CSV data.")
                
    # Generate pie charts for Wind variables
    if "Wind Speed" in selected_params or "Wind Direction" in selected_params:
        st.markdown("#### Wind Analysis (Pie Charts)")
        col1, col2 = st.columns(2)
        
        with col1:
            if "Wind Speed" in selected_params and "Wind Speed" in filtered_df.columns:
                fig_speed = px.pie(filtered_df, names='Wind Speed', title="Wind Speed Frequency")
                st.plotly_chart(fig_speed, use_container_width=True)
                
        with col2:
            if "Wind Direction" in selected_params and "Wind Direction" in filtered_df.columns:
                fig_dir = px.pie(filtered_df, names='Wind Direction', title="Wind Direction Frequency")
                st.plotly_chart(fig_dir, use_container_width=True)
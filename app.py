import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium
import glob

# --- CONFIGURATION ---
COLUMN_MAP = {
    "Rainfall": "Rainfall",               # UPDATE THIS
    "Minimum Temperature": "MIN_TEMP",    # UPDATE THIS
    "Average Temperature": "DRY",         # UPDATE THIS
    "Maximum Temperature": "MAX_TEMP",    # UPDATE THIS
    "Pressure": "SLP",                    # UPDATE THIS
    "Wind Speed": "WIND_SPD",             # UPDATE THIS
    "Wind Direction": "WIND_DIR"          # UPDATE THIS
}

st.set_page_config(page_title="GIS Weather Dashboard", layout="wide")
st.title("GIS Weather Data Dashboard")

@st.cache_data
def load_data():
    """Loads, merges, and formats date/time for the dataset."""
    try:
        stations = pd.read_csv("Data1/Station_List_WCOO.csv")
    except FileNotFoundError:
        st.error("Station_List_WCOO.csv not found.")
        return pd.DataFrame()

    weather_files = glob.glob("Data2/Hourly_PMSS_*.csv")
    if not weather_files:
        st.error("No weather data files found.")
        return pd.DataFrame()
        
    weather_list = [pd.read_csv(f) for f in weather_files]
    weather_data = pd.concat(weather_list, ignore_index=True)
    
    # Merge using the exact headers from your files
    df = pd.merge(weather_data, stations, on='STATION NAME', how='inner')
    
    # Combine YEAR, MTH, DAY, and HOUR into a Datetime object
    # FIX: Handle meteorological hour '24' by temporarily shifting to 0-23, then adding 1 hour back.
    adjusted_hour = df['HOUR'].astype(int) - 1
    
    df['Datetime_UTC'] = pd.to_datetime(
        df['YEAR'].astype(str) + '-' + 
        df['MTH'].astype(str) + '-' + 
        df['DAY'].astype(str) + ' ' + 
        adjusted_hour.astype(str) + ':00:00'
    ) + pd.Timedelta(hours=1)
    
    # Create MYT datetime (UTC + 8)
    df['Datetime_MYT'] = df['Datetime_UTC'] + pd.Timedelta(hours=8)
        
    return df

df = load_data()

if not df.empty:
    # --- SIDEBAR CONTROLS ---
    st.sidebar.header("Dashboard Controls")
    
    timezone = st.sidebar.radio("Select Timezone", ["UTC", "MYT"])
    time_col = 'Datetime_UTC' if timezone == "UTC" else 'Datetime_MYT'
    
    st.sidebar.subheader("Time Range")
    min_date = df[time_col].min().date()
    max_date = df[time_col].max().date()
    
    start_date = st.sidebar.date_input("Start Date", min_date, min_value=min_date, max_value=max_date)
    end_date = st.sidebar.date_input("End Date", max_date, min_value=min_date, max_value=max_date)
    
    start_hour = st.sidebar.slider("Start Hour", 0, 23, 0)
    end_hour = st.sidebar.slider("End Hour", 0, 23, 23)
    
    st.sidebar.subheader("Parameters")
    selected_params = st.sidebar.multiselect("Select Data to Plot", list(COLUMN_MAP.keys()), default=["Average Temperature"])
    
    # Filter Data
    mask = (df[time_col].dt.date >= start_date) & \
           (df[time_col].dt.date <= end_date) & \
           (df[time_col].dt.hour >= start_hour) & \
           (df[time_col].dt.hour <= end_hour)
    filtered_df = df.loc[mask]

    # --- GIS MAP ---
    st.subheader("Station Map")
    if 'LATITUDE' in filtered_df.columns and 'LONGITUDE' in filtered_df.columns:
        center_lat = filtered_df['LATITUDE'].mean()
        center_lon = filtered_df['LONGITUDE'].mean()
        m = folium.Map(location=[center_lat, center_lon], zoom_start=6)
        
        unique_stations = filtered_df.drop_duplicates(subset=['STATION NAME'])
        for idx, row in unique_stations.iterrows():
            folium.Marker(
                [row['LATITUDE'], row['LONGITUDE']], 
                popup=row['STATION NAME'],
                tooltip=row['STATION NAME']
            ).add_to(m)
            
        st_folium(m, width=1000, height=400)

    # --- DYNAMIC CHARTS ---
    st.subheader("Parameter Analysis")
    
    timeline_params = ["Rainfall", "Minimum Temperature", "Average Temperature", "Maximum Temperature", "Pressure"]
    
    for param in selected_params:
        csv_col = COLUMN_MAP[param]
        
        if param in timeline_params:
            if csv_col in filtered_df.columns:
                st.markdown(f"#### {param} Timeline")
                fig = px.line(filtered_df, x=time_col, y=csv_col, color='STATION NAME')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.error(f"Column '{csv_col}' not found in data.")
                
    if "Wind Speed" in selected_params or "Wind Direction" in selected_params:
        st.markdown("#### Wind Analysis")
        col1, col2 = st.columns(2)
        
        with col1:
            speed_col = COLUMN_MAP["Wind Speed"]
            if "Wind Speed" in selected_params and speed_col in filtered_df.columns:
                fig_speed = px.pie(filtered_df, names=speed_col, title="Wind Speed Frequency")
                st.plotly_chart(fig_speed, use_container_width=True)
                
        with col2:
            dir_col = COLUMN_MAP["Wind Direction"]
            if "Wind Direction" in selected_params and dir_col in filtered_df.columns:
                fig_dir = px.pie(filtered_df, names=dir_col, title="Wind Direction Frequency")
                st.plotly_chart(fig_dir, use_container_width=True)

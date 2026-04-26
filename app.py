from __future__ import annotations

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from folium import Map, TileLayer
from folium.plugins import HeatMap
from streamlit_folium import st_folium

from services.api_clients import EarthquakeClient, WeatherClient
from utils.disaster_rules import (
    analyze_country_city_risk,
    classify_earthquake_risk,
    classify_weather_risk,
    combine_risk_levels,
)

@st.cache_data(ttl=300)
def get_weekly_events(_client):
    return _client.weekly_events()

st.set_page_config(page_title="IoT Emergency Alert System", page_icon="🚨", layout="wide")

st.title(" IoT-Powered Emergency Alert and Disaster Monitoring System")
st.caption("Software-only implementation using third-party weather and earthquake APIs.")

city = st.text_input("Enter city to monitor", value="Gwalior")

# Auto-refresh every 60 seconds for live dashboard updates.
components.html(
    """
    <script>
      setTimeout(function () { window.parent.location.reload(); }, 60000);
    </script>
    """,
    height=0,
)

with st.sidebar:
    st.header("Detection Settings")
    radius = st.slider("Earthquake radius (km)", min_value=100, max_value=2000, value=500, step=50)
    min_mag = st.slider("Minimum earthquake magnitude", min_value=1.0, max_value=7.0, value=2.5, step=0.1)
    lookback = st.slider("Lookback window (hours)", min_value=6, max_value=168, value=48, step=6)

if st.button("Fetch Live Monitoring Data", type="primary") or "loaded_once" in st.session_state:
    st.session_state["loaded_once"] = True
    weather_client = WeatherClient()
    quake_client = EarthquakeClient()

    try:
        location = weather_client.resolve_city(city)
        current_weather = weather_client.current_weather(location.latitude, location.longitude)
        quake_events = quake_client.nearby_events(
            latitude=location.latitude,
            longitude=location.longitude,
            max_radius_km=radius,
            min_magnitude=min_mag,
            lookback_hours=lookback,
        )
        weekly_events = get_weekly_events(quake_client)
    except Exception as exc:
        st.error(f"Failed to fetch monitoring data: {exc}")
        st.stop()

    weather_level, weather_reason = classify_weather_risk(current_weather)
    quake_level, quake_reason = classify_earthquake_risk(quake_events)
    overall_level = combine_risk_levels(weather_level, quake_level)

    st.subheader(f"📍 Monitoring: {location.name}, {location.country}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Temperature (°C)", current_weather.get("temperature_2m", "N/A"))
    c2.metric("Humidity (%)", current_weather.get("relative_humidity_2m", "N/A"))
    c3.metric("Wind (km/h)", current_weather.get("wind_speed_10m", "N/A"))

    st.divider()

    level_color = {"LOW": "🟢", "MODERATE": "🟠", "HIGH": "🔴"}
    st.markdown(f"### Overall Alert Level: {level_color[overall_level]} **{overall_level}**")
    st.write(f"**Weather assessment:** {weather_reason}")
    st.write(f"**Earthquake assessment:** {quake_reason}")

    st.divider()
    st.subheader("Recent Nearby Earthquake Events")
    if quake_events:
        table = pd.DataFrame(quake_events)
        st.dataframe(
            table[["time_utc", "magnitude", "place", "depth_km", "url"]],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.success("No nearby earthquakes matched your filters in the selected window.")

    st.divider()
    st.subheader("🌍 Earthquake Heatmap (Global, Last 7 Days)")
    heatmap_df = pd.DataFrame(weekly_events)
    if not heatmap_df.empty:
        heatmap_df = heatmap_df[["latitude", "longitude", "magnitude"]].dropna()
        heatmap_df["magnitude"] = pd.to_numeric(heatmap_df["magnitude"], errors="coerce").fillna(0.0)
        heatmap_df = heatmap_df[heatmap_df["magnitude"] > 0]

        if heatmap_df.empty:
            st.info("No valid weekly earthquake coordinates available for heatmap rendering.")
        else:
            base_map = Map(location=[20, 0], zoom_start=2, control_scale=True)
            TileLayer("OpenStreetMap").add_to(base_map)

            heat_points = heatmap_df.apply(
                lambda row: [float(row["latitude"]), float(row["longitude"]), float(row["magnitude"])],
                axis=1,
            ).tolist()

            HeatMap(
                heat_points,
                radius=12,
                blur=10,
                min_opacity=0.3,
                max_zoom=6,
            ).add_to(base_map)

            st_folium(base_map, width=None, height=520, use_container_width=True)
    else:
        st.info("No weekly earthquake data available right now.")

    st.divider()
    st.subheader("📈 Historical Risk Analysis (Last 7 Days)")
    analysis = analyze_country_city_risk(weekly_events)
    top_countries = analysis["top_countries"]
    top_cities = analysis["top_cities"]

    left, right = st.columns(2)
    with left:
        st.markdown("#### Top 5 Risky Countries")
        if top_countries:
            for idx, country_item in enumerate(top_countries, start=1):
                st.write(
                    f"{idx}. **{country_item['country']}** — Risk Score: {country_item['risk_score']}"
                )
        else:
            st.write("No country-level historical data available.")

    with right:
        st.markdown("#### Top 3 Risky Cities per Country")
        if top_cities:
            for country_name, city_items in top_cities.items():
                st.markdown(f"**{country_name}**")
                for city_item in city_items:
                    st.write(f"- {city_item['city']} (Risk Score: {city_item['risk_score']})")
        else:
            st.write("No city-level historical data available.")
else:
    st.info("Set your location and click 'Fetch Live Monitoring Data' to start monitoring.")

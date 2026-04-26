from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import radians, sin, cos, sqrt, atan2
from typing import Any

import requests


@dataclass
class Coordinates:
    name: str
    country: str
    latitude: float
    longitude: float


class WeatherClient:
    """Fetches weather-related data from Open-Meteo endpoints."""

    GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
    WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

    def resolve_city(self, city: str) -> Coordinates:
        response = requests.get(
            self.GEO_URL,
            params={"name": city, "count": 1, "language": "en", "format": "json"},
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()

        results = payload.get("results") or []
        if not results:
            raise ValueError(f"City '{city}' not found in geocoding provider.")

        result = results[0]
        return Coordinates(
            name=result["name"],
            country=result.get("country", "Unknown"),
            latitude=result["latitude"],
            longitude=result["longitude"],
        )

    def current_weather(self, latitude: float, longitude: float) -> dict[str, Any]:
        response = requests.get(
            self.WEATHER_URL,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": [
                    "temperature_2m",
                    "relative_humidity_2m",
                    "precipitation",
                    "wind_speed_10m",
                ],
            },
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        return payload.get("current", {})


class EarthquakeClient:
    """Fetches earthquake events from USGS feeds."""

    USGS_WEEK_FEED = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_week.geojson"

    def weekly_events(self) -> list[dict[str, Any]]:
        """Returns all earthquake events globally from the last 7 days."""
        response = requests.get(self.USGS_WEEK_FEED, timeout=20)
        response.raise_for_status()
        features = response.json().get("features") or []

        events: list[dict[str, Any]] = []
        for item in features:
            props = item.get("properties") or {}
            geometry = item.get("geometry") or {}
            coordinates = geometry.get("coordinates") or [None, None, None]
            ts_ms = props.get("time")
            event_time = (
                datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).isoformat()
                if ts_ms else None
            )
            events.append({
                "place": props.get("place"),
                "magnitude": props.get("mag"),
                "time_utc": event_time,
                "url": props.get("url"),
                "longitude": coordinates[0],
                "latitude": coordinates[1],
                "depth_km": coordinates[2],
            })
        return events

    def nearby_events(
        self,
        latitude: float,
        longitude: float,
        max_radius_km: int = 500,
        min_magnitude: float = 2.5,
        lookback_hours: int = 48,
    ) -> list[dict[str, Any]]:
        """Returns nearby earthquake events filtered by distance, magnitude, and time."""

        def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
            R = 6371
            lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
            return R * 2 * atan2(sqrt(a), sqrt(1 - a))

        all_events = self.weekly_events()
        cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)

        filtered = []
        for ev in all_events:
            # Filter by magnitude
            mag = ev.get("magnitude")
            if mag is None or mag < min_magnitude:
                continue

            # Filter by time
            ev_time_str = ev.get("time_utc")
            if ev_time_str:
                ev_time = datetime.fromisoformat(ev_time_str)
                if ev_time < cutoff:
                    continue

            # Filter by distance
            ev_lat = ev.get("latitude")
            ev_lon = ev.get("longitude")
            if ev_lat is None or ev_lon is None:
                continue
            if haversine_km(latitude, longitude, ev_lat, ev_lon) > max_radius_km:
                continue

            filtered.append(ev)

        return filtered

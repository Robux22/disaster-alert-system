from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
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
    """Fetches nearby earthquake events from USGS API."""

    USGS_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    USGS_WEEK_FEED = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_week.geojson"

    def nearby_events(
        self,
        latitude: float,
        longitude: float,
        max_radius_km: int = 500,
        min_magnitude: float = 2.5,
        lookback_hours: int = 48,
    ) -> list[dict[str, Any]]:
        end = datetime.now(timezone.utc)
        start = end - timedelta(hours=lookback_hours)

        response = requests.get(
            self.USGS_URL,
            params={
                "format": "geojson",
                "starttime": start.isoformat(),
                "endtime": end.isoformat(),
                "latitude": latitude,
                "longitude": longitude,
                "maxradiuskm": max_radius_km,
                "minmagnitude": min_magnitude,
                "orderby": "time",
            },
            timeout=20,
        )
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
                if ts_ms
                else None
            )
            events.append(
                {
                    "place": props.get("place"),
                    "magnitude": props.get("mag"),
                    "time_utc": event_time,
                    "url": props.get("url"),
                    "longitude": coordinates[0],
                    "latitude": coordinates[1],
                    "depth_km": coordinates[2],
                }
            )

        return events

    def weekly_events(self) -> list[dict[str, Any]]:
        """Returns all publicly listed earthquake events in the last 7 days."""
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
                if ts_ms
                else None
            )
            events.append(
                {
                    "place": props.get("place"),
                    "magnitude": props.get("mag"),
                    "time_utc": event_time,
                    "url": props.get("url"),
                    "longitude": coordinates[0],
                    "latitude": coordinates[1],
                    "depth_km": coordinates[2],
                }
            )
        return events

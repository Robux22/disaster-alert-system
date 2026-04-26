from __future__ import annotations

from collections import defaultdict
from typing import Any


def classify_weather_risk(current_weather: dict[str, Any]) -> tuple[str, str]:
    """Returns risk level and reason based on weather conditions."""
    wind = float(current_weather.get("wind_speed_10m") or 0)
    precipitation = float(current_weather.get("precipitation") or 0)

    if wind >= 55 or precipitation >= 25:
        return "HIGH", "Severe wind or heavy precipitation detected."
    if wind >= 35 or precipitation >= 10:
        return "MODERATE", "Elevated wind or rainfall levels detected."
    return "LOW", "Weather conditions appear stable."


def classify_earthquake_risk(events: list[dict[str, Any]]) -> tuple[str, str]:
    """Returns risk level and reason based on nearby earthquake events."""
    if not events:
        return "LOW", "No significant nearby earthquake events in the lookback window."

    magnitudes = [float(event.get("magnitude") or 0) for event in events]
    peak = max(magnitudes)

    if peak >= 6.0:
        return "HIGH", f"Major seismic activity detected (max magnitude {peak:.1f})."
    if peak >= 4.5:
        return "MODERATE", f"Noticeable seismic activity detected (max magnitude {peak:.1f})."
    return "LOW", f"Minor seismic activity only (max magnitude {peak:.1f})."


def combine_risk_levels(weather_level: str, quake_level: str) -> str:
    levels = {"LOW": 1, "MODERATE": 2, "HIGH": 3}
    reverse = {1: "LOW", 2: "MODERATE", 3: "HIGH"}
    return reverse[max(levels[weather_level], levels[quake_level])]


def analyze_country_city_risk(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Build top-5 country and top-3 city risk analysis from weekly earthquakes."""
    country_scores: dict[str, float] = defaultdict(float)
    city_scores_by_country: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))

    for event in events:
        place = str(event.get("place") or "Unknown")
        magnitude = float(event.get("magnitude") or 0)
        city, country = _parse_place(place)
        country_scores[country] += magnitude
        city_scores_by_country[country][city] += magnitude

    top_countries = sorted(country_scores.items(), key=lambda item: item[1], reverse=True)[:5]

    top_cities: dict[str, list[dict[str, Any]]] = {}
    for country, _ in top_countries:
        sorted_cities = sorted(
            city_scores_by_country[country].items(),
            key=lambda item: item[1],
            reverse=True,
        )[:3]
        top_cities[country] = [
            {"city": city, "risk_score": round(score, 2)} for city, score in sorted_cities
        ]

    return {
        "top_countries": [
            {"country": country, "risk_score": round(score, 2)} for country, score in top_countries
        ],
        "top_cities": top_cities,
    }


def _parse_place(place: str) -> tuple[str, str]:
    """Extract city/location + country-like segment from a USGS place string."""
    if "," in place:
        left, right = place.rsplit(",", 1)
        country = right.strip() or "Unknown"
    else:
        left = place
        country = "Unknown"

    if " of " in left:
        city = left.split(" of ", 1)[1].strip()
    else:
        city = left.strip() or "Unknown"

    return city, country

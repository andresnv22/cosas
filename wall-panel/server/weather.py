"""Clima vía Open-Meteo: API gratis, sin registro, sin API key.
https://open-meteo.com/en/docs
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

# Códigos de clima de Open-Meteo (WMO) reducidos a algo que cabe en un
# ícono simple de e-ink (blanco y negro, 1 bit).
_WEATHER_ICONS = {
    0: "sol",
    1: "sol_nubes", 2: "sol_nubes", 3: "nublado",
    45: "niebla", 48: "niebla",
    51: "llovizna", 53: "llovizna", 55: "llovizna",
    61: "lluvia", 63: "lluvia", 65: "lluvia",
    71: "nieve", 73: "nieve", 75: "nieve",
    80: "chubascos", 81: "chubascos", 82: "chubascos",
    95: "tormenta", 96: "tormenta", 99: "tormenta",
}


@dataclass
class WeatherNow:
    temp_c: float
    feels_like_c: float
    condition: str  # clave de _WEATHER_ICONS, el firmware la mapea a un ícono
    temp_min_today: float
    temp_max_today: float
    chance_of_rain_today: int  # 0-100


def fetch(latitude: float, longitude: float, timeout: float = 10.0) -> WeatherNow:
    resp = httpx.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,apparent_temperature,weather_code",
            "daily": "temperature_2m_min,temperature_2m_max,precipitation_probability_max",
            "timezone": "auto",
            "forecast_days": 1,
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()

    current = data["current"]
    daily = data["daily"]
    code = current["weather_code"]

    return WeatherNow(
        temp_c=current["temperature_2m"],
        feels_like_c=current["apparent_temperature"],
        condition=_WEATHER_ICONS.get(code, "nublado"),
        temp_min_today=daily["temperature_2m_min"][0],
        temp_max_today=daily["temperature_2m_max"][0],
        chance_of_rain_today=daily["precipitation_probability_max"][0],
    )

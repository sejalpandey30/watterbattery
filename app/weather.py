"""Live 48 h forecast from Open-Meteo (free, no API key)."""
import httpx

URL = "https://api.open-meteo.com/v1/forecast"


def fetch_forecast(lat: float, lon: float) -> dict:
    params = {"latitude": lat, "longitude": lon, "hourly": "cloud_cover,precipitation",
              "forecast_days": 2, "timezone": "auto"}
    r = httpx.get(URL, params=params, timeout=10)
    r.raise_for_status()
    h = r.json()["hourly"]
    cloud = [float(x or 0) for x in h["cloud_cover"][:48]]
    rain = [float(x or 0) for x in h["precipitation"][:48]]
    if len(cloud) < 48 or len(rain) < 48:
        raise ValueError("Forecast response was incomplete")
    return {"cloud_cover": cloud,
            "rain_mm": [round(sum(rain[:24]), 1), round(sum(rain[24:48]), 1)]}

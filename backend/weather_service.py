"""
weather_service.py
--------------------
This file is the ONLY place in the whole app that knows how to fetch
weather data. Everything else (chat, alerts, agriculture) asks THIS
file for data and never touches an external API directly.

Why do it this way?
  If tomorrow you get access to an official IMD API, you only change
  this one file (add an IMDWeatherProvider class) — nothing else in
  the project needs to change.

WeatherProvider (abstract interface)
  |
  |-- MockWeatherProvider   -> generates realistic fake data, always works
  |-- RealWeatherProvider   -> calls OpenWeatherMap, needs an API key
  (future) IMDWeatherProvider

get_weather_provider() decides which one to use:
  - If DEMO_MODE=true in .env            -> MockWeatherProvider
  - If no WEATHER_API_KEY is set          -> MockWeatherProvider (auto fallback)
  - Otherwise                             -> RealWeatherProvider
  - If RealWeatherProvider's API call fails at runtime -> falls back to mock
"""

import os
import random
import math
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
import httpx

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "")
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"

CONDITIONS = ["Clear", "Partly Cloudy", "Cloudy", "Light Rain", "Moderate Rain", "Thunderstorm", "Haze"]

# A few Indian city coordinates for the mock provider (extend as needed)
CITY_COORDS = {
    "indore": (22.7196, 75.8577),
    "delhi": (28.6139, 77.2090),
    "mumbai": (19.0760, 72.8777),
    "bhopal": (23.2599, 77.4126),
    "jaipur": (26.9124, 75.7873),
    "pune": (18.5204, 73.8567),
    "chennai": (13.0827, 80.2707),
    "kolkata": (22.5726, 88.3639),
}


class WeatherProvider(ABC):
    """Every weather provider must implement these three methods."""

    @abstractmethod
    async def get_current(self, location: str) -> dict:
        ...

    @abstractmethod
    async def get_hourly(self, location: str, hours: int = 12) -> list[dict]:
        ...

    @abstractmethod
    async def get_forecast(self, location: str, days: int = 7) -> list[dict]:
        ...


class MockWeatherProvider(WeatherProvider):
    """
    Generates realistic-looking (but fake) weather data.
    Uses the location name as a random seed so the SAME city always
    returns similar-feeling numbers within one run — this makes demos
    look consistent instead of jumping around randomly.
    """

    def _seeded_random(self, location: str, offset: int = 0):
        seed = sum(ord(c) for c in location.lower()) + offset
        rng = random.Random(seed)
        return rng

    async def get_current(self, location: str) -> dict:
        rng = self._seeded_random(location)
        base_temp = rng.uniform(24, 38)
        return {
            "location": location.title(),
            "timestamp": datetime.utcnow().isoformat(),
            "temperature": round(base_temp, 1),
            "feels_like": round(base_temp + rng.uniform(-1, 3), 1),
            "humidity": rng.randint(35, 90),
            "wind_speed": round(rng.uniform(4, 35), 1),
            "wind_direction": rng.choice(["N", "NE", "E", "SE", "S", "SW", "W", "NW"]),
            "pressure": rng.randint(998, 1015),
            "visibility": round(rng.uniform(2, 10), 1),
            "condition": rng.choice(CONDITIONS),
            "rain_probability": rng.randint(0, 90),
            "sunrise": "06:12",
            "sunset": "18:47",
            "data_source": "mock",
        }

    async def get_hourly(self, location: str, hours: int = 12) -> list[dict]:
        rng = self._seeded_random(location, offset=1)
        base_temp = rng.uniform(24, 38)
        now = datetime.utcnow()
        result = []
        for h in range(hours):
            hour_time = now + timedelta(hours=h)
            temp = base_temp + 4 * math.sin(h / 24 * 2 * math.pi) + rng.uniform(-1, 1)
            result.append({
                "time": hour_time.strftime("%H:00"),
                "temperature": round(temp, 1),
                "rain_probability": rng.randint(0, 80),
                "condition": rng.choice(CONDITIONS),
            })
        return result

    async def get_forecast(self, location: str, days: int = 7) -> list[dict]:
        rng = self._seeded_random(location, offset=2)
        base_temp = rng.uniform(24, 36)
        today = datetime.utcnow()
        result = []
        for d in range(days):
            date = today + timedelta(days=d)
            day_variation = rng.uniform(-3, 3)
            result.append({
                "date": date.strftime("%Y-%m-%d"),
                "day_name": date.strftime("%A"),
                "temp_max": round(base_temp + day_variation + 3, 1),
                "temp_min": round(base_temp + day_variation - 5, 1),
                "condition": rng.choice(CONDITIONS),
                "rain_probability": rng.randint(0, 85),
                "rainfall_mm": round(rng.uniform(0, 60), 1) if rng.random() > 0.5 else 0,
                "wind_speed": round(rng.uniform(5, 30), 1),
            })
        return result


class RealWeatherProvider(WeatherProvider):
    """
    Calls the OpenWeatherMap API (free tier). Requires WEATHER_API_KEY
    to be set in .env. If the request fails for any reason (bad key,
    no internet, rate limit), the caller (get_weather_provider) has
    already arranged a mock fallback — see chat/main.py usage.
    """

    BASE_URL = "https://api.openweathermap.org/data/2.5"

    async def _get_coords(self, client: httpx.AsyncClient, location: str):
        geo_url = f"https://api.openweathermap.org/geo/1.0/direct"
        resp = await client.get(geo_url, params={"q": f"{location},IN", "limit": 1, "appid": WEATHER_API_KEY})
        resp.raise_for_status()
        data = resp.json()
        if not data:
            raise ValueError(f"Location '{location}' not found")
        return data[0]["lat"], data[0]["lon"]

    async def get_current(self, location: str) -> dict:
        async with httpx.AsyncClient(timeout=10) as client:
            lat, lon = await self._get_coords(client, location)
            resp = await client.get(f"{self.BASE_URL}/weather", params={
                "lat": lat, "lon": lon, "appid": WEATHER_API_KEY, "units": "metric"
            })
            resp.raise_for_status()
            d = resp.json()
            return {
                "location": location.title(),
                "timestamp": datetime.utcnow().isoformat(),
                "temperature": d["main"]["temp"],
                "feels_like": d["main"]["feels_like"],
                "humidity": d["main"]["humidity"],
                "wind_speed": round(d["wind"]["speed"] * 3.6, 1),  # m/s -> km/h
                "wind_direction": str(d["wind"].get("deg", "")),
                "pressure": d["main"]["pressure"],
                "visibility": round(d.get("visibility", 10000) / 1000, 1),
                "condition": d["weather"][0]["main"],
                "rain_probability": 0,  # not provided by this endpoint
                "sunrise": datetime.utcfromtimestamp(d["sys"]["sunrise"]).strftime("%H:%M"),
                "sunset": datetime.utcfromtimestamp(d["sys"]["sunset"]).strftime("%H:%M"),
                "data_source": "real",
            }

    async def get_hourly(self, location: str, hours: int = 12) -> list[dict]:
        async with httpx.AsyncClient(timeout=10) as client:
            lat, lon = await self._get_coords(client, location)
            resp = await client.get(f"{self.BASE_URL}/forecast", params={
                "lat": lat, "lon": lon, "appid": WEATHER_API_KEY, "units": "metric"
            })
            resp.raise_for_status()
            d = resp.json()
            result = []
            for item in d["list"][: math.ceil(hours / 3)]:
                result.append({
                    "time": item["dt_txt"].split(" ")[1][:5],
                    "temperature": item["main"]["temp"],
                    "rain_probability": int(item.get("pop", 0) * 100),
                    "condition": item["weather"][0]["main"],
                })
            return result

    async def get_forecast(self, location: str, days: int = 7) -> list[dict]:
        # Free OpenWeatherMap tier only gives 5-day/3-hour forecast, so we
        # aggregate that into daily buckets to approximate a 7-day view.
        async with httpx.AsyncClient(timeout=10) as client:
            lat, lon = await self._get_coords(client, location)
            resp = await client.get(f"{self.BASE_URL}/forecast", params={
                "lat": lat, "lon": lon, "appid": WEATHER_API_KEY, "units": "metric"
            })
            resp.raise_for_status()
            d = resp.json()
            by_day = {}
            for item in d["list"]:
                date = item["dt_txt"].split(" ")[0]
                by_day.setdefault(date, []).append(item)

            result = []
            for date, items in list(by_day.items())[:days]:
                temps = [i["main"]["temp"] for i in items]
                result.append({
                    "date": date,
                    "day_name": datetime.strptime(date, "%Y-%m-%d").strftime("%A"),
                    "temp_max": round(max(temps), 1),
                    "temp_min": round(min(temps), 1),
                    "condition": items[len(items) // 2]["weather"][0]["main"],
                    "rain_probability": int(max(i.get("pop", 0) for i in items) * 100),
                    "rainfall_mm": round(sum(i.get("rain", {}).get("3h", 0) for i in items), 1),
                    "wind_speed": round(items[0]["wind"]["speed"] * 3.6, 1),
                })
            return result


def get_weather_provider() -> WeatherProvider:
    """
    Decides which provider to hand out. This is the single switch that
    controls demo mode vs real mode for the entire app.
    """
    if DEMO_MODE or not WEATHER_API_KEY:
        return MockWeatherProvider()
    return RealWeatherProvider()


async def get_current_weather_safe(location: str) -> dict:
    """
    Wraps the provider call with automatic fallback: if the real API
    fails for any reason, we silently degrade to mock data instead of
    crashing the demo. The response always tells you which one you got
    via the 'data_source' field.
    """
    provider = get_weather_provider()
    try:
        return await provider.get_current(location)
    except Exception:
        fallback = await MockWeatherProvider().get_current(location)
        fallback["data_source"] = "mock (fallback - real API failed)"
        return fallback

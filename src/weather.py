"""OpenWeatherMap integration for the Travel Planner."""

import requests
from datetime import datetime, timedelta
from .config import settings
from .models import Weather, Coordinates


OWM_BASE = "https://api.openweathermap.org/data/2.5"


def get_coordinates(city: str) -> Coordinates | None:
    """Convert a city name to coordinates using OpenWeatherMap Geocoding API."""
    if not settings.has_owm:
        print("⚠️  OpenWeatherMap API key not set. Set OWM_API_KEY in .env")
        return None

    print(f"[weather] geocoding city: {city}")

    url = f"{OWM_BASE}/weather"
    params = {"q": city, "appid": settings.OWM_API_KEY}

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        print(f"[weather] geocoding success: {city} -> {data['coord']['lat']}, {data['coord']['lon']}")
        return Coordinates(lat=data["coord"]["lat"], lon=data["coord"]["lon"])
    except Exception as e:
        print(f"❌ Geocoding failed for '{city}': {e}")
        return None


def get_forecast(city_or_coords: str | Coordinates, days: int = 7) -> list[Weather]:
    """
    Get weather forecast for a city.
    
    Args:
        city_or_coords: City name (e.g. "Tokyo") or Coordinates object
        days: Number of days of forecast (max 5 on free tier)
    
    Returns:
        List of Weather objects, one per day
    """
    if not settings.has_owm:
        print("⚠️  OpenWeatherMap API key not set. Set OWM_API_KEY in .env")
        return []

    print(f"[weather] forecast requested for: {city_or_coords}")

    # Get lat/lon
    if isinstance(city_or_coords, str):
        coords = get_coordinates(city_or_coords)
        if not coords:
            return []
    else:
        coords = city_or_coords

    # 5-day / 3-hour forecast (free tier)
    url = f"{OWM_BASE}/forecast"
    params = {
        "lat": coords.lat,
        "lon": coords.lon,
        "appid": settings.OWM_API_KEY,
        "units": "metric",
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        print(f"[weather] forecast API returned {len(data.get('list', []))} intervals")
    except Exception as e:
        print(f"❌ Weather fetch failed: {e}")
        return []

    # Aggregate 3-hour intervals into daily forecasts
    daily_weather: dict[str, list[dict]] = {}
    for item in data.get("list", []):
        dt = datetime.fromtimestamp(item["dt"])
        date_key = dt.strftime("%Y-%m-%d")
        if date_key not in daily_weather:
            daily_weather[date_key] = []
        daily_weather[date_key].append(item)

    weather_list = []
    today = datetime.now().strftime("%Y-%m-%d")

    for date_key in sorted(daily_weather.keys())[:days]:
        # Skip today if it's already the current day's partial data
        intervals = daily_weather[date_key]

        temps = [i["main"]["temp"] for i in intervals]
        conditions = [i["weather"][0]["main"] for i in intervals]
        descriptions = [i["weather"][0]["description"] for i in intervals]
        icons = [i["weather"][0]["icon"] for i in intervals]

        # Most common condition
        from collections import Counter
        top_condition = Counter(conditions).most_common(1)[0][0]
        top_desc = Counter(descriptions).most_common(1)[0][0]
        top_icon = Counter(icons).most_common(1)[0][0]

        weather_list.append(Weather(
            date=date_key,
            temp_high=round(max(temps)),
            temp_low=round(min(temps)),
            condition=top_condition,
            icon=top_icon,
            description=top_desc,
        ))

    print(f"[weather] forecast normalized into {len(weather_list)} day(s)")

    return weather_list


def weather_emoji(condition: str) -> str:
    """Convert weather condition to an emoji for display."""
    emoji_map = {
        "Clear": "☀️",
        "Sunny": "☀️",
        "Clouds": "☁️",
        "Overcast": "☁️",
        "Rain": "🌧️",
        "Drizzle": "🌦️",
        "Thunderstorm": "⛈️",
        "Snow": "❄️",
        "Mist": "🌫️",
        "Fog": "🌫️",
        "Haze": "🌫️",
    }
    return emoji_map.get(condition, "🌤️")


def weather_advice(weather: Weather) -> str:
    """Generate one-line advice based on weather."""
    condition = weather.condition.lower()
    temp = (weather.temp_high + weather.temp_low) / 2

    if "rain" in condition or "thunder" in condition:
        return "🧥 Bring an umbrella! Plan indoor activities."
    if "snow" in condition:
        return "❄️ Snowy! Dress warm and check for closures."
    if temp > 35:
        return "🥵 Extreme heat! Stay hydrated, avoid midday sun."
    if temp > 28:
        return "☀️ Hot day! Perfect for beach or pool."
    if temp > 20:
        return "🌤️ Great weather! Perfect for outdoor exploring."
    if temp > 10:
        return "🌥️ Mild weather. A light jacket recommended."
    return "🧥 Cool day. Pack a warm layer."

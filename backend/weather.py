import os
import requests
from dotenv import load_dotenv

load_dotenv()

CITY = "London,CA"
OWM_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")

# Historical climate averages for London, Ontario by month
MONTHLY_CLIMATE = {
    1:  {"label": "January",   "desc": "cold winter with heavy snowfall, avg -6°C",      "risk": "high"},
    2:  {"label": "February",  "desc": "cold winter with snowfall likely, avg -5°C",      "risk": "high"},
    3:  {"label": "March",     "desc": "late winter/early spring, variable, avg 1°C",     "risk": "medium"},
    4:  {"label": "April",     "desc": "spring, mild with occasional rain, avg 8°C",      "risk": "low"},
    5:  {"label": "May",       "desc": "spring, pleasant and warming, avg 14°C",          "risk": "low"},
    6:  {"label": "June",      "desc": "early summer, warm and sunny, avg 19°C",          "risk": "low"},
    7:  {"label": "July",      "desc": "peak summer, warm and mostly dry, avg 22°C",      "risk": "low"},
    8:  {"label": "August",    "desc": "peak summer, warm and mostly dry, avg 21°C",      "risk": "low"},
    9:  {"label": "September", "desc": "early fall, pleasant and cooling, avg 16°C",      "risk": "low"},
    10: {"label": "October",   "desc": "fall, cooler with increasing rain, avg 10°C",     "risk": "medium"},
    11: {"label": "November",  "desc": "late fall, cold with possible early snow, avg 4°C", "risk": "high"},
    12: {"label": "December",  "desc": "winter, cold with snowfall likely, avg -2°C",     "risk": "high"},
}


def get_current_weather():
    """Fetch current live weather for London, Ontario from OpenWeatherMap."""
    if not OWM_API_KEY:
        return None

    try:
        response = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"q": CITY, "appid": OWM_API_KEY, "units": "metric"},
            timeout=5
        )
        response.raise_for_status()
        data = response.json()
        return {
            "temp":        data["main"]["temp"],
            "description": data["weather"][0]["description"],
            "humidity":    data["main"]["humidity"],
            "wind_speed":  data["wind"]["speed"],
        }
    except Exception as e:
        print(f"[Weather] API call failed: {e}")
        return None


def get_weather_context(event_date):
    """
    Returns a weather context string to inject into the conflict detection prompt.
    Combines a live current weather snapshot with monthly climate data for the event date.
    Only called when venue_type is outdoor.
    """
    parts = []

    current = get_current_weather()
    if current:
        parts.append(
            f"Current conditions in London, Ontario: {current['description']}, "
            f"{current['temp']}°C, humidity {current['humidity']}%, "
            f"wind {current['wind_speed']} m/s."
        )
    else:
        parts.append("Current weather data for London, Ontario is unavailable.")

    if event_date:
        try:
            month = int(event_date.split("-")[1])
            climate = MONTHLY_CLIMATE.get(month)
            if climate:
                parts.append(
                    f"Historical climate for London, Ontario in {climate['label']}: "
                    f"{climate['desc']}. Outdoor weather risk level: {climate['risk'].upper()}."
                )
        except (IndexError, ValueError):
            pass

    return "\n".join(parts) if parts else None

"""
alert_service.py
------------------
A simple, explainable, THRESHOLD-based alert engine.

Why rule-based instead of ML for this?
  - Alert thresholds for heat/rain/wind are already well-defined by
    meteorological bodies (IMD publishes exact heatwave/rainfall
    criteria). There's no pattern to "learn" — we just compare numbers
    to known limits.
  - It's 100% explainable: you can tell a judge exactly why an alert
    fired ("temperature crossed 40°C"), which builds trust — a black-box
    ML model can't do that as convincingly for a disaster-management tool.
  - It needs zero training data and works correctly from day one.

Severity scale: LOW -> MODERATE -> HIGH -> SEVERE -> EXTREME
"""

def evaluate_alerts(weather: dict) -> list[dict]:
    alerts = []
    temp = weather.get("temperature", 0)
    rain_prob = weather.get("rain_probability", 0)
    wind = weather.get("wind_speed", 0)
    condition = str(weather.get("condition", "")).lower()
    location = weather.get("location", "your area")

    # --- Heat alerts ---
    if temp >= 45:
        alerts.append(_alert("Extreme Heatwave", "EXTREME",
            f"Temperature in {location} has reached {temp}°C — extreme heat danger.",
            "Avoid all outdoor activity between 11 AM–4 PM. Stay hydrated. Check on elderly/children/outdoor workers."))
    elif temp >= 40:
        alerts.append(_alert("Heatwave", "HIGH",
            f"Temperature in {location} is {temp}°C — heatwave conditions.",
            "Limit outdoor exposure during peak afternoon hours. Drink water frequently."))
    elif temp >= 37:
        alerts.append(_alert("Heat Advisory", "MODERATE",
            f"Temperature in {location} is {temp}°C — above normal.",
            "Stay hydrated and avoid strenuous outdoor activity during midday."))

    # --- Rain / flood alerts ---
    rainfall_mm = weather.get("rainfall_mm", 0)
    if rainfall_mm >= 115 or (rain_prob >= 85 and "thunderstorm" in condition):
        alerts.append(_alert("Heavy Rainfall / Flood Risk", "SEVERE",
            f"Very heavy rainfall expected in {location} ({rainfall_mm} mm).",
            "Avoid waterlogged areas and unnecessary travel. Move to higher ground if near flood-prone zones."))
    elif rainfall_mm >= 64 or rain_prob >= 75:
        alerts.append(_alert("Heavy Rainfall", "HIGH",
            f"Heavy rainfall likely in {location} ({rain_prob}% probability).",
            "Avoid unnecessary travel. Watch for waterlogging in low-lying areas."))
    elif rain_prob >= 50:
        alerts.append(_alert("Moderate Rain Expected", "LOW",
            f"Moderate rain chance in {location} ({rain_prob}%).",
            "Carry an umbrella. Minor delays possible in travel."))

    # --- Wind / storm alerts ---
    if wind >= 62:
        alerts.append(_alert("Severe Wind / Storm", "SEVERE",
            f"Very high wind speed in {location} ({wind} km/h).",
            "Stay indoors. Secure loose objects. Avoid trees and weak structures."))
    elif wind >= 40:
        alerts.append(_alert("Strong Wind Alert", "MODERATE",
            f"Strong winds in {location} ({wind} km/h).",
            "Secure loose outdoor items. Drive carefully, especially two-wheelers."))

    # --- Thunderstorm / lightning ---
    if "thunderstorm" in condition:
        alerts.append(_alert("Thunderstorm & Lightning", "HIGH",
            f"Thunderstorm activity reported in {location}.",
            "Stay indoors. Avoid open fields, tall trees, and metal structures. Unplug electronics."))

    # --- Fog ---
    visibility = weather.get("visibility", 10)
    if visibility <= 1:
        alerts.append(_alert("Dense Fog", "MODERATE",
            f"Visibility in {location} has dropped to {visibility} km.",
            "Drive slowly with fog lights on. Avoid highway travel if possible."))

    return alerts


def _alert(alert_type: str, severity: str, message: str, recommendation: str) -> dict:
    return {
        "type": alert_type,
        "severity": severity,
        "message": message,
        "recommendation": recommendation,
    }

"""
agriculture_service.py
------------------------
Combines current weather with simple, predefined agronomy rules for
5 major crops. This is a WEATHER-BASED ADVISORY, not professional
agricultural advice — we say this explicitly in every response.

Each crop has a few weather-triggered rules. This keeps the module
easy to extend: add a new crop by adding a new list of rule functions.
"""

DISCLAIMER = ("This is a weather-based advisory generated from general agronomic "
              "guidelines. It is not a substitute for professional agricultural advice.")


def _common_rules(weather: dict) -> list[str]:
    """Rules that apply to most crops, regardless of type."""
    advisories = []
    rain_prob = weather.get("rain_probability", 0)
    temp = weather.get("temperature", 0)
    wind = weather.get("wind_speed", 0)

    if rain_prob >= 70:
        advisories.append("High rain probability — consider postponing irrigation to avoid waterlogging.")
        advisories.append("Avoid spraying pesticides or fertilizers before expected rainfall; it will wash off.")
    elif rain_prob <= 15 and temp >= 35:
        advisories.append("Low rain chance with high temperature — monitor soil moisture and irrigate if needed.")

    if temp >= 40:
        advisories.append("Extreme heat — monitor crops for heat/water stress, especially during flowering stage.")

    if wind >= 40:
        advisories.append("Strong winds expected — delay spraying operations to avoid drift and crop damage.")

    return advisories


def _crop_specific_rules(crop: str, weather: dict) -> list[str]:
    crop = crop.lower()
    temp = weather.get("temperature", 0)
    rain_prob = weather.get("rain_probability", 0)
    humidity = weather.get("humidity", 0)

    rules = []
    if crop == "wheat":
        if temp <= 5:
            rules.append("Low temperature risk of frost damage — consider light irrigation in the evening to protect crop.")
        if humidity >= 85:
            rules.append("High humidity increases risk of rust/blight — inspect crop and consider preventive fungicide if symptoms appear.")
    if crop == "rice":
        if rain_prob >= 60:
            rules.append("Good rainfall expected — suitable window for transplanting if field preparation is complete.")
        if temp >= 35:
            rules.append("High temperature — maintain standing water level to reduce heat stress.")
    if crop == "soybean":
        if humidity >= 80:
            rules.append("High humidity increases risk of fungal disease — monitor for yellow mosaic and rust.")
    if crop == "cotton":
        if rain_prob >= 70:
            rules.append("Heavy rain risk — ensure field drainage to prevent waterlogging, which cotton is sensitive to.")
    if crop == "maize":
        if temp >= 38:
            rules.append("High temperature during tasseling stage can affect pollination — ensure adequate soil moisture.")

    return rules


def get_advisory(crop: str, weather: dict) -> list[str]:
    advisories = _common_rules(weather) + _crop_specific_rules(crop, weather)
    if not advisories:
        advisories.append(f"No specific weather risks detected for {crop} today. Conditions look normal for routine farm operations.")
    return advisories

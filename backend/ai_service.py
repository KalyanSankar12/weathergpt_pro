"""
ai_service.py
---------------
This is WeatherGPT's "brain" for understanding language — but NOT for
knowing weather facts. Read this carefully, because it's the most
important architectural rule in the whole project:

    The AI NEVER invents temperature, rainfall, or any weather number.
    It only does two jobs:
      1. UNDERSTAND the question  -> figure out intent + location + date
      2. PHRASE the answer        -> turn real data (from weather_service.py)
                                      into a natural sentence

Two modes:
  - Rule-based (default, always works, no API key needed): uses keyword
    matching and simple templates. Good enough for a fixed vocabulary
    of weather questions in English and Hindi.
  - LLM-enhanced (optional): if ANTHROPIC_API_KEY is set in .env, we
    ask Claude to (a) extract intent/location more flexibly, and
    (b) write a more natural final sentence FROM the retrieved data.
    The LLM is given the real numbers as context — it is told to only
    use those numbers, never invent its own.
"""

import os
import re
import json
import httpx

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
USE_LLM = bool(ANTHROPIC_API_KEY)

KNOWN_CITIES = ["indore", "delhi", "mumbai", "bhopal", "jaipur", "pune", "chennai", "kolkata"]

RAIN_WORDS = ["rain", "बारिश", "barish", "rainfall"]
TEMP_WORDS = ["temperature", "temp", "tapman", "तापमान", "hot", "cold"]
FORECAST_WORDS = ["tomorrow", "week", "forecast", "कल", "अगले", "आने वाले"]
ALERT_WORDS = ["alert", "warning", "चेतावनी", "danger", "risk"]
IRRIGATE_WORDS = ["irrigate", "irrigation", "सिंचाई", "crop", "फसल"]
HEATWAVE_WORDS = ["heatwave", "heat wave", "लू", "precaution"]
GREETING_WORDS = [
    "hi",
    "hello",
    "hey",
    "namaste",
    "good morning",
    "good afternoon",
    "good evening",
    "नमस्ते",
    "नमस्कार"
]

def extract_location(text: str) -> str:
    text_lower = text.lower()
    for city in KNOWN_CITIES:
        if city in text_lower:
            return city
    return "indore"  


def detect_intent(text):
    text_lower = text.lower().strip()

    # ---------------- GREETING ----------------
    greeting_phrases = [
        "hi",
        "hello",
        "hey",
        "namaste",
        "good morning",
        "good afternoon",
        "good evening",
        "नमस्ते",
        "नमस्कार"
    ]

    if text_lower in greeting_phrases:
        return "greeting"

    # ---------------- WEATHER ----------------
    rain_words = [
        "rain",
        "rainfall",
        "raining",
        "barish",
        "बारिश"
    ]

    forecast_words = [
        "forecast",
        "tomorrow",
        "today",
        "this week",
        "कल",
        "आज"
    ]

    temperature_words = [
        "temperature",
        "temp",
        "hot",
        "cold",
        "तापमान"
    ]

    alert_words = [
        "alert",
        "warning",
        "danger",
        "risk",
        "चेतावनी"
    ]

    agriculture_words = [
        "crop",
        "agriculture",
        "irrigation",
        "irrigate",
        "फसल",
        "सिंचाई"
    ]
    if any(word in text_lower for word in alert_words):
        return "alerts"

    if any(word in text_lower for word in agriculture_words):
        return "agriculture"
    if any(word in text_lower for word in rain_words):
        if "tomorrow" in text_lower or "कल" in text_lower:
            return "rain_tomorrow"
        if "today" in text_lower or "आज" in text_lower:
            return "rain_today"
        return "rain_today"
    if any(word in text_lower for word in forecast_words):
        return "forecast"

    if any(word in text_lower for word in temperature_words):
        return "current_weather"

    # ---------------- GENERAL WEATHER WORDS ----------------

    weather_words = [
        "weather",
        "climate",
        "mausam",
        "मौसम"
    ]

    if any(word in text_lower for word in weather_words):
        return "current_weather"

    # ---------------- UNKNOWN ----------------
    return "out_of_scope"
def detect_language(text: str) -> str:
    """If the text contains Devanagari characters, treat it as Hindi."""
    return "hi" if re.search(r"[\u0900-\u097F]", text) else "en"


def parse_query(text: str) -> dict:
    """Main entry point: turns a raw user question into structured intent."""
    return {
        "intent": detect_intent(text),
        "location": extract_location(text),
        "language": detect_language(text),
        "raw_query": text,
    }


# ---------------------------------------------------------------------
# Response templates (rule-based — always available, zero API cost)
# ---------------------------------------------------------------------

TEMPLATES = {
    "en": {
        "greeting": "Hello! 👋 I'm WeatherGPT. You can ask me about current weather, forecasts, rainfall, alerts, or agriculture advisories.",
        "current_weather": "The weather in {location} right now is {condition} with a temperature of {temperature}°C (feels like {feels_like}°C). Humidity is {humidity}% and wind speed is {wind_speed} km/h.",
        "temperature": "The current temperature in {location} is {temperature}°C, feels like {feels_like}°C.",
        "rain_now": "Current rain probability in {location} is {rain_probability}%. Condition: {condition}.",
        "rain_today": "Today's rain probability in {location} is around {rain_probability}%, with an expected condition of {condition}.",
        "rain_tomorrow": "Tomorrow's rain probability in {location} is around {rain_probability}%, with an expected condition of {condition}.",
        "forecast": "Here's the forecast for {location}: expect {condition} with a high of {temp_max}°C and a low of {temp_min}°C.",
        "alerts_none": "No active weather alerts for {location} right now. Conditions look normal.",
        "alerts_some": "⚠️ {count} active alert(s) for {location}: {alert_summary}",
        "heatwave_precaution": "Current temperature in {location} is {temperature}°C. During heatwaves: stay hydrated, avoid direct sun 12–3 PM, wear light cotton clothing, and check on elderly/children regularly.",
        "out_of_scope": (
    "Sorry, I can only answer weather-related questions, "
    "forecasts, alerts, and agriculture weather advisories."
)
    },
    "hi": {
        "greeting": "नमस्ते! 👋 मैं WeatherGPT हूँ। आप मुझसे मौसम, पूर्वानुमान, बारिश, चेतावनी या कृषि संबंधी जानकारी पूछ सकते हैं।",
        "current_weather": "{location} में अभी मौसम {condition} है। तापमान {temperature}°C है (महसूस {feels_like}°C जैसा)। आर्द्रता {humidity}% है और हवा की गति {wind_speed} किमी/घंटा है।",
        "temperature": "{location} में वर्तमान तापमान {temperature}°C है, महसूस {feels_like}°C जैसा होता है।",
        "rain_now": "{location} में अभी बारिश की संभावना {rain_probability}% है। स्थिति: {condition}.",
        "rain_today": "{location} में आज बारिश की संभावना लगभग {rain_probability}% है, स्थिति {condition} रहने की उम्मीद है।",
        "rain_tomorrow": "{location} में कल बारिश की संभावना लगभग {rain_probability}% है, स्थिति {condition} रहने की उम्मीद है।",
        "rain_forecast": "{location} में कल बारिश की संभावना लगभग {rain_probability}% है, स्थिति {condition} रहने की उम्मीद है।",
        "forecast": "{location} का पूर्वानुमान: {condition}, अधिकतम तापमान {temp_max}°C और न्यूनतम {temp_min}°C रहने की संभावना है।",
        "alerts_none": "{location} के लिए अभी कोई सक्रिय मौसम चेतावनी नहीं है। स्थिति सामान्य है।",
        "alerts_some": "⚠️ {location} के लिए {count} सक्रिय चेतावनी: {alert_summary}",
        "heatwave_precaution": "{location} में वर्तमान तापमान {temperature}°C है। लू के दौरान: पानी पीते रहें, दोपहर 12-3 बजे धूप से बचें, हल्के सूती कपड़े पहनें, बुजुर्गों और बच्चों का ध्यान रखें।",
        "out_of_scope": (
    "क्षमा करें, मैं केवल मौसम, मौसम के पूर्वानुमान, "
    "चेतावनी और कृषि मौसम सलाह से संबंधित प्रश्नों का उत्तर दे सकता हूँ।"
)
    },
}


CONDITION_HI = {
    "Clear": "साफ़", "Partly Cloudy": "आंशिक बादल", "Cloudy": "बादल छाए हुए",
    "Light Rain": "हल्की बारिश", "Moderate Rain": "मध्यम बारिश",
    "Thunderstorm": "आंधी-तूफान", "Haze": "धुंध",
}


def generate_response_rule_based(intent: str, language: str, context: dict) -> str:
    """Fills in a template using ONLY real data passed in `context`."""
    lang = language if language in TEMPLATES else "en"
    template_set = TEMPLATES[lang]
    template = template_set.get(intent, template_set["current_weather"])

    render_context = dict(context)
    if lang == "hi" and "condition" in render_context:
        render_context["condition"] = CONDITION_HI.get(render_context["condition"], render_context["condition"])

    try:
        return template.format(**render_context)
    except KeyError:
        # If context is missing a field the template needs, fall back safely
        return template_set["current_weather"].format(**{**render_context, **_safe_defaults()})


def _safe_defaults():
    return {"condition": "Clear", "temperature": "N/A", "feels_like": "N/A",
            "humidity": "N/A", "wind_speed": "N/A", "location": "your location"}


async def generate_response_llm(intent: str, language: str, context: dict, raw_query: str) -> str:
    """
    Asks Claude to phrase the answer using ONLY the retrieved weather
    context below — it is explicitly instructed not to invent numbers.
    If this call fails for any reason, the caller falls back to the
    rule-based template above.
    """
    lang_name = "Hindi" if language == "hi" else "English"
    system_prompt = (
        "You are WeatherGPT, a weather assistant for Indian users. "
        "You are given REAL weather data as JSON context. "
        "Write ONE short, natural, friendly sentence or two answering the user's question "
        f"in {lang_name}. "
        "CRITICAL RULE: Use ONLY the numbers given in the context. "
        "NEVER invent, estimate, or guess any weather value not present in the context."
    )
    user_prompt = f"User question: {raw_query}\nIntent: {intent}\nWeather context: {json.dumps(context)}"

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 200,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}],
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"].strip()


async def generate_response(intent: str, language: str, context: dict, raw_query: str) -> tuple[str, str]:
    """
    Returns (response_text, method_used). Tries the LLM first if
    configured, otherwise (or on failure) uses the rule-based template.
    """
    if USE_LLM:
        try:
            text = await generate_response_llm(intent, language, context, raw_query)
            return text, "llm"
        except Exception:
            pass  # fall through to rule-based
    return generate_response_rule_based(intent, language, context), "rule_based"

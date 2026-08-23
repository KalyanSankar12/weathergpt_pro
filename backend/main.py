"""
main.py
--------
Entry point of the WeatherGPT backend.

An "API endpoint" is just a URL that, when your frontend (or anyone)
sends a request to it, runs some Python code and returns a JSON
answer. FastAPI wires each Python function below to a URL using the
@app.get(...) / @app.post(...) decorators.

Run this file with:  uvicorn main:app --reload --port 8000
Interactive API docs auto-appear at: http://localhost:8000/docs
"""

import os
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv()  # reads variables from .env into os.environ

import database
import weather_service
import ai_service
import alert_service
import agriculture_service
from schemas import ChatRequest, ChatResponse, AgricultureRequest, AgricultureResponse

DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"

app = FastAPI(title="WeatherGPT API", version="0.1.0")

# CORS: allows the frontend (running on a different port/origin during
# development) to call this API. In production you'd restrict this to
# your actual domain instead of "*".
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    database.init_db()


# -----------------------------------------------------------------
# Health check
# -----------------------------------------------------------------
@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "demo_mode": DEMO_MODE,
        "weather_provider": type(weather_service.get_weather_provider()).__name__,
        "llm_enabled": ai_service.USE_LLM,
        "timestamp": datetime.utcnow().isoformat(),
    }


# -----------------------------------------------------------------
# Weather endpoints
# -----------------------------------------------------------------
@app.get("/api/weather/current")
async def weather_current(location: str = "Indore"):
    data = await weather_service.get_current_weather_safe(location)
    database.log_query(f"current weather {location}", location, "current_weather")
    return data


@app.get("/api/weather/forecast")
async def weather_forecast(location: str = "Indore", days: int = 7):
    provider = weather_service.get_weather_provider()
    try:
        data = await provider.get_forecast(location, days)
    except Exception:
        data = await weather_service.MockWeatherProvider().get_forecast(location, days)
    database.log_query(f"forecast {location}", location, "forecast")
    return {"location": location.title(), "forecast": data}


@app.get("/api/weather/hourly")
async def weather_hourly(location: str = "Indore", hours: int = 12):
    provider = weather_service.get_weather_provider()
    try:
        data = await provider.get_hourly(location, hours)
    except Exception:
        data = await weather_service.MockWeatherProvider().get_hourly(location, hours)
    return {"location": location.title(), "hourly": data}


# -----------------------------------------------------------------
# Chat endpoint — the WeatherGPT conversational core
# -----------------------------------------------------------------
@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="message cannot be empty")

    # STEP 1: understand the question (rule-based NLU, see ai_service.py)
    parsed = ai_service.parse_query(req.message)
    intent, location, language = parsed["intent"], parsed["location"], parsed["language"]

    # STEP 2: fetch REAL data for that location (never invented by AI)
    weather = await weather_service.get_current_weather_safe(location)

    # STEP 3: for forecast-flavoured intents, blend in tomorrow's forecast data
    context = dict(weather)
    if intent in ("forecast", "rain_forecast"):
        provider = weather_service.get_weather_provider()
        try:
            forecast = await provider.get_forecast(location, days=2)
        except Exception:
            forecast = await weather_service.MockWeatherProvider().get_forecast(location, days=2)
        if len(forecast) > 1:
            context.update(forecast[1])  # tomorrow

    # STEP 4: if this is an alert-related question, evaluate alerts now
    alert_summary = ""
    if intent == "alerts":
        alerts = alert_service.evaluate_alerts(weather)
        if alerts:
            intent = "alerts_some"
            context["count"] = len(alerts)
            context["alert_summary"] = "; ".join(a["type"] for a in alerts)
        else:
            intent = "alerts_none"

    # STEP 5: agriculture questions get routed with a generic wheat example
    # (the dedicated /api/agriculture/advisory endpoint handles specific crops)
    if intent == "agriculture":
        advisories = agriculture_service.get_advisory("wheat", weather)
        reply = " ".join(advisories)
        database.log_chat(req.message, reply, language)
        return ChatResponse(reply=reply, intent=intent, location=location.title(),
                             data_source=weather.get("data_source", "mock"), weather_data=weather)

    # STEP 6: turn the real data into a natural-language sentence
    reply, method = await ai_service.generate_response(intent, language, context, req.message)

    database.log_query(req.message, location, intent)
    database.log_chat(req.message, reply, language)

    return ChatResponse(
        reply=reply,
        intent=intent,
        location=location.title(),
        data_source=weather.get("data_source", "mock"),
        weather_data=weather,
    )


# -----------------------------------------------------------------
# Alerts endpoint
# -----------------------------------------------------------------
@app.get("/api/alerts")
async def alerts(location: str = "Indore"):
    weather = await weather_service.get_current_weather_safe(location)
    forecast_alerts = []
    try:
        provider = weather_service.get_weather_provider()
        forecast = await provider.get_forecast(location, days=1)
        if forecast:
            merged = {**weather, **forecast[0]}
            forecast_alerts = alert_service.evaluate_alerts(merged)
    except Exception:
        forecast_alerts = alert_service.evaluate_alerts(weather)

    if not forecast_alerts:
        forecast_alerts = alert_service.evaluate_alerts(weather)

    if forecast_alerts:
        database.save_alerts(location.title(), forecast_alerts)

    return {"location": location.title(), "alert_count": len(forecast_alerts), "alerts": forecast_alerts}


# -----------------------------------------------------------------
# Agriculture advisory endpoint
# -----------------------------------------------------------------
@app.post("/api/agriculture/advisory", response_model=AgricultureResponse)
async def agriculture_advisory(req: AgricultureRequest):
    valid_crops = ["wheat", "rice", "soybean", "cotton", "maize"]
    if req.crop.lower() not in valid_crops:
        raise HTTPException(status_code=400, detail=f"crop must be one of {valid_crops}")

    weather = await weather_service.get_current_weather_safe(req.location)
    advisories = agriculture_service.get_advisory(req.crop, weather)
    database.save_agriculture_profile(req.crop, req.location.title(), " | ".join(advisories))

    return AgricultureResponse(
        crop=req.crop.title(),
        location=req.location.title(),
        advisories=advisories,
        disclaimer=agriculture_service.DISCLAIMER,
    )


# -----------------------------------------------------------------
# Climate trends (demo/historical dataset — clearly labelled as such)
# -----------------------------------------------------------------
@app.get("/api/climate/trends")
async def climate_trends(location: str = "Indore"):
    # Small illustrative demo dataset. Clearly NOT official IMD records —
    # in a real deployment this would be replaced by an IMDClimateProvider.
    rng_seed = sum(ord(c) for c in location.lower())
    import random
    rng = random.Random(rng_seed)
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    monthly_rainfall = [round(rng.uniform(0, 20), 1) if m not in ("Jun", "Jul", "Aug", "Sep")
                         else round(rng.uniform(100, 300), 1) for m in months]
    monthly_avg_temp = [round(rng.uniform(12, 20), 1) if m in ("Dec", "Jan") else
                         round(rng.uniform(30, 42), 1) if m in ("Apr", "May", "Jun") else
                         round(rng.uniform(22, 30), 1) for m in months]

    return {
        "location": location.title(),
        "data_source": "DEMO DATASET — illustrative only, not official IMD records",
        "months": months,
        "monthly_rainfall_mm": monthly_rainfall,
        "monthly_avg_temp_c": monthly_avg_temp,
        "yearly_total_rainfall_mm": round(sum(monthly_rainfall), 1),
    }


# -----------------------------------------------------------------
# Admin stats (simple, no auth yet — fine for an SIH prototype)
# -----------------------------------------------------------------
@app.get("/api/admin/stats")
def admin_stats():
    stats = database.get_stats()
    stats["demo_mode"] = DEMO_MODE
    stats["weather_provider"] = type(weather_service.get_weather_provider()).__name__
    return stats


# -----------------------------------------------------------------
# Serve the frontend (simple static files — no separate frontend server needed)
# -----------------------------------------------------------------
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

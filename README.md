# WeatherGPT

**Conversational AI for Weather Forecasting, Alerts, and Climate Information**
Smart India Hackathon 2026 — **SIH26068**
Organization: Ministry of Earth Sciences (MoES) · Department: India Meteorological Department (IMD)
Theme: Disaster Management

---

## What this is

WeatherGPT is a chat-first weather platform. A user asks a question in plain English or Hindi
("Will it rain tomorrow in Indore?", "कल इंदौर में बारिश होगी क्या?"), and the system:

1. Understands the question (intent, location, language)
2. Fetches **real weather data** for that location
3. Runs it through a rule-based alert/risk engine
4. Turns the retrieved data into a natural-language answer

It also provides a full dashboard (current conditions, hourly/7-day forecast, alerts,
crop advisory, and demo climate charts) built on the same data layer as the chatbot.

## Why this architecture — the "no-hallucination" rule

**The AI layer never invents a weather number.** Intent understanding and sentence phrasing
are the AI's only jobs. All temperatures, rainfall %, and alert thresholds come from the
`weather_service.py` data layer and `alert_service.py` rule engine — deterministic Python code,
not a language model. This is why the project doesn't need a trained ML model: intent
classification over a fixed vocabulary of weather questions is solved well by keyword rules,
and alert thresholds are already defined by meteorological standards (not something to "learn").

```
User question
   │
   ▼
ai_service.parse_query()      → intent, location, language   (rule-based, or LLM-assisted if configured)
   │
   ▼
weather_service.get_current_weather_safe()  → REAL weather numbers (never touched by AI)
   │
   ▼
alert_service.evaluate_alerts()             → rule-based risk/severity
   │
   ▼
ai_service.generate_response()              → phrases the real numbers into a sentence
   │
   ▼
User sees answer
```

## Tech stack

| Layer      | Choice                    | Why |
|------------|---------------------------|-----|
| Backend    | Python + FastAPI          | Simple, async, auto-generates API docs |
| Frontend   | HTML + CSS + vanilla JS   | No build tooling needed; easy to explain line-by-line |
| Database   | SQLite (`weathergpt.db`)  | Zero setup; swappable for PostgreSQL later (see below) |
| Weather    | OpenWeatherMap API, behind a `WeatherProvider` abstraction | Swappable for an official IMD source later without touching other code |
| AI         | Rule-based NLU + templates, optional Anthropic Claude for phrasing | Works with zero API keys; upgrades gracefully if a key is added |
| Charts     | Chart.js                  | Lightweight, no build step |
| Maps       | Leaflet + OpenStreetMap (Phase 10 — not yet wired into this MVP) | |
| Voice      | Browser `SpeechRecognition` / `speechSynthesis` | No paid speech API needed |

## Project structure

```
WeatherGPT/
├── backend/
│   ├── main.py                 # FastAPI app + all API endpoints, serves frontend
│   ├── database.py             # SQLite tables + helper functions
│   ├── schemas.py              # Pydantic request/response models
│   ├── weather_service.py      # WeatherProvider abstraction (Mock + Real)
│   ├── ai_service.py           # Intent parsing + response generation
│   ├── alert_service.py        # Rule-based alert/risk engine
│   ├── agriculture_service.py  # Rule-based crop advisory engine
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── .env.example
├── .gitignore
└── README.md
```

## Running it

```bash
cd WeatherGPT
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

pip install -r backend/requirements.txt

copy .env.example .env       # Windows
cp .env.example .env         # Mac/Linux

cd backend
uvicorn main:app --reload --port 8000
```

Then open **http://localhost:8000** — the backend serves the frontend directly, so you don't
need a separate frontend server. Interactive API docs are at **http://localhost:8000/docs**.

## Demo mode

`.env` ships with `DEMO_MODE=true`. In this mode:
- Weather data comes from `MockWeatherProvider` (realistic, seeded-random data — no internet needed)
- Chat uses the rule-based NLU + templates (no LLM key needed)
- Alerts and agriculture advisories run on the mock data
- The UI shows a **DEMO MODE** badge so nobody mistakes it for live data

To go live: get a free key at [openweathermap.org/api](https://openweathermap.org/api), put it
in `.env` as `WEATHER_API_KEY`, and set `DEMO_MODE=false`. If the real API call ever fails at
runtime (bad key, no internet, rate limit), the app **automatically falls back to mock data**
instead of crashing — this is what keeps the demo safe even with a flaky venue connection.

Adding `ANTHROPIC_API_KEY` is optional — it upgrades the chatbot's phrasing to an LLM call, but
the LLM is only ever given the real weather numbers as context and is instructed not to invent any.

## Database schema

| Table | Purpose |
|---|---|
| `weather_queries` | Every question asked, with detected location/intent |
| `chat_history` | Full conversation log (question + answer) |
| `alerts` | Alerts generated by the rule engine |
| `agriculture_profiles` | Crop/location advisories generated |

SQLite is used via Python's built-in `sqlite3` module (no ORM) to keep the code readable for a
beginner. To move to PostgreSQL later: swap the `sqlite3.connect()` call in `database.py` for a
`psycopg2`/`asyncpg` connection — the table schemas and query logic don't need to change.

## What's implemented in this MVP vs. what's next

**Implemented:** current weather, hourly + 7-day forecast, WeatherGPT chat (English + Hindi),
voice input/output via the browser, rule-based alert engine, rule-based agriculture advisory
(5 crops), demo climate trend charts, admin stats endpoint, demo mode with automatic fallback.

**Not yet implemented (next phases):** interactive Leaflet map, a dedicated polished admin
dashboard page, Docker packaging, automated test suite, additional Indian languages.
The architecture (`WeatherProvider`, `AlertProvider`-style rule engine) is built so these can be
added without reworking existing code.

## Honest data-source policy

- Current/forecast weather: **real** OpenWeatherMap data when `DEMO_MODE=false` and a valid key
  is set; otherwise clearly-labeled **mock** data.
- Climate trend charts: an illustrative **demo dataset**, explicitly labeled as such — not
  official IMD historical records.
- This project is **designed for integration with official IMD meteorological services**
  (via the `WeatherProvider` interface) — it does not claim to already be integrated with IMD.

## Answering likely SIH judge questions

- **"How does your AI work?"** — A rule-based NLU layer extracts intent/location/language from
  the question; an LLM (optional) or template engine phrases the answer using only retrieved data.
- **"Where does weather data come from?"** — A pluggable `WeatherProvider`; currently
  OpenWeatherMap or seeded mock data, designed to be replaced by an IMD data source.
- **"How do you prevent hallucination?"** — The LLM is never asked to produce a weather number;
  it only rephrases numbers already fetched from the weather service.
- **"How does your alert system work?"** — Fixed meteorological thresholds (heat, rainfall,
  wind, visibility) evaluated in Python — fully explainable, no ML needed.
- **"Why an LLM instead of training your own model?"** — Intent classification over a small,
  well-defined question vocabulary doesn't need ML; and no labeled weather-forecast training
  data exists for this project. An LLM/rules combination reaches high accuracy with zero training
  data and stays fully explainable to judges and end users.

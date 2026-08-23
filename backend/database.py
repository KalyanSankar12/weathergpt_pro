"""
database.py
------------
Handles the SQLite database for WeatherGPT.

We use Python's built-in `sqlite3` module directly (no ORM like SQLAlchemy)
to keep things beginner-friendly. SQLite stores everything in a single
file: weathergpt.db, which is created automatically the first time you
run the app.

Tables:
  - weather_queries   : every question a user asks WeatherGPT
  - chat_history       : full chat conversation log (question + answer)
  - alerts              : alerts that have been generated
  - agriculture_profiles: saved crop/location selections per session
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime

DB_PATH = "weathergpt.db"


def init_db():
    """Create all tables if they don't already exist. Called once at startup."""
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS weather_queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_text TEXT NOT NULL,
                location TEXT,
                intent TEXT,
                created_at TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_message TEXT NOT NULL,
                bot_response TEXT NOT NULL,
                language TEXT DEFAULT 'en',
                created_at TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                location TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                recommendation TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agriculture_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crop TEXT NOT NULL,
                location TEXT NOT NULL,
                advisory TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        conn.commit()


@contextmanager
def get_connection():
    """Provides a database connection that automatically closes itself."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets us access columns by name
    try:
        yield conn
    finally:
        conn.close()


def log_query(query_text: str, location: str, intent: str):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO weather_queries (query_text, location, intent, created_at) VALUES (?, ?, ?, ?)",
            (query_text, location, intent, datetime.utcnow().isoformat()),
        )
        conn.commit()


def log_chat(user_message: str, bot_response: str, language: str = "en"):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO chat_history (user_message, bot_response, language, created_at) VALUES (?, ?, ?, ?)",
            (user_message, bot_response, language, datetime.utcnow().isoformat()),
        )
        conn.commit()


def save_alerts(location: str, alerts: list[dict]):
    with get_connection() as conn:
        for a in alerts:
            conn.execute(
                """INSERT INTO alerts (location, alert_type, severity, message, recommendation, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (location, a["type"], a["severity"], a["message"], a["recommendation"], datetime.utcnow().isoformat()),
            )
        conn.commit()


def save_agriculture_profile(crop: str, location: str, advisory: str):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO agriculture_profiles (crop, location, advisory, created_at) VALUES (?, ?, ?, ?)",
            (crop, location, advisory, datetime.utcnow().isoformat()),
        )
        conn.commit()


def get_stats():
    """Used by the admin dashboard later. Returns simple usage stats."""
    with get_connection() as conn:
        total_queries = conn.execute("SELECT COUNT(*) as c FROM weather_queries").fetchone()["c"]
        total_chats = conn.execute("SELECT COUNT(*) as c FROM chat_history").fetchone()["c"]
        top_locations = conn.execute(
            """SELECT location, COUNT(*) as count FROM weather_queries
               WHERE location IS NOT NULL GROUP BY location ORDER BY count DESC LIMIT 5"""
        ).fetchall()
        active_alerts = conn.execute("SELECT COUNT(*) as c FROM alerts").fetchone()["c"]

        return {
            "total_queries": total_queries,
            "total_chats": total_chats,
            "top_locations": [dict(row) for row in top_locations],
            "active_alerts": active_alerts,
        }

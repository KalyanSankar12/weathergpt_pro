"""
schemas.py
-----------
Pydantic models define the "shape" of data going in and out of our API.
FastAPI uses these to validate requests automatically and to generate
the interactive docs at /docs.
"""

from pydantic import BaseModel
from typing import Optional


class ChatRequest(BaseModel):
    message: str
    language: Optional[str] = "en"  # "en" or "hi"


class ChatResponse(BaseModel):
    reply: str
    intent: str
    location: Optional[str] = None
    data_source: str  # "real" or "mock"
    weather_data: Optional[dict] = None


class AgricultureRequest(BaseModel):
    crop: str
    location: str
    language: Optional[str] = "en"


class AgricultureResponse(BaseModel):
    crop: str
    location: str
    advisories: list[str]
    disclaimer: str

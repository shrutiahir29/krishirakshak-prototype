"""
KrishiRakshak Backend
======================
FastAPI entrypoint. Run with:
    uvicorn app.main:app --reload --port 8000

Then visit http://localhost:8000/docs for interactive API docs (auto-generated
by FastAPI — great for testing each module as we build it).
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from app.routers import weather, soil_moisture, pest_risk, irrigation, crop_recommendation, disease_detection

app = FastAPI(
    title="KrishiRakshak API",
    description="Predict. Detect. Irrigate. Protect. — AI-driven smart farming backend.",
    version="0.1.0",
)

# ALLOWED_ORIGINS is a comma-separated env var, e.g.
#   ALLOWED_ORIGINS=https://krishirakshak.vercel.app,http://localhost:3000
# Falls back to localhost-only if not set, so local dev keeps working out of the box.
_origins_env = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173,http://localhost:8080")
ALLOWED_ORIGINS = [o.strip() for o in _origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(weather.router)
app.include_router(soil_moisture.router)
app.include_router(pest_risk.router)
app.include_router(irrigation.router)
app.include_router(crop_recommendation.router)
app.include_router(disease_detection.router)


@app.get("/")
async def root():
    return {"status": "ok", "message": "KrishiRakshak API is running 🌾"}


@app.get("/health")
async def health():
    return {"status": "healthy"}

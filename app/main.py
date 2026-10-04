"""FastAPI service: JSON API plus the static dashboard."""
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .optimizer import ET_MM_PER_DAY, HOURS, SKY_CLOUD, build_plan
from .weather import fetch_forecast

STATIC = Path(__file__).resolve().parent.parent / "static"
app = FastAPI(title="WaterBattery", version="1.0.0",
              description="Solar-synced smart irrigation scheduler")


class PlanRequest(BaseModel):
    crop: str = "tomato"
    acres: float = Field(4, gt=0, le=100)
    sky: str = "clear"
    cloud_cover: list[float] | None = None   # 48 hourly values, 0-100
    rain_mm: list[float] = Field(default_factory=lambda: [0.0, 0.0])
    pump_kw: float = Field(3.0, gt=0, le=50)
    flow_m3h: float = Field(12.0, gt=0, le=500)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/crops")
def crops():
    return ET_MM_PER_DAY


@app.post("/api/plan")
def plan(req: PlanRequest):
    crop = req.crop.lower()
    if crop not in ET_MM_PER_DAY:
        raise HTTPException(422, f"Unknown crop. Choose one of: {', '.join(ET_MM_PER_DAY)}")
    if req.cloud_cover is not None:
        if len(req.cloud_cover) != HOURS:
            raise HTTPException(422, "cloud_cover must have 48 hourly values")
        cloud = [min(100.0, max(0.0, c)) for c in req.cloud_cover]
    elif req.sky in SKY_CLOUD:
        cloud = [SKY_CLOUD[req.sky]] * HOURS
    else:
        raise HTTPException(422, f"sky must be one of: {', '.join(SKY_CLOUD)}")
    if len(req.rain_mm) != 2 or min(req.rain_mm) < 0:
        raise HTTPException(422, "rain_mm needs two non-negative daily values")
    return build_plan(crop, req.acres, cloud, req.rain_mm, req.pump_kw, req.flow_m3h)


@app.get("/api/forecast")
def forecast(lat: float = Query(..., ge=-90, le=90), lon: float = Query(..., ge=-180, le=180)):
    try:
        return fetch_forecast(lat, lon)
    except (httpx.HTTPError, ValueError, KeyError) as e:
        raise HTTPException(502, f"Weather service unavailable: {e}")


app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC / "index.html")

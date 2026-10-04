# WaterBattery: solar-synced smart irrigation

Water in a tank or soil is stored energy. WaterBattery schedules irrigation for hours when solar power is
plentiful and cheap, skips irrigation before forecast rain, and still delivers the crop's water need.
Built for the Sustainable Agriculture challenge (energy, water and productivity).

## How it works
1. Inputs: crop, field size, 48 h cloud cover and rain (scenario or live from Open-Meteo).
2. Crop water demand = daily evapotranspiration for the crop x field area, minus usable rain.
3. A greedy optimizer fills the cheapest effective-price hours (grid tariff discounted by sun) first.
4. The dashboard compares it with a fixed timer: cost, water, solar share and CO2.

## Run locally
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
uvicorn app.main:app --reload      # http://localhost:8000  (API docs: /docs)
```

## API
| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/api/crops` | Supported crops and daily demand (mm) |
| POST | `/api/plan` | Build a 48 h plan (`crop`, `acres`, `sky` or `cloud_cover`, `rain_mm`) |
| GET | `/api/forecast?lat=&lon=` | Live cloud and rain forecast (Open-Meteo) |

## Deploy
- **Render (free):** push to GitHub, then New > Blueprint and select the repo. `render.yaml` does the rest.
- **Any Docker host (Railway, Fly.io, Cloud Run):** `docker build -t waterbattery . && docker run -p 8000:8000 waterbattery`. The container honors `$PORT`.

## Assumptions (edit in `app/optimizer.py`)
Typical crop ET, a 3 kW / 12 m3-per-hour pump, illustrative three-tier tariff, timers over-water by 25%,
80% of rain is usable, 0.82 kg CO2 per grid kWh. Replace with local data for a real pilot.

## Roadmap
Soil-moisture sensor input, relay control of the pump, tank-capacity constraints, multi-field and
cooperative scheduling, SMS/WhatsApp alerts.

## License
MIT

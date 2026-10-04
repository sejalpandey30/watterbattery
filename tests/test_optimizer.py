from fastapi.testclient import TestClient

from app.main import app
from app.optimizer import build_plan, solar_factor

client = TestClient(app)
CLEAR = [0.0] * 48


def test_solar_curve_shape():
    assert solar_factor(2) == 0 and solar_factor(20) == 0
    assert solar_factor(12) > solar_factor(7) > 0


def test_schedule_bounds_and_solar_window():
    p = build_plan("tomato", 4, CLEAR, [0, 0])
    for key in ("baseline", "optimized"):
        assert all(0 <= x <= 1 for x in p[key]["schedule"])
    on = [h % 24 for h, x in enumerate(p["optimized"]["schedule"]) if x > 0]
    assert on and all(6 <= h < 18 for h in on)


def test_optimized_is_cheaper_and_uses_less_water():
    p = build_plan("tomato", 4, CLEAR, [0, 0])
    assert p["optimized"]["cost"] < p["baseline"]["cost"]
    assert p["savings"]["water_m3"] > 0 and p["savings"]["co2_kg"] > 0


def test_meets_crop_demand_without_rain():
    p = build_plan("maize", 3, CLEAR, [0, 0])
    assert abs(p["optimized"]["water_m3"] - sum(p["demand_m3"])) < 0.5


def test_heavy_rain_skips_day():
    p = build_plan("wheat", 4, CLEAR, [0, 12])
    assert sum(p["optimized"]["schedule"][24:]) == 0
    assert sum(p["baseline"]["schedule"][24:]) > 0


def test_api_health_and_plan():
    assert client.get("/health").json() == {"status": "ok"}
    r = client.post("/api/plan", json={"crop": "rice", "acres": 2, "sky": "partly"})
    assert r.status_code == 200 and len(r.json()["sun"]) == 48


def test_api_validation():
    assert client.post("/api/plan", json={"crop": "kale"}).status_code == 422
    assert client.post("/api/plan", json={"sky": "stormy"}).status_code == 422
    assert client.post("/api/plan", json={"cloud_cover": [1, 2]}).status_code == 422
    assert client.post("/api/plan", json={"acres": -1}).status_code == 422


def test_index_served():
    assert "WaterBattery" in client.get("/").text

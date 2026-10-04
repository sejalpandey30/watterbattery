"""Core scheduling logic (pure Python, no I/O).

Idea: water in a tank or soil is stored energy. Pump when solar power is plentiful
and cheap, skip irrigation before rain, and still deliver the crop's water need.
"""
import math

ET_MM_PER_DAY = {"tomato": 5.0, "wheat": 4.0, "maize": 5.5, "rice": 8.0}
SKY_CLOUD = {"clear": 0.0, "partly": 40.0, "overcast": 80.0}
M3_PER_ACRE_MM = 4.047       # 1 mm of water over 1 acre
TIMER_OVERIRRIGATION = 1.25  # fixed timers typically over-water
RAIN_EFFECTIVE = 0.8         # share of rainfall the crop can use
SOLAR_DISCOUNT = 0.85        # cost cut when pumping directly on sun
GRID_EF = 0.82               # kg CO2 per grid kWh
HOURS = 48


def solar_factor(hour: int, cloud_pct: float = 0.0) -> float:
    """Relative solar output (0..1) for the hour slot starting at `hour`."""
    t = hour % 24
    if t < 6 or t >= 18:
        return 0.0
    return math.sin(math.pi * (t + 0.5 - 6) / 12) * (1 - 0.75 * cloud_pct / 100)


def tariff(hour: int) -> float:
    """Illustrative grid price per kWh: off-peak, day, evening peak."""
    t = hour % 24
    return 5.0 if t >= 22 or t < 6 else 11.0 if t >= 18 else 7.0


def effective_price(hour: int, cloud_pct: float) -> float:
    return tariff(hour) * (1 - SOLAR_DISCOUNT * solar_factor(hour, cloud_pct))


def _allocate(sched, slots, hours):
    for s in slots:
        if hours <= 1e-9 or s >= HOURS:
            break
        x = min(1.0 - sched[s], hours, 1.0)
        sched[s] += x
        hours -= x


def _totals(sched, cloud, kw, flow):
    kwh = cost = grid = 0.0
    for h, x in enumerate(sched):
        q = x * kw
        kwh += q
        cost += q * effective_price(h, cloud[h])
        grid += q * (1 - solar_factor(h, cloud[h]))
    return {"schedule": [round(x, 3) for x in sched], "kwh": kwh, "cost": cost,
            "grid_kwh": grid, "water_m3": sum(sched) * flow}


def _window(sched, d):
    on = [h - d * 24 for h in range(d * 24, d * 24 + 24) if sched[h] > 0.01]
    return (min(on), max(on) + 1) if on else None


def build_plan(crop, acres, cloud, rain_mm, pump_kw=3.0, flow_m3h=12.0):
    """Return baseline (fixed timer) vs optimized (WaterBattery) 48 h plans."""
    et = ET_MM_PER_DAY[crop]
    m3 = acres * M3_PER_ACRE_MM
    base, opt = [0.0] * HOURS, [0.0] * HOURS
    demand, notes = [], []
    for d in range(2):
        full = et * m3
        need = max(0.0, et - RAIN_EFFECTIVE * rain_mm[d]) * m3
        demand.append(need)
        tb = min(24.0, TIMER_OVERIRRIGATION * full / flow_m3h)
        _allocate(base, range(d * 24 + 6, d * 24 + 18), tb / 2)
        _allocate(base, range(d * 24 + 18, d * 24 + 30), tb / 2)
        hrs = sorted(range(d * 24, d * 24 + 24),
                     key=lambda h: (effective_price(h, cloud[h]), abs(h % 24 - 12)))
        _allocate(opt, hrs, min(24.0, need / flow_m3h))
        w = _window(opt, d)
        if rain_mm[d] > 0:
            notes.append(f"Day {d+1}: {rain_mm[d]:.0f} mm rain forecast cuts the need "
                         f"from {full:.0f} to {need:.0f} m3.")
        notes.append(f"Day {d+1}: " + (f"pumps {w[0]:02d}:00 to {w[1]:02d}:00, the cheapest solar-rich window."
                                       if w else "no pumping needed."))
    B = _totals(base, cloud, pump_kw, flow_m3h)
    O = _totals(opt, cloud, pump_kw, flow_m3h)
    savings = {
        "cost_pct": round(100 * (1 - O["cost"] / B["cost"])) if B["cost"] else 0,
        "water_m3": round(B["water_m3"] - O["water_m3"], 1),
        "solar_share_pct": round(100 * (1 - O["grid_kwh"] / O["kwh"])) if O["kwh"] else 0,
        "co2_kg": round((B["grid_kwh"] - O["grid_kwh"]) * GRID_EF, 1),
    }
    notes.append("The fixed timer over-waters by 25% and ignores rain and sunshine.")
    return {"crop": crop, "demand_m3": [round(x, 1) for x in demand],
            "baseline": B, "optimized": O, "savings": savings, "notes": notes,
            "sun": [round(solar_factor(h, cloud[h]), 3) for h in range(HOURS)],
            "tariff": [tariff(h) for h in range(HOURS)],
            "cloud_cover": cloud}

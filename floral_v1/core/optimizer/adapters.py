from __future__ import annotations

import json
import math
from datetime import datetime, timedelta
from pathlib import Path
import sys
from typing import Dict, Iterable, List, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parents[3]
DIGITAL_TWIN_SRC = REPO_ROOT / "digital_twin_ryan" / "src"
if str(DIGITAL_TWIN_SRC) not in sys.path:
    sys.path.insert(0, str(DIGITAL_TWIN_SRC))
COST_DATA_PATH = REPO_ROOT / "digital_twin_ryan" / "cost_data.json"
DEFAULT_SIM_HOURS = 168

import numpy as np
from digital_twin.simulation.run import run_hourly_simulation
from floral_v1.core.models import SiteModel


def load_cost_data() -> dict:
    try:
        text = COST_DATA_PATH.read_text(encoding="utf-8")
        return json.loads(text)
    except OSError:
        return {}
    except json.JSONDecodeError:
        return {}


def repeat_load_profile(load_profile_kw: Sequence[float], hours: int, fallback_kw: float) -> List[float]:
    pattern = list(load_profile_kw) or [fallback_kw]
    if not pattern:
        pattern = [fallback_kw]
    series: List[float] = []
    for idx in range(hours):
        series.append(float(pattern[idx % len(pattern)]))
    return series


def build_timestamps(start: datetime, hours: int) -> List[str]:
    return [(start + timedelta(hours=idx)).isoformat() for idx in range(hours)]


def synthesize_pv_profile(hours: int, capacity_kw: float) -> List[float]:
    if capacity_kw <= 0:
        return [0.0] * hours
    profile: List[float] = []
    for idx in range(hours):
        hour = idx % 24
        if 6 <= hour <= 18:
            x = (hour - 6) / 12.0
            irradiance = math.sin(math.pi * x)
            profile.append(max(0.0, irradiance) * capacity_kw)
        else:
            profile.append(0.0)
    return profile


def derive_pv_capacity_kw(site: SiteModel, load_kw: Sequence[float]) -> float:
    if site.buildable_area_acres > 0:
        density_kw_per_acre = 900.0
        return site.buildable_area_acres * density_kw_per_acre
    return max(load_kw, default=0.0) * 0.5


def pv_candidates(base_capacity_kw: float) -> List[float]:
    levels = {0.0}
    if base_capacity_kw > 0:
        levels.update({base_capacity_kw * 0.5, base_capacity_kw, base_capacity_kw * 1.25})
    return sorted(max(0.0, lvl) for lvl in levels)


def storage_candidates(pv_capacity_kw: float, pv_profile: Sequence[float], loads_kw: Sequence[float]) -> List[float]:
    pv_surplus_kwh = float(np.maximum(np.array(pv_profile) - np.array(loads_kw), 0.0).sum())
    denom = max(pv_capacity_kw, 1e-6)
    pv_surplus_hours = pv_surplus_kwh / denom
    hours_set = {0.0, 0.5, 1.0, 2.0, min(4.0, max(0.0, pv_surplus_hours))}
    return sorted(hours_set)


def capital_recovery_factor(rate: float, years: float) -> float:
    if rate <= 0 or years <= 0:
        return 1.0
    r = rate
    n = years
    return r * (1 + r) ** n / ((1 + r) ** n - 1)


def compute_lcoe(
    costs: Dict[str, Dict[str, float]],
    summary,
    pv_capacity_kw: float,
    pv_energy_kwh: float,
    bess_capacity_kwh: float,
    genset_energy_kwh: float,
    load_energy_kwh: float,
) -> float:
    if not costs:
        return float("inf")
    finance = costs.get("finance", {})
    pv_costs = costs.get("pv", {})
    bess_costs = costs.get("bess", {})
    genset_costs = costs.get("genset", {})
    fuel_costs = costs.get("fuel", {})

    discount_rate = float(finance.get("discount_rate", 0.1))
    project_life = float(finance.get("project_life_years", 25))

    energy_served = max(load_energy_kwh - summary.unserved_energy_kWh, 0.0)
    if energy_served <= 0:
        return float("inf")

    pv_capex = pv_capacity_kw * float(pv_costs.get("capex_per_kw", 0.0))
    pv_crf = capital_recovery_factor(discount_rate, float(pv_costs.get("lifetime_years", project_life)))
    pv_annualized = pv_capex * pv_crf
    pv_opex = pv_energy_kwh * float(pv_costs.get("opex_per_kwh_per_year", 0.0))

    bess_capex = bess_capacity_kwh * float(bess_costs.get("capex_per_kwh", 0.0))
    bess_crf = capital_recovery_factor(discount_rate, float(bess_costs.get("lifetime_years", project_life)))
    bess_annualized = bess_capex * bess_crf
    bess_opex = bess_capacity_kwh * float(bess_costs.get("opex_per_kwh_per_year", 0.0))

    genset_capacity_kw = summary.max_engines * float(genset_costs.get("unit_rating_kw", 2000.0))
    genset_capex = genset_capacity_kw * float(genset_costs.get("capex_per_kw", 0.0))
    genset_crf = capital_recovery_factor(discount_rate, float(genset_costs.get("lifetime_years", project_life)))
    genset_annualized = genset_capex * genset_crf
    genset_opex = genset_energy_kwh * float(genset_costs.get("opex_per_kwh", 0.0))

    fuel_energy_kwh = float(summary.total_fuel_Btu) / 3412.14163
    fuel_cost = fuel_energy_kwh * float(fuel_costs.get("cost_per_kwh", 0.0))

    total_cost = (
        pv_annualized
        + pv_opex
        + bess_annualized
        + bess_opex
        + genset_annualized
        + genset_opex
        + fuel_cost
    )
    return total_cost / energy_served


def evaluate_candidate(
    site: SiteModel,
    timestamps: Sequence[str],
    loads_kw: Sequence[float],
    pv_profile_kw: Sequence[float],
    pv_capacity_kw: float,
    storage_hours: float,
    cost_data: dict,
):
    peak_load_kw = max(loads_kw) if loads_kw else 0.0
    bess_capacity_kwh = max(5000.0, storage_hours * pv_capacity_kw)
    batt_power_kw = max(0.25 * peak_load_kw, 1000.0)
    bess_params = {
        "capacity_kwh": bess_capacity_kwh,
        "max_charge_kw": batt_power_kw,
        "max_discharge_kw": batt_power_kw,
        "min_soc_fraction": 0.2,
        "primary_reserve_kwh": 5000.0,
        "charge_efficiency": 0.95,
        "discharge_efficiency": 1.0,
    }
    ambient = float(site.metadata.get("ambient_c", 25.0)) if site.metadata else 25.0
    altitude_ft = float(site.site.altitude_m or 0.0) * 3.28084
    load_series = list(zip(timestamps, loads_kw))
    pv_series = list(zip(timestamps, pv_profile_kw)) if pv_capacity_kw > 0 else None
    temperature_series = [(ts, ambient) for ts in timestamps]

    summary = run_hourly_simulation(
        loads=load_series,
        pv_generation=pv_series,
        temperatures=temperature_series,
        altitude_ft=altitude_ft,
        bess_params=bess_params,
        initial_bess_soc_kwh=bess_capacity_kwh,
    )
    pv_energy_kwh = float(sum(pv_profile_kw))
    load_energy_kwh = float(sum(loads_kw))
    genset_energy_kwh = float(sum(summary.genset_load_trace))
    lcoe = compute_lcoe(
        cost_data,
        summary,
        pv_capacity_kw=pv_capacity_kw,
        pv_energy_kwh=pv_energy_kwh,
        bess_capacity_kwh=bess_capacity_kwh,
        genset_energy_kwh=genset_energy_kwh,
        load_energy_kwh=load_energy_kwh,
    )
    return {
        "summary": summary,
        "pv_capacity_kw": pv_capacity_kw,
        "pv_energy_kwh": pv_energy_kwh,
        "bess_capacity_kwh": bess_capacity_kwh,
        "bess_power_kw": batt_power_kw,
        "storage_hours": storage_hours,
        "lcoe": lcoe,
        "unserved_kwh": summary.unserved_energy_kWh,
    }

# digital_twin/models/g3520h_simple_derated.py
import bisect
import json
from pathlib import Path
from typing import Any, Dict, Sequence, Tuple, Union


def _data_path(filename: str) -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "raw" / filename

DERATION_JSON = _data_path("deration_factors_g3520h.json")
EMISSIONS_JSON = _data_path("emissions_g3520h.json")

# --- Load deration grid (same as before) ---
with open(DERATION_JSON) as f:
    GRID = json.load(f)

TEMPS = sorted(int(t) for t in GRID.keys())
ALTS  = sorted({int(a) for t in GRID for a in GRID[t]})

def _neighbors(arr: Sequence[int], v: float) -> Tuple[int, int]:
    j = bisect.bisect_left(arr, v)
    if j == 0: return 0, 0
    if j >= len(arr): return len(arr)-1, len(arr)-1
    return j-1, j

def derate_bilinear(temp_F: float, alt_ft: float) -> float:
    # (unchanged logic)
    i0,i1 = _neighbors(TEMPS, temp_F)
    j0,j1 = _neighbors(ALTS,  alt_ft)
    T0,T1 = TEMPS[i0], TEMPS[i1]
    A0,A1 = ALTS[j0],  ALTS[j1]
    def val(i,j):
        return GRID.get(str(TEMPS[i]), {}).get(str(ALTS[j]), None)
    f00,f10,f01,f11 = val(i0,j0), val(i1,j0), val(i0,j1), val(i1,j1)
    candidates = [v for v in (f00,f10,f01,f11) if v is not None]
    if not candidates:
        return 1.0
    def num(x):
        if x is None: return None
        return float(x)
    f00,f10,f01,f11 = map(num, (f00,f10,f01,f11))
    if i0==i1 and j0==j1:
        return f00 if f00 is not None else float(candidates[0])
    t = 0 if T1==T0 else (temp_F - T0)/(T1 - T0)
    u = 0 if A1==A0 else (alt_ft  - A0)/(A1 - A0)
    if f00 is None: f00 = float(candidates[0])
    if f10 is None: f10 = f00
    if f01 is None: f01 = f00
    if f11 is None: f11 = f00
    return (1-t)*(1-u)*f00 + t*(1-u)*f10 + (1-t)*u*f01 + t*u*f11

# --- Load emissions data (ordered 50%, 75%, 100%) ---
with open(EMISSIONS_JSON) as f:
    EMISSIONS = json.load(f)

NOX_G_BHP_HR = EMISSIONS["NOx_as_NO2"]  # 3-point array e.g. [0.50, 0.50, 0.50]:contentReference[oaicite:6]{index=6}
CO2_G_BHP_HR = EMISSIONS["CO2"]         # 3-point array e.g. [438.0, 420.0, 412.0]:contentReference[oaicite:7]{index=7}

# --- Base performance curves (keep your values/logic) ---
LOADS           = [0.50, 0.75, 1.00]
EKW_POINTS      = [1235, 1852, 2469]
FUEL_ISO_BTU_KWH= [8466, 8091, 7942]
GENSET_EFF      = [0.405, 0.424, 0.4328]

def lin(x: float, xs: Sequence[float], ys: Sequence[float]) -> float:
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(1, len(xs)):
        if x <= xs[i]:
            t = (x - xs[i-1])/(xs[i]-xs[i-1])
            return ys[i-1] + t*(ys[i]-ys[i-1])
    raise ValueError("Interpolation failed: input outside range.")

def g_bhp_hr_to_g_kwh(x: float) -> float:
    return x / 0.7457

def evaluate(
    load_frac: float,
    ambient_C: float = 25.0,
    altitude_ft: float = 0.0,
    fuel_LHV_Btu_per_scf: float = 905.0,
) -> Dict[str, Any]:
    # (your existing evaluate body remains the same):contentReference[oaicite:8]{index=8}
    ambient_F = ambient_C * 9/5 + 32
    der = derate_bilinear(ambient_F, altitude_ft)
    ekW_req = lin(load_frac, LOADS, EKW_POINTS)
    ekW_max = EKW_POINTS[-1] * der
    ekW = min(ekW_req, ekW_max)
    operating_frac = (ekW / EKW_POINTS[-1]) if EKW_POINTS[-1] else load_frac
    operating_frac = max(min(operating_frac, LOADS[-1]), 0.40)
    fuel_Btu_per_kWh = lin(operating_frac, LOADS, FUEL_ISO_BTU_KWH)
    fuel_Btu_per_hr = fuel_Btu_per_kWh * ekW
    fuel_scf_per_hr = fuel_Btu_per_hr / fuel_LHV_Btu_per_scf
    genset_efficiency = lin(operating_frac, LOADS, GENSET_EFF)
    nox_g_kwh = g_bhp_hr_to_g_kwh(lin(load_frac, LOADS, NOX_G_BHP_HR))
    co2_g_kwh = g_bhp_hr_to_g_kwh(lin(load_frac, LOADS, CO2_G_BHP_HR))
    nox_g_hr  = nox_g_kwh * ekW
    co2_g_hr  = co2_g_kwh * ekW
    nox_kg_hr = nox_g_hr / 1000.0
    co2_kg_hr = co2_g_hr / 1000.0
    return {
        'derate_factor': der,
        'site_ekW': ekW,
        'fuel_Btu_per_kWh': fuel_Btu_per_kWh,
        'fuel_Btu_per_hr': fuel_Btu_per_hr,
        'fuel_scf_per_hr': fuel_scf_per_hr,
        'NOx_g_per_kWh': nox_g_kwh,
        'NOx_kg_per_hr': nox_kg_hr,
        'CO2_g_per_kWh': co2_g_kwh,
        'CO2_kg_per_hr': co2_kg_hr,
        'GENSET_efficiency': genset_efficiency
    }

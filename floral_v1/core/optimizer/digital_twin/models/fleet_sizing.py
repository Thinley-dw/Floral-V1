from math import ceil, floor
from typing import Any, Dict, List, Tuple

from .g3520h_simple_derated import evaluate, derate_bilinear, EKW_POINTS

MIN_LOAD_FRAC = 0.40  # allow gensets down to 40% loading


def allocate_unit_loads(total_ekW: float, per_unit_max: float) -> Tuple[List[float], bool]:
    D = float(total_ekW)
    C = float(per_unit_max)
    if C <= 0:  return [], True
    if D <= 0:  return [], False
    K = int(D // C)
    R = D - K * C
    if R <= 1e-9:
        return [C] * K, False
    if K == 0:
        if R >= MIN_LOAD_FRAC * C:
            return [R], False
        else:
            return [], True
    if R >= MIN_LOAD_FRAC * C:
        return [C] * K + [R], False
    L = 0.5 * (R + C)
    return [C] * (K - 1) + [L, L], False

def size_and_calculate(
    total_ekW: float,
    ambient_C: float = 25.0,
    altitude_ft: float = 0.0,
    fuel_LHV_Btu_per_scf: float = 905.0,
) -> Dict[str, Any]:
    ambient_F = ambient_C * 9/5 + 32
    der = derate_bilinear(ambient_F, altitude_ft)
    rated_ekW = EKW_POINTS[-1]
    per_unit_max = der * rated_ekW
    if per_unit_max <= 0:
        raise ValueError("Deration produced zero available capacity per genset.")
    loads, infeasible = allocate_unit_loads(total_ekW, per_unit_max)
    if infeasible or not loads:
        return {"per_unit": [], "totals": {}, "per_unit_max_ekW": per_unit_max, "derate": der}

    units = []
    totals = {
        "gensets": len(loads),
        "site_ekW": 0.0,
        "fuel_Btu_per_hr": 0.0,
        "fuel_scf_per_hr": 0.0,
        "CO2_kg_per_hr": 0.0,
        "NOx_kg_per_hr": 0.0,
    }

    for L in loads:
        load_frac = max(0.5, min(1.0, L / rated_ekW))
        r = evaluate(load_frac, ambient_C=ambient_C, altitude_ft=altitude_ft,
                     fuel_LHV_Btu_per_scf=fuel_LHV_Btu_per_scf)
        if r["site_ekW"] > 0:
            scale = L / r["site_ekW"]
            r["site_ekW"]        *= scale
            r["fuel_Btu_per_hr"] *= scale
            r["fuel_scf_per_hr"] *= scale
            r["CO2_kg_per_hr"]   *= scale
            r["NOx_kg_per_hr"]   *= scale
        units.append(r)

    for r in units:
        totals["site_ekW"]        += r["site_ekW"]
        totals["fuel_Btu_per_hr"] += r["fuel_Btu_per_hr"]
        totals["fuel_scf_per_hr"] += r["fuel_scf_per_hr"]
        totals["CO2_kg_per_hr"]   += r["CO2_kg_per_hr"]
        totals["NOx_kg_per_hr"]   += r["NOx_kg_per_hr"]

    return {
        "per_unit_max_ekW": per_unit_max,
        "derate": der,
        "per_unit": units,
        "totals": totals
    }

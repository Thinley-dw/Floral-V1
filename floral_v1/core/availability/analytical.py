from __future__ import annotations

import math

from floral_v1.core.models import AvailabilityReport, HybridDesign
from floral_v1.core.sizing.engine import estimate_chp_availability, k_out_of_n_availability


def _load_mw(hybrid: HybridDesign) -> float:
    if hybrid.load_profile_kw:
        return max(hybrid.load_profile_kw) / 1000.0
    return hybrid.gensets.required_units * hybrid.gensets.per_unit_mw


def verify_availability(hybrid: HybridDesign) -> AvailabilityReport:
    """
    Analytical availability estimate leveraging the AvailabilityDesigner sizing logic.
    """
    load_mw = _load_mw(hybrid)
    per_unit = max(hybrid.gensets.per_unit_mw, 0.1)
    required_units = max(1, int(math.ceil(load_mw / per_unit)))
    engine_avail = estimate_chp_availability()
    genset_avail = k_out_of_n_availability(
        hybrid.gensets.installed_units,
        required_units,
        engine_avail,
    )

    bess_hours = hybrid.bess_energy_mwh / max(load_mw, 1e-6)
    bess_bonus = min(bess_hours * 0.01, 0.05)
    pv_ratio = hybrid.pv_capacity_kw / max(load_mw * 1000.0, 1e-6)
    pv_bonus = min(pv_ratio * 0.002, 0.03)

    achieved = min(0.9999, genset_avail + bess_bonus + pv_bonus)
    target = hybrid.gensets.expected_availability
    meets_target = achieved >= target
    details = {
        "genset_availability": genset_avail,
        "bess_bonus": bess_bonus,
        "pv_bonus": pv_bonus,
        "required_units": required_units,
        "load_mw": load_mw,
    }
    return AvailabilityReport(
        meets_target=meets_target,
        achieved=achieved,
        target=target,
        details=details,
    )

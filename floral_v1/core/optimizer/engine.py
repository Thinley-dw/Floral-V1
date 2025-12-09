from __future__ import annotations

from datetime import datetime
from typing import Dict, Sequence

from floral_v1.core.models import GensetDesign, HybridDesign, PlacementPlan, SiteModel
from floral_v1.core.optimizer import adapters
from floral_v1.logging_config import get_logger

logger = get_logger(__name__)


def optimize_hybrid(
    site: SiteModel,
    gensets: GensetDesign,
    placement: PlacementPlan,
    load_profile: Sequence[float],
    objectives: Dict[str, float] | None = None,
) -> HybridDesign:
    """
    Wrapper around the digital_twin optimizer that evaluates PV/BESS candidates.
    """
    logger.info(
        "Optimizing hybrid design for %s | objectives=%s",
        site.site.name,
        objectives,
    )
    try:
        objectives = objectives or {}
        base_pattern = list(load_profile) or [gensets.required_units * gensets.per_unit_mw * 1000.0]
        base_kw = gensets.required_units * gensets.per_unit_mw * 1000.0
        hours = adapters.DEFAULT_SIM_HOURS
        loads_kw = adapters.repeat_load_profile(base_pattern, hours, base_kw)
        timestamps = adapters.build_timestamps(datetime(2023, 1, 1), hours)
        pv_capacity_guess = adapters.derive_pv_capacity_kw(site, loads_kw)
        pv_levels = adapters.pv_candidates(pv_capacity_guess)
        cost_data = adapters.load_cost_data()

        best_candidate = None
        for pv_cap in pv_levels:
            pv_profile = adapters.synthesize_pv_profile(hours, pv_cap)
            for storage_hours in adapters.storage_candidates(pv_cap, pv_profile, loads_kw):
                candidate = adapters.evaluate_candidate(
                    site=site,
                    timestamps=timestamps,
                    loads_kw=loads_kw,
                    pv_profile_kw=pv_profile,
                    pv_capacity_kw=pv_cap,
                    storage_hours=storage_hours,
                    cost_data=cost_data,
                )
                if _is_better_candidate(candidate, best_candidate, objectives):
                    best_candidate = candidate

        if best_candidate is None:
            peak_kw = max(base_pattern)
            logger.warning("Optimizer fallback path activated for %s", site.site.name)
            return HybridDesign(
                gensets=gensets,
                site=site,
                placement=placement,
                pv_capacity_kw=0.0,
                bess_energy_mwh=0.0,
                bess_power_mw=peak_kw * 0.25 / 1000.0,
                load_profile_kw=list(base_pattern),
                metadata={"optimizer": "fallback"},
            )

        metadata = {
            "optimizer_lcoe": best_candidate["lcoe"],
            "storage_hours": best_candidate["storage_hours"],
            "sim_hours": hours,
            "unserved_kwh": best_candidate["unserved_kwh"],
        }
        design = HybridDesign(
            gensets=gensets,
            site=site,
            placement=placement,
            pv_capacity_kw=best_candidate["pv_capacity_kw"],
            bess_energy_mwh=best_candidate["bess_capacity_kwh"] / 1000.0,
            bess_power_mw=best_candidate["bess_power_kw"] / 1000.0,
            load_profile_kw=list(base_pattern),
            metadata=metadata,
        )
        logger.info(
            "Optimized hybrid design: pv_kw=%.1f bess_mwh=%.2f bess_mw=%.2f lcoe=%.4f",
            design.pv_capacity_kw,
            design.bess_energy_mwh,
            design.bess_power_mw,
            metadata["optimizer_lcoe"],
        )
        return design
    except Exception:
        logger.exception("Hybrid optimization failed for %s", site.site.name)
        raise


def _is_better_candidate(
    candidate: dict | None,
    current: dict | None,
    objectives: Dict[str, float],
) -> bool:
    if candidate is None:
        return False
    if current is None:
        return True

    prioritize_lcoe = bool(objectives.get("lcoe")) if objectives else True

    cand_lcoe = candidate.get("lcoe", float("inf"))
    curr_lcoe = current.get("lcoe", float("inf"))
    cand_unserved = candidate.get("unserved_kwh", float("inf"))
    curr_unserved = current.get("unserved_kwh", float("inf"))

    if prioritize_lcoe:
        cand_key = (cand_lcoe, cand_unserved)
        curr_key = (curr_lcoe, curr_unserved)
    else:
        cand_key = (cand_unserved, cand_lcoe)
        curr_key = (curr_unserved, curr_lcoe)
    return cand_key < curr_key

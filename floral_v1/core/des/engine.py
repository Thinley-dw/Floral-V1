from __future__ import annotations

from typing import Dict

from floral_v1.core.des import des_core, des_engine
from floral_v1.core.models import HybridDesign, SimulationConfig, SimulationResult
from floral_v1.logging_config import get_logger

logger = get_logger(__name__)


def _build_architecture_payload(hybrid: HybridDesign) -> Dict[str, float]:
    """Translate the hybrid design into the DES architecture dictionary."""
    gensets = hybrid.gensets
    load_profile = hybrid.load_profile_kw or []
    load_mw = max(load_profile) / 1000 if load_profile else gensets.required_units * gensets.per_unit_mw
    guaranteed_mw = gensets.required_units * gensets.per_unit_mw

    pv_total_mw = max(hybrid.pv_capacity_kw, 0.0) / 1000.0
    if pv_total_mw > 0:
        pv_blocks = max(1, int(round(pv_total_mw / 5.0)))
        pv_block_rating = pv_total_mw / pv_blocks
    else:
        pv_blocks = 0
        pv_block_rating = 0.0

    bess_power_mw = max(hybrid.bess_power_mw, 0.0)
    bess_energy_mwh = max(hybrid.bess_energy_mwh, 0.0)
    if bess_power_mw > 0:
        bess_pcs_units = max(1, int(round(bess_power_mw)))
    else:
        bess_pcs_units = 0
    if bess_energy_mwh > 0:
        bess_string_groups = max(1, int(round(bess_energy_mwh / 5.0)))
    else:
        bess_string_groups = 0

    return {
        "num_lines": int(max(1, gensets.installed_units)),
        "engine_rating_mw": max(gensets.per_unit_mw, 0.1),
        "guaranteed_mw": guaranteed_mw,
        "load_mw": load_mw,
        "pv_blocks": pv_blocks,
        "pv_block_rating_mw": pv_block_rating,
        "bess_power_mw": bess_power_mw,
        "bess_energy_mwh": bess_energy_mwh,
        "bess_pcs_units": bess_pcs_units,
        "bess_string_groups": bess_string_groups,
    }


def _resolve_mode(mode: str) -> str:
    lookup = {
        "stochastic": "random",
        "random": "random",
        "scheduled": "schedule",
        "schedule": "schedule",
        "hybrid": "hybrid",
    }
    return lookup.get((mode or "stochastic").lower(), "random")


def run_des(hybrid: HybridDesign, sim_config: SimulationConfig) -> SimulationResult:
    """Execute the SimPy DES using the migrated DESModel engine."""
    logger.info(
        "Running DES for %s | hours=%s seed=%s",
        hybrid.site.site.name,
        sim_config.hours,
        sim_config.seed,
    )
    try:
        hours = max(1, int(sim_config.hours or 0))
        arch_payload = _build_architecture_payload(hybrid)
        logger.debug("DES architecture payload: %s", arch_payload)
        des_core.configure_arch(arch_payload, sim_hours=hours)

        des_mode = _resolve_mode(getattr(sim_config, "mode", "stochastic"))
        schedule = getattr(sim_config, "schedule", None)
        des_engine.reset_simulation(
            seed=sim_config.seed,
            mode=des_mode,
            schedule=schedule,
        )
        if hours > 1:
            des_engine.fast_forward(hours - 1)

        history = des_engine.get_history() or []
        diagnostics = des_engine.compute_diagnostics(window_hours=hours)
        load_mw = arch_payload["load_mw"]
        energy_pv_mwh = 0.0
        energy_bess_mwh = 0.0
        energy_chp_mwh = 0.0
        energy_unserved_mwh = 0.0
        timeseries = {
            "hour": [],
            "load_mw": [],
            "served_mw": [],
            "pv_mw": [],
            "bess_mw": [],
            "chp_mw": [],
            "unserved_mw": [],
        }

        for idx, frame in enumerate(history):
            load = float(frame.get("load_mw", load_mw))
            served = float(frame.get("datacenter", {}).get("served_mw", load))
            pv_blocks = frame.get("pv", []) or []
            pv_gen = sum(float(block.get("mw", 0.0)) for block in pv_blocks)
            bess_dis = float(frame.get("bess", {}).get("discharge_mw", 0.0))
            chp_gen = max(served - pv_gen - bess_dis, 0.0)
            unserved = max(load - served, 0.0)

            energy_pv_mwh += pv_gen
            energy_bess_mwh += bess_dis
            energy_chp_mwh += chp_gen
            energy_unserved_mwh += unserved

            timeseries["hour"].append(idx)
            timeseries["load_mw"].append(load)
            timeseries["served_mw"].append(served)
            timeseries["pv_mw"].append(pv_gen)
            timeseries["bess_mw"].append(bess_dis)
            timeseries["chp_mw"].append(chp_gen)
            timeseries["unserved_mw"].append(unserved)

        unserved_mwh = energy_unserved_mwh

        availability = (
            diagnostics.get("overall", {}).get("availability_overall", 0.0)
            if diagnostics.get("ready", True)
            else 0.0
        )
        outage_hours = (
            diagnostics.get("overall", {}).get("hours_underpowered", 0.0)
            if diagnostics.get("ready", True)
            else 0.0
        )
        metadata = {
            "frames": len(history),
            "load_mw": load_mw,
            "sim_hours": hours,
            "des_mode": des_mode,
            "sim_seed": sim_config.seed if sim_config else None,
            "energy_chp_mwh": energy_chp_mwh,
            "energy_pv_mwh": energy_pv_mwh,
            "energy_bess_mwh": energy_bess_mwh,
            "energy_unserved_mwh": energy_unserved_mwh,
        }
        result = SimulationResult(
            availability=availability,
            outage_hours=outage_hours,
            unserved_energy_mwh=unserved_mwh,
            metadata=metadata,
            timeseries=timeseries,
        )
        logger.info(
            "DES result availability=%.4f outage_hours=%.2f unserved_mwh=%.2f",
            result.availability,
            result.outage_hours,
            result.unserved_energy_mwh,
        )
        return result
    except Exception:
        logger.exception("DES run failed for %s", hybrid.site.site.name)
        raise

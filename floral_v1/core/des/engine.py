from __future__ import annotations

from typing import Dict

from floral_v1.core.des import des_core, des_engine
from floral_v1.core.models import HybridDesign, SimulationConfig, SimulationResult


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


def run_des(hybrid: HybridDesign, sim_config: SimulationConfig) -> SimulationResult:
    """Execute the SimPy DES using the migrated DESModel engine."""
    hours = max(1, int(sim_config.hours or 0))
    arch_payload = _build_architecture_payload(hybrid)
    des_core.configure_arch(arch_payload, sim_hours=hours)

    des_engine.reset_simulation(seed=sim_config.seed, mode="random", schedule=None)
    if hours > 1:
        des_engine.fast_forward(hours - 1)

    history = des_engine.get_history() or []
    diagnostics = des_engine.compute_diagnostics(window_hours=hours)
    load_mw = arch_payload["load_mw"]
    unserved_mwh = 0.0
    for frame in history:
        served = frame.get("datacenter", {}).get("served_mw", load_mw)
        unserved_mwh += max(load_mw - float(served), 0.0)

    availability = diagnostics["overall"]["availability_overall"] if diagnostics.get("ready") else 0.0
    outage_hours = diagnostics["overall"]["hours_underpowered"] if diagnostics.get("ready") else 0.0
    metadata = {
        "frames": len(history),
        "load_mw": load_mw,
    }
    return SimulationResult(
        availability=availability,
        outage_hours=outage_hours,
        unserved_energy_mwh=unserved_mwh,
        metadata=metadata,
    )

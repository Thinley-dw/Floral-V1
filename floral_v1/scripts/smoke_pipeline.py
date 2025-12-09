from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Callable, Dict

from floral_v1.core.availability.analytical import verify_availability
from floral_v1.core.des.engine import run_des
from floral_v1.core.models import (
    AvailabilityReport,
    GensetDesign,
    HybridDesign,
    PlacementPlan,
    SimulationConfig,
    SimulationResult,
    SiteContext,
    SiteModel,
    UserRequest,
)
from floral_v1.core.optimizer.engine import optimize_hybrid
from floral_v1.core.sizing.engine import size_gensets
from floral_v1.core.site_plan.builder import build_site_model
from floral_v1.core.site_plan.placement import place_assets


def build_demo_request() -> UserRequest:
    site = SiteContext(name="Demo Site", latitude=1.3521, longitude=103.8198)
    load_profile = [45000.0] * 24
    return UserRequest(
        project_name="floral_v1_demo",
        target_load_mw=45.0,
        availability_target=0.999,
        site=site,
        load_profile_kw=load_profile,
        genset_size_mw=2.5,
        pv_land_m2=20000,
        objectives={"lcoe": 1.0},
    )


def build_reference_request_small() -> UserRequest:
    site = SiteContext(name="Small Campus", latitude=37.7749, longitude=-122.4194)
    load_profile = [3000.0] * 24
    return UserRequest(
        project_name="small_reference",
        target_load_mw=3.0,
        availability_target=0.995,
        site=site,
        load_profile_kw=load_profile,
        genset_size_mw=1.5,
        pv_land_m2=8000,
        objectives={"lcoe": 1.0},
    )


def build_reference_request_large() -> UserRequest:
    site = SiteContext(name="Large Campus", latitude=34.0522, longitude=-118.2437)
    load_profile = [10000.0] * 24
    return UserRequest(
        project_name="large_reference",
        target_load_mw=10.0,
        availability_target=0.9995,
        site=site,
        load_profile_kw=load_profile,
        genset_size_mw=3.0,
        pv_land_m2=120000,
        objectives={"lcoe": 1.0, "emissions": 0.2},
    )


def run_pipeline(request: UserRequest, sim_hours: int = 168) -> Dict[str, object]:
    gensets = size_gensets(request)
    site_model = build_site_model(request, gensets)
    placement = place_assets(site_model, gensets)
    hybrid = optimize_hybrid(
        site_model, gensets, placement, request.load_profile_kw, request.objectives
    )
    report = verify_availability(hybrid)
    des_config = SimulationConfig(hours=sim_hours, mode="stochastic")
    sim_result = run_des(hybrid, des_config)
    return {
        "request": request,
        "gensets": gensets,
        "site_model": site_model,
        "placement": placement,
        "hybrid": hybrid,
        "availability": report,
        "simulation": sim_result,
        "des_config": des_config,
    }


def summarize_outputs(label: str, outputs: Dict[str, object]) -> None:
    gensets: GensetDesign = outputs["gensets"]  # type: ignore[assignment]
    site_model: SiteModel = outputs["site_model"]  # type: ignore[assignment]
    hybrid: HybridDesign = outputs["hybrid"]  # type: ignore[assignment]
    report: AvailabilityReport = outputs["availability"]  # type: ignore[assignment]
    sim_result: SimulationResult = outputs["simulation"]  # type: ignore[assignment]

    print(f"=== Floral V1 Reference Scenario: {label} ===")
    print("-- Genset Sizing --")
    print(
        f"required={gensets.required_units} installed={gensets.installed_units} "
        f"per_unit_mw={gensets.per_unit_mw:.2f} expected_avail={gensets.expected_availability:.4f}"
    )
    print("-- Site --")
    print(
        f"footprint_acres={site_model.footprint_acres:.2f} buildable_acres={site_model.buildable_area_acres:.2f}"
    )
    print("-- Hybrid Design --")
    print(
        f"pv_capacity_kw={hybrid.pv_capacity_kw:.1f} bess_energy_mwh={hybrid.bess_energy_mwh:.2f} "
        f"bess_power_mw={hybrid.bess_power_mw:.2f}"
    )
    print("-- Availability --")
    print(
        f"analytical={report.achieved:.4f} target={report.target:.4f} meets_target={report.meets_target}"
    )
    print("-- DES --")
    print(
        f"availability={sim_result.availability:.4f} outage_hours={sim_result.outage_hours:.2f} "
        f"unserved_energy_mwh={sim_result.unserved_energy_mwh:.2f}"
    )


@dataclass(frozen=True)
class ScenarioDefinition:
    builder: Callable[[], UserRequest]
    hours: int


SCENARIOS: Dict[str, ScenarioDefinition] = {
    "demo": ScenarioDefinition(build_demo_request, 168),
    "small": ScenarioDefinition(build_reference_request_small, 72),
    "large": ScenarioDefinition(build_reference_request_large, 168),
}


def run_named_scenario(name: str, summarize: bool = True) -> Dict[str, object]:
    key = name.lower()
    definition = SCENARIOS.get(key)
    if not definition:
        raise KeyError(f"Unknown scenario '{name}'")
    request = definition.builder()
    outputs = run_pipeline(request, sim_hours=definition.hours)
    if summarize:
        summarize_outputs(key, outputs)
    return outputs


def main(argv: list[str] | None = None) -> None:
    args = argv if argv is not None else sys.argv[1:]
    scenario = args[0].lower() if args else "demo"
    if scenario not in SCENARIOS:
        print(f"Unknown scenario '{scenario}'. Available: {', '.join(SCENARIOS)}")
        scenario = "demo"
    run_named_scenario(scenario)


if __name__ == "__main__":
    main()

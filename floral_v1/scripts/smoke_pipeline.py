from __future__ import annotations

from floral_v1.core.availability.analytical import verify_availability
from floral_v1.core.des.engine import run_des
from floral_v1.core.models import (
    SimulationConfig,
    SiteContext,
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
        project_name="floral_v1_smoke",
        target_load_mw=45.0,
        availability_target=0.999,
        site=site,
        load_profile_kw=load_profile,
        genset_size_mw=2.5,
        pv_land_m2=20000,
        objectives={"lcoe": 1.0},
    )


def main() -> None:
    request = build_demo_request()
    gensets = size_gensets(request)
    site_model = build_site_model(request, gensets)
    placement = place_assets(site_model, gensets)
    hybrid = optimize_hybrid(
        site_model, gensets, placement, request.load_profile_kw, request.objectives
    )
    report = verify_availability(hybrid)
    sim_result = run_des(hybrid, SimulationConfig(hours=168))
    print("=== Floral V1 Smoke Test ===")
    print(f"Gensets installed: {gensets.installed_units}")
    print(f"Site footprint (acres): {site_model.footprint_acres}")
    print(f"Availability check: {report.achieved:.4f} (target {report.target:.4f})")
    print(f"DES availability: {sim_result.availability:.4f}")
    print(f"DES outage hours: {sim_result.outage_hours:.2f}")


if __name__ == "__main__":
    main()

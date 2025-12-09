from __future__ import annotations

import math

from floral_v1.core.des.engine import run_des
from floral_v1.core.models import Heightmap, PlacementPlan, SimulationConfig, SiteModel
from floral_v1.core.optimizer.engine import optimize_hybrid
from floral_v1.core.sizing.engine import size_gensets


def _site_model(site_context) -> SiteModel:
    heightmap = Heightmap(grid=[[0.0, 0.0], [0.1, 0.2]], resolution_m=20.0, source="test")
    return SiteModel(
        site=site_context,
        heightmap=heightmap,
        footprint_acres=30.0,
        buildable_area_acres=15.0,
        metadata={"fixture": "test"},
    )


def _placement(site_model: SiteModel, genset_count: int) -> PlacementPlan:
    assets = {
        "genset_pad": {"x_m": 5.0, "y_m": 5.0, "type": "genset"},
        "bess_block": {"x_m": 15.0, "y_m": 10.0, "type": "bess"},
    }
    constraints = {"genset_count": float(genset_count)}
    return PlacementPlan(site=site_model, asset_locations=assets, constraints=constraints)


def _build_hybrid(request):
    gensets = size_gensets(request)
    site_model = _site_model(request.site)
    placement = _placement(site_model, gensets.installed_units)
    hybrid = optimize_hybrid(
        site_model,
        gensets,
        placement,
        request.load_profile_kw,
        request.objectives,
    )
    return hybrid


def test_run_des_returns_finite_metrics(demo_request):
    hybrid = _build_hybrid(demo_request)
    config = SimulationConfig(hours=24)
    result = run_des(hybrid, config)

    assert 0.0 <= result.availability <= 1.0
    assert result.outage_hours >= 0.0
    assert result.unserved_energy_mwh >= 0.0
    for value in (result.availability, result.outage_hours, result.unserved_energy_mwh):
        assert math.isfinite(value)

    for key in (
        "energy_chp_mwh",
        "energy_pv_mwh",
        "energy_bess_mwh",
        "energy_unserved_mwh",
    ):
        assert key in result.metadata
        assert result.metadata[key] >= 0.0

    assert result.timeseries
    assert len(result.timeseries.get("hour", [])) == len(result.timeseries.get("served_mw", []))

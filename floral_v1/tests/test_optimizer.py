from __future__ import annotations

from floral_v1.core.models import Heightmap, PlacementPlan, SiteModel
from floral_v1.core.optimizer.engine import optimize_hybrid
from floral_v1.core.sizing.engine import size_gensets


def _make_site_model(site_context) -> SiteModel:
    heightmap = Heightmap(grid=[[0.0, 0.1], [0.2, 0.0]], resolution_m=10.0, source="test")
    return SiteModel(
        site=site_context,
        heightmap=heightmap,
        footprint_acres=20.0,
        buildable_area_acres=10.0,
        metadata={"source": "unit-test"},
    )


def _make_placement(site_model: SiteModel, genset_count: int) -> PlacementPlan:
    asset_locations = {
        "genset_pad": {"x_m": 0.0, "y_m": 0.0, "type": "genset"},
        "pv_field": {"x_m": 50.0, "y_m": 10.0, "type": "pv"},
    }
    constraints = {"genset_count": float(genset_count)}
    return PlacementPlan(site=site_model, asset_locations=asset_locations, constraints=constraints)


def test_optimize_hybrid_produces_non_negative_capacities(demo_request):
    gensets = size_gensets(demo_request)
    site_model = _make_site_model(demo_request.site)
    placement = _make_placement(site_model, gensets.installed_units)

    hybrid = optimize_hybrid(
        site_model,
        gensets,
        placement,
        demo_request.load_profile_kw,
        demo_request.objectives,
    )

    assert hybrid.gensets.installed_units == gensets.installed_units
    assert hybrid.site.site.name == site_model.site.name
    assert hybrid.pv_capacity_kw >= 0.0
    assert hybrid.bess_energy_mwh >= 0.0
    assert hybrid.bess_power_mw >= 0.0

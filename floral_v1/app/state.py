from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Optional

from floral_v1.core.models import (
    AvailabilityReport,
    GensetDesign,
    Heightmap,
    HybridDesign,
    PlacementPlan,
    SimulationConfig,
    SimulationResult,
    SiteContext,
    SiteModel,
    UserRequest,
)


def _maybe_number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def serialize_dataclass(instance: Any) -> Dict[str, Any]:
    return asdict(instance)


def site_context_from_store(data: Dict[str, Any]) -> SiteContext:
    return SiteContext(
        name=data.get("name", "Site"),
        latitude=_maybe_number(data.get("latitude"), 0.0),
        longitude=_maybe_number(data.get("longitude"), 0.0),
        altitude_m=_maybe_number(data.get("altitude_m"), 0.0),
        boundary_file=data.get("boundary_file"),
        notes=data.get("notes", ""),
        boundary_geojson=data.get("boundary_geojson"),
        entrance_geojson=data.get("entrance_geojson"),
        gas_line_geojson=data.get("gas_line_geojson"),
    )


def heightmap_from_store(data: Optional[Dict[str, Any]]) -> Optional[Heightmap]:
    if not data:
        return None
    return Heightmap(
        grid=data.get("grid", []),
        resolution_m=_maybe_number(data.get("resolution_m"), 0.0),
        source=data.get("source", "synthetic"),
    )


def user_request_from_store(data: Dict[str, Any]) -> UserRequest:
    site = site_context_from_store(data.get("site", {}))
    return UserRequest(
        project_name=data.get("project_name", "demo"),
        target_load_mw=_maybe_number(data.get("target_load_mw"), 10.0),
        availability_target=_maybe_number(data.get("availability_target"), 0.99),
        site=site,
        load_profile_kw=list(data.get("load_profile_kw", [])),
        genset_size_mw=_maybe_number(data.get("genset_size_mw"), 2.5),
        ambient_c=_maybe_number(data.get("ambient_c"), 25.0),
        altitude_ft=_maybe_number(data.get("altitude_ft"), 0.0),
        pv_land_m2=_maybe_number(data.get("pv_land_m2"), 0.0),
        objectives=dict(data.get("objectives", {})),
    )


def genset_design_from_store(data: Dict[str, Any]) -> GensetDesign:
    return GensetDesign(
        required_units=int(data.get("required_units", 0)),
        installed_units=int(data.get("installed_units", 0)),
        per_unit_mw=_maybe_number(data.get("per_unit_mw"), 0.0),
        expected_availability=_maybe_number(data.get("expected_availability"), 0.0),
        notes=data.get("notes", ""),
    )


def site_model_from_store(data: Dict[str, Any]) -> SiteModel:
    return SiteModel(
        site=site_context_from_store(data.get("site", {})),
        heightmap=heightmap_from_store(data.get("heightmap")),
        footprint_acres=_maybe_number(data.get("footprint_acres"), 0.0),
        buildable_area_acres=_maybe_number(data.get("buildable_area_acres"), 0.0),
        metadata=dict(data.get("metadata", {})),
    )


def placement_plan_from_store(data: Dict[str, Any]) -> PlacementPlan:
    return PlacementPlan(
        site=site_model_from_store(data.get("site", {})),
        asset_locations=dict(data.get("asset_locations", {})),
        constraints=dict(data.get("constraints", {})),
    )


def hybrid_design_from_store(data: Dict[str, Any]) -> HybridDesign:
    return HybridDesign(
        gensets=genset_design_from_store(data.get("gensets", {})),
        site=site_model_from_store(data.get("site", {})),
        placement=placement_plan_from_store(data.get("placement", {})),
        pv_capacity_kw=_maybe_number(data.get("pv_capacity_kw"), 0.0),
        bess_energy_mwh=_maybe_number(data.get("bess_energy_mwh"), 0.0),
        bess_power_mw=_maybe_number(data.get("bess_power_mw"), 0.0),
        load_profile_kw=list(data.get("load_profile_kw", [])),
        metadata=dict(data.get("metadata", {})),
    )


def availability_report_from_store(data: Dict[str, Any]) -> AvailabilityReport:
    return AvailabilityReport(
        meets_target=bool(data.get("meets_target", False)),
        achieved=_maybe_number(data.get("achieved"), 0.0),
        target=_maybe_number(data.get("target"), 0.0),
        details=dict(data.get("details", {})),
    )


def simulation_result_from_store(data: Dict[str, Any]) -> SimulationResult:
    return SimulationResult(
        availability=_maybe_number(data.get("availability"), 0.0),
        outage_hours=_maybe_number(data.get("outage_hours"), 0.0),
        unserved_energy_mwh=_maybe_number(data.get("unserved_energy_mwh"), 0.0),
        metadata=dict(data.get("metadata", {})),
        timeseries=dict(data.get("timeseries", {})),
    )


def simulation_config_from_inputs(hours: Any, seed: Any = None) -> SimulationConfig:
    return SimulationConfig(hours=int(hours or 0), seed=seed)

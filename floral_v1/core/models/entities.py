from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class SiteContext:
    """High level site metadata used by every stage of the pipeline."""

    name: str
    latitude: float
    longitude: float
    altitude_m: float = 0.0
    boundary_file: Optional[str] = None
    notes: str = ""


@dataclass
class UserRequest:
    """Top level request that drives the integrated workflow."""

    project_name: str
    target_load_mw: float
    availability_target: float
    site: SiteContext
    load_profile_kw: List[float]
    genset_size_mw: float = 2.5
    ambient_c: float = 25.0
    altitude_ft: float = 0.0
    pv_land_m2: float = 0.0
    objectives: Dict[str, float] = field(default_factory=dict)


@dataclass
class Heightmap:
    """Minimal representation of a sampled heightmap."""

    grid: List[List[float]]
    resolution_m: float
    source: str = "synthetic"


@dataclass
class SiteModel:
    """Normalized site model that includes boundaries, topography, and metadata."""

    site: SiteContext
    heightmap: Optional[Heightmap]
    footprint_acres: float
    buildable_area_acres: float
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class GensetDesign:
    """Sizing output produced by the availability designer."""

    required_units: int
    installed_units: int
    per_unit_mw: float
    expected_availability: float
    notes: str = ""


@dataclass
class PlacementPlan:
    """Structured output from the site planning layer."""

    site: SiteModel
    asset_locations: Dict[str, Dict[str, float]]
    constraints: Dict[str, float] = field(default_factory=dict)


@dataclass
class HybridDesign:
    """Defines the optimized mix of gensets, PV, and BESS."""

    gensets: GensetDesign
    site: SiteModel
    placement: PlacementPlan
    pv_capacity_kw: float
    bess_energy_mwh: float
    bess_power_mw: float
    load_profile_kw: List[float]
    metadata: Dict[str, float] = field(default_factory=dict)


@dataclass
class AvailabilityReport:
    """Analytical availability validation prior to DES."""

    meets_target: bool
    achieved: float
    target: float
    details: Dict[str, float] = field(default_factory=dict)


@dataclass
class SimulationConfig:
    """Discrete event simulation configuration."""

    hours: int = 168
    seed: Optional[int] = None


@dataclass
class SimulationResult:
    """Aggregated DES output consumed by downstream tooling."""

    availability: float
    outage_hours: float
    unserved_energy_mwh: float
    metadata: Dict[str, float] = field(default_factory=dict)


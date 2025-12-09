from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional

from shapely import wkt
from shapely.geometry import Polygon

from floral_v1.core.models import GensetDesign, SiteModel, UserRequest
from floral_v1.core.site_plan import opentopo_client

SITEPLAN_ROOT = Path(__file__).resolve().parents[3] / "siteplan-visuals"
SITE_PLAN_PATH = SITEPLAN_ROOT / "site_plan.json"
BOUNDARY_PATH = SITEPLAN_ROOT / "boundary.geojson"
M2_PER_ACRE = 4046.8564224


def _load_site_plan() -> Optional[dict]:
    if SITE_PLAN_PATH.exists():
        try:
            return json.loads(SITE_PLAN_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
    return None


def _load_boundary_polygon(plan: Optional[dict]) -> Polygon:
    if plan and plan.get("site_boundary"):
        try:
            return wkt.loads(plan["site_boundary"])
        except Exception:
            pass
    if BOUNDARY_PATH.exists():
        try:
            data = json.loads(BOUNDARY_PATH.read_text(encoding="utf-8"))
            coords = data["features"][0]["geometry"]["coordinates"][0]
            return Polygon(coords)
        except Exception:
            pass
    # fallback simple square of 10 acres
    return Polygon([(0, 0), (100, 0), (100, 100), (0, 100)])


def build_site_model(request: UserRequest, gensets: GensetDesign) -> SiteModel:
    """
    Build a SiteModel by parsing the legacy siteplan JSON and sampling OpenTopo heightmaps.
    """
    plan_data = _load_site_plan()
    boundary = _load_boundary_polygon(plan_data)
    footprint_acres = max(boundary.area / M2_PER_ACRE, 0.1)
    buildable_area = footprint_acres * 0.8

    bounds: Dict[str, float] = {
        "lat": request.site.latitude,
        "lon": request.site.longitude,
        "size_km": max((boundary.area**0.5) / 1000.0, 0.5),
    }
    heightmap = opentopo_client.fetch_heightmap(bounds)

    metadata = {
        "gensets_required": str(gensets.required_units),
        "gensets_installed": str(gensets.installed_units),
        "grid_angle": plan_data.get("grid_angle") if plan_data else None,
        "site_plan_path": str(SITE_PLAN_PATH) if SITE_PLAN_PATH.exists() else "",
        "site_crs": plan_data.get("site_crs") if plan_data else "",
    }
    return SiteModel(
        site=request.site,
        heightmap=heightmap,
        footprint_acres=footprint_acres,
        buildable_area_acres=buildable_area,
        metadata=metadata,
    )

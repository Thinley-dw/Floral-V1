from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional

from shapely import wkt
from shapely.geometry import Polygon

from floral_v1.core.models import GensetDesign, SiteModel, UserRequest
from floral_v1.core.site_plan import opentopo_client
from floral_v1.logging_config import get_logger

DATA_ROOT = Path(__file__).resolve().parent / "data"
SITE_PLAN_PATH = DATA_ROOT / "site_plan.json"
BOUNDARY_PATH = DATA_ROOT / "boundary.geojson"
M2_PER_ACRE = 4046.8564224
logger = get_logger(__name__)


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
    logger.info(
        "Building site model for %s | lat=%.4f lon=%.4f",
        request.site.name,
        request.site.latitude,
        request.site.longitude,
    )
    try:
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
        site_model = SiteModel(
            site=request.site,
            heightmap=heightmap,
            footprint_acres=footprint_acres,
            buildable_area_acres=buildable_area,
            metadata=metadata,
        )
        logger.info(
            "Built site model: footprint=%.2f acres buildable=%.2f acres",
            site_model.footprint_acres,
            site_model.buildable_area_acres,
        )
        return site_model
    except Exception:
        logger.exception("Failed to build site model for %s", request.site.name)
        raise

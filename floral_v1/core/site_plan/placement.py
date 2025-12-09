from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional

from shapely import wkt

from floral_v1.core.models import GensetDesign, PlacementPlan, SiteModel
from floral_v1.logging_config import get_logger

DATA_ROOT = Path(__file__).resolve().parent / "data"
SITE_PLAN_PATH = DATA_ROOT / "site_plan.json"
logger = get_logger(__name__)


def _load_site_plan(path: str | None) -> Optional[dict]:
    candidate = Path(path) if path else SITE_PLAN_PATH
    if candidate.exists():
        try:
            return json.loads(candidate.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
    return None


def place_assets(site_model: SiteModel, gensets: GensetDesign) -> PlacementPlan:
    """
    Parse the legacy site_plan JSON and translate assets into a PlacementPlan.
    """
    logger.info(
        "Placing assets for %s | gensets=%d",
        site_model.site.name,
        gensets.installed_units,
    )
    try:
        plan = _load_site_plan(site_model.metadata.get("site_plan_path") if site_model.metadata else None)
        asset_locations: Dict[str, Dict[str, float]] = {}
        constraints = {
            "genset_count": float(gensets.installed_units),
            "grid_angle": plan.get("grid_angle") if plan else None,
        }
        if plan:
            for asset in plan.get("assets", []):
                try:
                    centroid = wkt.loads(asset.get("centroid") or asset.get("geometry"))
                except Exception:
                    logger.debug("Skipping asset with invalid geometry: %s", asset.get("name"))
                    continue
                asset_locations[asset["name"]] = {
                    "type": asset.get("type", "asset"),
                    "x_m": centroid.x,
                    "y_m": centroid.y,
                    "angle_deg": asset.get("angle_deg", 0.0),
                    "obj_file": asset.get("obj_file"),
                }
            pv_panels = sum(1 for a in plan.get("assets", []) if "PV Panel" in a.get("name", ""))
            constraints["pv_panels"] = pv_panels
        if not asset_locations:
            asset_locations = {
                "genset_block": {"x_m": 0.0, "y_m": 0.0, "type": "genset"},
                "bess_block": {"x_m": 20.0, "y_m": 10.0, "type": "bess"},
            }
        placement = PlacementPlan(site=site_model, asset_locations=asset_locations, constraints=constraints)
        logger.info("Placed %d assets", len(asset_locations))
        return placement
    except Exception:
        logger.exception("Failed to place assets for %s", site_model.site.name)
        raise

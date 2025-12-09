from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional, Tuple

from pyproj import Geod
from shapely import wkt
from shapely.geometry import Polygon, shape

from floral_v1.core.models import GensetDesign, SiteContext, SiteModel, UserRequest
from floral_v1.core.site_plan import opentopo_client
from floral_v1.logging_config import get_logger

DATA_ROOT = Path(__file__).resolve().parent / "data"
SITE_PLAN_PATH = DATA_ROOT / "site_plan.json"
BOUNDARY_PATH = DATA_ROOT / "boundary.geojson"
M2_PER_ACRE = 4046.8564224
GEOD = Geod(ellps="WGS84")
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
    boundary_feature = request.site.boundary_geojson
    entrance_feature = request.site.entrance_geojson
    gas_feature = request.site.gas_line_geojson
    user_boundary = _polygon_from_geojson(boundary_feature)

    plan_data = None if user_boundary else _load_site_plan()
    boundary = user_boundary or _load_boundary_polygon(plan_data)
    site_ctx = _normalize_site_context(request.site, boundary)

    logger.info(
        "Building site model for %s | lat=%.4f lon=%.4f",
        site_ctx.name,
        site_ctx.latitude,
        site_ctx.longitude,
    )
    try:
        if user_boundary:
            area_m2 = max(_polygon_area_m2(user_boundary), 1.0)
            footprint_acres = max(area_m2 / M2_PER_ACRE, 0.1)
        else:
            footprint_acres = max(boundary.area / M2_PER_ACRE, 0.1)
        buildable_area = footprint_acres * 0.8

        bounds: Dict[str, float] = {
            "lat": site_ctx.latitude,
            "lon": site_ctx.longitude,
            "size_km": _estimate_capture_size_km(boundary, user_boundary),
        }
        heightmap = opentopo_client.fetch_heightmap(bounds)

        metadata = {
            "gensets_required": str(gensets.required_units),
            "gensets_installed": str(gensets.installed_units),
            "grid_angle": plan_data.get("grid_angle") if plan_data else None,
            "site_plan_path": str(SITE_PLAN_PATH) if SITE_PLAN_PATH.exists() else "",
            "site_crs": plan_data.get("site_crs") if plan_data else "",
            "boundary_geojson": boundary_feature,
            "entrance_geojson": entrance_feature,
            "gas_line_geojson": gas_feature,
            "geometry_source": "user" if user_boundary else "legacy",
            "site_notes": site_ctx.notes,
            "ambient_c": request.ambient_c,
        }
        site_model = SiteModel(
            site=site_ctx,
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


def _polygon_from_geojson(feature: Optional[dict]) -> Optional[Polygon]:
    if not feature:
        return None
    geometry = feature.get("geometry") if "geometry" in feature else feature
    if not geometry:
        return None
    try:
        geom = shape(geometry)
        if geom.geom_type == "Polygon":
            return geom
        if geom.geom_type == "MultiPolygon" and getattr(geom, "geoms", None):
            return max(geom.geoms, key=lambda g: g.area)
    except Exception:
        logger.debug("Invalid boundary geometry received from inputs")
    return None


def _polygon_area_m2(polygon: Polygon) -> float:
    if polygon.is_empty:
        return 0.0
    lon, lat = polygon.exterior.coords.xy
    area, _ = GEOD.polygon_area_perimeter(lon, lat)
    return abs(area)


def _estimate_capture_size_km(boundary: Polygon, user_boundary: Optional[Polygon]) -> float:
    if user_boundary:
        area_m2 = max(_polygon_area_m2(user_boundary), 1.0)
        side_km = (area_m2 ** 0.5) / 1000.0
        return max(side_km, 0.5)
    return max((boundary.area ** 0.5) / 1000.0, 0.5)


def _normalize_site_context(site: SiteContext, boundary: Polygon) -> SiteContext:
    lat = site.latitude
    lon = site.longitude
    if (abs(lat) < 1e-6 or abs(lon) < 1e-6) and boundary:
        centroid = boundary.centroid
        if centroid:
            lon = centroid.x
            lat = centroid.y
    return SiteContext(
        name=site.name,
        latitude=lat,
        longitude=lon,
        altitude_m=site.altitude_m,
        boundary_file=site.boundary_file,
        notes=site.notes,
        boundary_geojson=site.boundary_geojson,
        entrance_geojson=site.entrance_geojson,
        gas_line_geojson=site.gas_line_geojson,
    )

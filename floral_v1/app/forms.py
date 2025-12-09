from __future__ import annotations

from typing import Any, Dict, List, Optional

from shapely.geometry import shape

from floral_v1.core.models import SiteContext, UserRequest


def parse_load_profile(text: str) -> List[float]:
    if not text:
        return []
    values: List[float] = []
    for chunk in text.replace("\n", ",").split(","):
        piece = chunk.strip()
        if not piece:
            continue
        try:
            values.append(float(piece))
        except ValueError:
            continue
    return values


def build_objectives(mode: Optional[str], weight: Optional[float]) -> Dict[str, float]:
    mode_key = (mode or "lcoe").lower()
    if mode_key == "emissions":
        return {"emissions": 1.0}
    if mode_key == "weighted":
        w = float(weight if weight is not None else 0.5)
        w = max(0.0, min(1.0, w))
        return {"lcoe": w, "emissions": max(0.0, 1.0 - w)}
    return {"lcoe": 1.0}


def build_user_request(
    project_name: Optional[str],
    site_name: Optional[str],
    target_load_mw: Optional[float],
    availability_target: Optional[float],
    genset_size_mw: Optional[float],
    latitude: Optional[float],
    longitude: Optional[float],
    altitude_m: Optional[float],
    ambient_c: Optional[float],
    pv_land_m2: Optional[float],
    load_profile_text: str,
    site_notes: Optional[str],
    objective_mode: Optional[str],
    objective_weight: Optional[float],
    geometry: Optional[Dict[str, Any]],
) -> UserRequest:
    load_profile = parse_load_profile(load_profile_text)
    if not load_profile:
        raise ValueError("Load profile must contain numeric values.")

    boundary_feature = _clean_feature((geometry or {}).get("boundary"))
    entrance_feature = _clean_feature((geometry or {}).get("entrance"))
    gas_feature = _clean_feature((geometry or {}).get("gas_line"))

    lat = _to_float(latitude, 0.0)
    lon = _to_float(longitude, 0.0)
    if (abs(lat) < 1e-6 or abs(lon) < 1e-6) and boundary_feature:
        try:
            geom = boundary_feature.get("geometry") or boundary_feature
            centroid = shape(geom).centroid
            lon = centroid.x
            lat = centroid.y
        except Exception:
            pass

    site_context = SiteContext(
        name=(site_name or project_name or "Site"),
        latitude=lat,
        longitude=lon,
        altitude_m=_to_float(altitude_m, 0.0),
        notes=site_notes or "",
        boundary_geojson=boundary_feature,
        entrance_geojson=entrance_feature,
        gas_line_geojson=gas_feature,
    )

    objectives = build_objectives(objective_mode, objective_weight)
    return UserRequest(
        project_name=project_name or "floral_v1_project",
        target_load_mw=_to_float(target_load_mw, 0.0),
        availability_target=_to_float(availability_target, 0.0),
        site=site_context,
        load_profile_kw=load_profile,
        genset_size_mw=_to_float(genset_size_mw, 2.5),
        ambient_c=_to_float(ambient_c, 25.0),
        pv_land_m2=_to_float(pv_land_m2, 0.0),
        objectives=objectives,
    )


def _clean_feature(feature: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not feature:
        return None
    if feature.get("type") == "Feature":
        return feature
    if "geometry" in feature:
        return {"type": "Feature", "geometry": feature["geometry"]}
    if feature.get("type") in {"Polygon", "LineString", "Point"}:
        return {"type": "Feature", "geometry": feature}
    return None


def _to_float(value: Optional[float], default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

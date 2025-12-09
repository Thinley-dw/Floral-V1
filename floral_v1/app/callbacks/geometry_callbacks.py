from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, Dict, List, Optional

from dash import Input, Output, State
from dash.exceptions import PreventUpdate

from floral_v1.app.feature_flags import HAS_DASH_LEAFLET

DEFAULT_GEOMETRY = {"boundary": None, "entrance": None, "gas_line": None}


def register(app):
    if HAS_DASH_LEAFLET:
        _register_map_callbacks(app)
    else:
        _register_fallback_callbacks(app)


def _register_map_callbacks(app):
    @app.callback(
        Output("site-geometry-store", "data"),
        Output("site-geometry-preview", "data"),
        Input("geometry-draw-control", "last_draw"),
        Input("geometry-draw-control", "last_edit"),
        Input("geometry-draw-control", "last_delete"),
        State("site-geometry-store", "data"),
        prevent_initial_call=True,
    )
    def update_geometry(last_draw, last_edit, last_delete, current):
        data = deepcopy(current) if current else deepcopy(DEFAULT_GEOMETRY)
        updated = False
        for payload, mode in (
            (last_draw, "draw"),
            (last_edit, "edit"),
            (last_delete, "delete"),
        ):
            if not payload:
                continue
            updated = True
            data = _apply_features(data, payload, mode)
        if not updated:
            raise PreventUpdate
        preview = _feature_collection(data)
        return data, preview


def _register_fallback_callbacks(app):
    @app.callback(
        Output("site-geometry-store", "data"),
        Output("site-geometry-preview", "children"),
        Input("geometry-json-button", "n_clicks"),
        State("geometry-json-input", "value"),
        State("site-geometry-store", "data"),
        prevent_initial_call=True,
    )
    def load_geometry_from_json(n_clicks, text, current):
        if not n_clicks:
            raise PreventUpdate
        data = deepcopy(current) if current else deepcopy(DEFAULT_GEOMETRY)
        if not text:
            raise PreventUpdate
        try:
            parsed = _parse_manual_geojson(text)
        except ValueError as exc:
            raise PreventUpdate from exc
        data.update(parsed)
        preview = json.dumps(_feature_collection(data), indent=2)
        return data, preview



def _apply_features(store: Dict[str, Any], payload: Dict[str, Any], mode: str) -> Dict[str, Any]:
    for feature in _feature_list(payload):
        geom_type = (feature.get("geometry") or {}).get("type")
        if geom_type == "Polygon":
            store["boundary"] = None if mode == "delete" else feature
        elif geom_type == "Point":
            store["entrance"] = None if mode == "delete" else feature
        elif geom_type == "LineString":
            store["gas_line"] = None if mode == "delete" else feature
    return store


def _feature_list(payload: Any) -> List[Dict[str, Any]]:
    if not payload:
        return []
    if isinstance(payload, dict) and payload.get("type") == "FeatureCollection":
        return [feat for feat in payload.get("features", []) if isinstance(feat, dict)]
    if isinstance(payload, dict):
        return [payload]
    if isinstance(payload, list):
        return [feat for feat in payload if isinstance(feat, dict)]
    return []


def _feature_collection(store: Dict[str, Any]) -> Dict[str, Any]:
    features = [feat for feat in (store.get("boundary"), store.get("entrance"), store.get("gas_line")) if feat]
    return {"type": "FeatureCollection", "features": features}


def _parse_manual_geojson(text: str) -> Dict[str, Any]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("Invalid JSON provided for site geometry.") from exc
    result: Dict[str, Any] = {}
    for key in ("boundary", "entrance", "gas_line"):
        feature = _clean_feature(payload.get(key))
        if feature:
            result[key] = feature
    if not result:
        raise ValueError("No valid boundary, entrance, or gas_line geometry found.")
    return result


def _clean_feature(value: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not value:
        return None
    if value.get("type") == "Feature":
        return value
    if "geometry" in value and isinstance(value["geometry"], dict):
        return {"type": "Feature", "geometry": value["geometry"]}
    if value.get("type") in {"Polygon", "LineString", "Point"}:
        return {"type": "Feature", "geometry": value}
    return None

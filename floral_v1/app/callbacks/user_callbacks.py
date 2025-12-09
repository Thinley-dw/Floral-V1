from __future__ import annotations

import json
from typing import List

from dash import Input, Output, State
from dash.exceptions import PreventUpdate

from floral_v1.app.state import serialize_dataclass, user_request_from_store
from floral_v1.core.models import SiteContext, UserRequest
from floral_v1.core.visualization import load_profile_figure


def parse_load_profile(text: str) -> List[float]:
    if not text:
        return []
    values: List[float] = []
    for chunk in text.replace("\n", ",").split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            values.append(float(chunk))
        except ValueError:
            continue
    return values


def register(app):
    @app.callback(
        Output("user-request-store", "data"),
        Output("request-status", "children"),
        Input("save-request-button", "n_clicks"),
        State("project-name-input", "value"),
        State("target-load-input", "value"),
        State("availability-target-input", "value"),
        State("genset-size-input", "value"),
        State("latitude-input", "value"),
        State("longitude-input", "value"),
        State("altitude-input", "value"),
        State("pv-land-input", "value"),
        State("load-profile-input", "value"),
        State("objective-lcoe-input", "value"),
        State("objective-emissions-input", "value"),
    )
    def save_request(
        n_clicks,
        project_name,
        target_load,
        availability_target,
        genset_size,
        latitude,
        longitude,
        altitude,
        pv_land,
        load_profile_text,
        lcoe_weight,
        emissions_weight,
    ):
        if not n_clicks:
            raise PreventUpdate

        load_profile = parse_load_profile(load_profile_text)
        if not load_profile:
            raise PreventUpdate

        site = SiteContext(
            name=project_name or "floral_v1_project",
            latitude=float(latitude or 0.0),
            longitude=float(longitude or 0.0),
            altitude_m=float(altitude or 0.0),
        )
        objectives = {
            "lcoe": float(lcoe_weight or 0.0),
            "emissions": float(emissions_weight or 0.0),
        }
        request = UserRequest(
            project_name=project_name or "floral_v1_project",
            target_load_mw=float(target_load or 0.0),
            availability_target=float(availability_target or 0.0),
            site=site,
            load_profile_kw=load_profile,
            genset_size_mw=float(genset_size or 2.5),
            pv_land_m2=float(pv_land or 0.0),
            objectives=objectives,
        )
        payload = serialize_dataclass(request)
        status = "User request saved."
        return payload, status

    @app.callback(
        Output("request-preview", "children"),
        Output("load-profile-graph", "figure"),
        Input("user-request-store", "data"),
    )
    def render_request_preview(request_payload):
        if not request_payload:
            return "No request saved yet.", load_profile_figure([])

        request = user_request_from_store(request_payload)
        preview = json.dumps(request_payload, indent=2)
        figure = load_profile_figure(request.load_profile_kw)
        return preview, figure

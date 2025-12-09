from __future__ import annotations

import json
from dash import Input, Output, State, ctx
from dash.exceptions import PreventUpdate

from floral_v1.app.forms import build_user_request
from floral_v1.app.state import serialize_dataclass, user_request_from_store
from floral_v1.core.visualization import load_profile_figure


def register(app):
    @app.callback(
        Output("user-request-store", "data"),
        Output("request-status", "children"),
        Input("save-request-button", "n_clicks"),
        Input("pipeline-output-store", "data"),
        State("project-name-input", "value"),
        State("site-name-input", "value"),
        State("target-load-input", "value"),
        State("availability-target-input", "value"),
        State("genset-size-input", "value"),
        State("latitude-input", "value"),
        State("longitude-input", "value"),
        State("altitude-input", "value"),
        State("ambient-input", "value"),
        State("pv-land-input", "value"),
        State("load-profile-input", "value"),
        State("site-notes-input", "value"),
        State("objective-mode-radio", "value"),
        State("objective-weight-slider", "value"),
        State("site-geometry-store", "data"),
    )
    def save_request(
        n_clicks,
        pipeline_payload,
        project_name,
        site_name,
        target_load,
        availability_target,
        genset_size,
        latitude,
        longitude,
        altitude,
        ambient_c,
        pv_land,
        load_profile_text,
        site_notes,
        objective_mode,
        objective_weight,
        geometry_store,
    ):
        triggered = ctx.triggered_id
        if triggered == "pipeline-output-store":
            if pipeline_payload and pipeline_payload.get("user_request"):
                return pipeline_payload["user_request"], "Request captured from latest pipeline run."
            raise PreventUpdate

        if not n_clicks:
            raise PreventUpdate

        request = build_user_request(
            project_name=project_name,
            site_name=site_name,
            target_load_mw=target_load,
            availability_target=availability_target,
            genset_size_mw=genset_size,
            latitude=latitude,
            longitude=longitude,
            altitude_m=altitude,
            ambient_c=ambient_c,
            pv_land_m2=pv_land,
            load_profile_text=load_profile_text or "",
            site_notes=site_notes,
            objective_mode=objective_mode,
            objective_weight=objective_weight,
            geometry=geometry_store,
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

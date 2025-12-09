from __future__ import annotations

import json

from dash import Input, Output, State, ctx
from dash.exceptions import PreventUpdate

from floral_v1.app.state import (
    genset_design_from_store,
    serialize_dataclass,
    user_request_from_store,
)
from floral_v1.core.sizing.engine import size_gensets


def register(app):
    @app.callback(
        Output("genset-design-store", "data"),
        Input("size-gensets-button", "n_clicks"),
        Input("pipeline-output-store", "data"),
        State("user-request-store", "data"),
    )
    def run_sizing(n_clicks, pipeline_payload, request_payload):
        triggered = ctx.triggered_id
        if triggered == "pipeline-output-store":
            if pipeline_payload and pipeline_payload.get("genset_design"):
                return pipeline_payload["genset_design"]
            raise PreventUpdate
        if not n_clicks:
            raise PreventUpdate
        if not request_payload:
            raise PreventUpdate

        request = user_request_from_store(request_payload)
        design = size_gensets(request)
        payload = serialize_dataclass(design)
        return payload

    @app.callback(
        Output("genset-summary", "children"),
        Input("genset-design-store", "data"),
    )
    def render_genset_summary(genset_payload):
        if not genset_payload:
            return "Run sizing to view genset design."

        design = genset_design_from_store(genset_payload)
        summary = json.dumps(
            {
                "required_units": design.required_units,
                "installed_units": design.installed_units,
                "per_unit_mw": design.per_unit_mw,
                "expected_availability": design.expected_availability,
            },
            indent=2,
        )
        return summary

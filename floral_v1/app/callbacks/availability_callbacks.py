from __future__ import annotations

import json

from dash import Input, Output, State
from dash.exceptions import PreventUpdate

from floral_v1.app.state import (
    hybrid_design_from_store,
    serialize_dataclass,
    user_request_from_store,
)
from floral_v1.core.availability.analytical import verify_availability


def register(app):
    @app.callback(
        Output("availability-report-store", "data"),
        Output("availability-summary", "children"),
        Input("availability-button", "n_clicks"),
        State("hybrid-design-store", "data"),
        State("user-request-store", "data"),
    )
    def analyze(n_clicks, hybrid_payload, request_payload):
        if not n_clicks:
            raise PreventUpdate
        if not (hybrid_payload and request_payload):
            raise PreventUpdate

        hybrid = hybrid_design_from_store(hybrid_payload)
        request = user_request_from_store(request_payload)
        report = verify_availability(hybrid)
        payload = serialize_dataclass(report)
        summary = json.dumps(
            {
                "achieved": report.achieved,
                "target_from_design": report.target,
                "user_target": request.availability_target,
                "meets_target": report.meets_target,
            },
            indent=2,
        )
        return payload, summary

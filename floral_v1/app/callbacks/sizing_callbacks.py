from __future__ import annotations

import json

from dash import Input, Output, State
from dash.exceptions import PreventUpdate

from floral_v1.app.state import (
    serialize_dataclass,
    user_request_from_store,
)
from floral_v1.core.sizing.engine import size_gensets


def register(app):
    @app.callback(
        Output("genset-design-store", "data"),
        Output("genset-summary", "children"),
        Input("size-gensets-button", "n_clicks"),
        State("user-request-store", "data"),
    )
    def run_sizing(n_clicks, request_payload):
        if not n_clicks:
            raise PreventUpdate
        if not request_payload:
            raise PreventUpdate

        request = user_request_from_store(request_payload)
        design = size_gensets(request)
        payload = serialize_dataclass(design)
        summary = json.dumps(payload, indent=2)
        return payload, summary

from __future__ import annotations

import json

from dash import Input, Output, State
from dash.exceptions import PreventUpdate

from floral_v1.app.state import (
    genset_design_from_store,
    serialize_dataclass,
    user_request_from_store,
)
from floral_v1.core.site_plan.builder import build_site_model
from floral_v1.core.site_plan.placement import place_assets


def register(app):
    @app.callback(
        Output("site-model-store", "data"),
        Output("placement-plan-store", "data"),
        Output("site-summary", "children"),
        Output("placement-summary", "children"),
        Input("build-site-button", "n_clicks"),
        State("user-request-store", "data"),
        State("genset-design-store", "data"),
    )
    def build_site_and_place_assets(n_clicks, request_payload, genset_payload):
        if not n_clicks:
            raise PreventUpdate
        if not request_payload or not genset_payload:
            raise PreventUpdate

        request = user_request_from_store(request_payload)
        gensets = genset_design_from_store(genset_payload)
        site_model = build_site_model(request, gensets)
        placement = place_assets(site_model, gensets)
        site_payload = serialize_dataclass(site_model)
        placement_payload = serialize_dataclass(placement)
        site_summary = json.dumps(
            {
                "footprint_acres": site_model.footprint_acres,
                "buildable_acres": site_model.buildable_area_acres,
                "metadata": site_model.metadata,
            },
            indent=2,
        )
        placement_summary = json.dumps(
            {
                "assets": list(placement.asset_locations.keys()),
                "constraints": placement.constraints,
            },
            indent=2,
        )
        return site_payload, placement_payload, site_summary, placement_summary

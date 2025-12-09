from __future__ import annotations

import json

from dash import Input, Output, State
from dash.exceptions import PreventUpdate

from floral_v1.app.state import (
    genset_design_from_store,
    placement_plan_from_store,
    serialize_dataclass,
    site_model_from_store,
    user_request_from_store,
)
from floral_v1.core.optimizer.engine import optimize_hybrid


def register(app):
    @app.callback(
        Output("hybrid-design-store", "data"),
        Output("hybrid-summary", "children"),
        Input("optimize-hybrid-button", "n_clicks"),
        State("user-request-store", "data"),
        State("site-model-store", "data"),
        State("genset-design-store", "data"),
        State("placement-plan-store", "data"),
    )
    def optimize(n_clicks, request_payload, site_payload, genset_payload, placement_payload):
        if not n_clicks:
            raise PreventUpdate
        if not (request_payload and site_payload and genset_payload and placement_payload):
            raise PreventUpdate

        request = user_request_from_store(request_payload)
        site_model = site_model_from_store(site_payload)
        gensets = genset_design_from_store(genset_payload)
        placement = placement_plan_from_store(placement_payload)
        hybrid = optimize_hybrid(
            site_model,
            gensets,
            placement,
            request.load_profile_kw,
            request.objectives,
        )
        payload = serialize_dataclass(hybrid)
        summary = json.dumps(
            {
                "pv_capacity_kw": hybrid.pv_capacity_kw,
                "bess_energy_mwh": hybrid.bess_energy_mwh,
                "bess_power_mw": hybrid.bess_power_mw,
            },
            indent=2,
        )
        return payload, summary

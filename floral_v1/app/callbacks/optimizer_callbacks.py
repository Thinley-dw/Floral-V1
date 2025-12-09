from __future__ import annotations

import json

from dash import Input, Output, State
from dash.exceptions import PreventUpdate

from floral_v1.app.state import (
    genset_design_from_store,
    hybrid_design_from_store,
    placement_plan_from_store,
    serialize_dataclass,
    site_model_from_store,
    user_request_from_store,
)
from floral_v1.core.optimizer.engine import optimize_hybrid
from floral_v1.core.visualization import hybrid_capacity_figure


def register(app):
    @app.callback(
        Output("hybrid-design-store", "data"),
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
        return payload

    @app.callback(
        Output("hybrid-summary", "children"),
        Output("hybrid-capacity-graph", "figure"),
        Input("hybrid-design-store", "data"),
    )
    def render_hybrid_summary(hybrid_payload):
        if not hybrid_payload:
            return "No hybrid design available.", hybrid_capacity_figure(None)

        hybrid = hybrid_design_from_store(hybrid_payload)
        summary = json.dumps(
            {
                "pv_capacity_kw": hybrid.pv_capacity_kw,
                "bess_energy_mwh": hybrid.bess_energy_mwh,
                "bess_power_mw": hybrid.bess_power_mw,
            },
            indent=2,
        )
        figure = hybrid_capacity_figure(hybrid)
        return summary, figure

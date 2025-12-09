from __future__ import annotations

import json

from dash import Input, Output, State, ctx
from dash.exceptions import PreventUpdate

from floral_v1.app.state import (
    genset_design_from_store,
    placement_plan_from_store,
    serialize_dataclass,
    site_model_from_store,
    user_request_from_store,
)
from floral_v1.core.site_plan.builder import build_site_model
from floral_v1.core.site_plan.placement import place_assets
from floral_v1.core.visualization import placement_map_figure


def register(app):
    @app.callback(
        Output("site-model-store", "data"),
        Output("placement-plan-store", "data"),
        Input("build-site-button", "n_clicks"),
        Input("pipeline-output-store", "data"),
        State("user-request-store", "data"),
        State("genset-design-store", "data"),
    )
    def build_site_and_place_assets(n_clicks, pipeline_payload, request_payload, genset_payload):
        triggered = ctx.triggered_id
        if triggered == "pipeline-output-store":
            if pipeline_payload:
                return pipeline_payload.get("site_model"), pipeline_payload.get("placement_plan")
            raise PreventUpdate
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
        return site_payload, placement_payload

    @app.callback(
        Output("site-summary", "children"),
        Input("site-model-store", "data"),
    )
    def render_site_summary(site_payload):
        if not site_payload:
            return "Build the site to view summary."

        site_model = site_model_from_store(site_payload)
        summary = json.dumps(
            {
                "footprint_acres": site_model.footprint_acres,
                "buildable_acres": site_model.buildable_area_acres,
                "metadata": site_model.metadata,
            },
            indent=2,
        )
        return summary

    @app.callback(
        Output("placement-summary", "children"),
        Output("placement-graph", "figure"),
        Input("placement-plan-store", "data"),
    )
    def render_placement_summary(placement_payload):
        if not placement_payload:
            return "No placement plan available.", placement_map_figure(None)

        placement = placement_plan_from_store(placement_payload)
        summary = json.dumps(
            {
                "assets": list(placement.asset_locations.keys()),
                "constraints": placement.constraints,
            },
            indent=2,
        )
        figure = placement_map_figure(placement)
        return summary, figure

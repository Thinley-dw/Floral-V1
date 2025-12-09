from __future__ import annotations

from dash import Input, Output, State, html
from dash.exceptions import PreventUpdate

from floral_v1.ai_engine import build_ai_context, generate_ai_response, simulation_config_from_metadata
from floral_v1.app.state import (
    availability_report_from_store,
    genset_design_from_store,
    hybrid_design_from_store,
    placement_plan_from_store,
    simulation_result_from_store,
    site_model_from_store,
    user_request_from_store,
)
from floral_v1.core.models import SimulationConfig


def _derive_config_from_metadata(sim_payload) -> SimulationConfig | None:
    if not sim_payload:
        return None
    metadata = sim_payload.get("metadata") if isinstance(sim_payload, dict) else None
    return simulation_config_from_metadata(metadata)


def _info_panel_children(request, des_result) -> list:
    if not request or not des_result:
        return [html.P("Run DES to generate diagnostics.")]
    metadata = des_result.metadata or {}
    mode = metadata.get("des_mode", "stochastic")
    items = [
        html.P(f"Project: {request.project_name}"),
        html.P(f"DES mode: {mode}"),
        html.P(f"DES availability: {des_result.availability:.5f}"),
    ]
    return items


def register(app):
    @app.callback(
        Output("ai-context-store", "data"),
        Output("ai-report-store", "data"),
        Output("ai-info-panel", "children"),
        Input("simulation-result-store", "data"),
        State("user-request-store", "data"),
        State("site-model-store", "data"),
        State("genset-design-store", "data"),
        State("placement-plan-store", "data"),
        State("hybrid-design-store", "data"),
        State("availability-report-store", "data"),
    )
    def update_ai_report(
        sim_payload,
        request_payload,
        site_payload,
        genset_payload,
        placement_payload,
        hybrid_payload,
        availability_payload,
    ):
        if not sim_payload:
            placeholder = "Run the full pipeline (including DES) before using Floragen AI."
            return "", placeholder, html.P("Awaiting DES run...")

        request = user_request_from_store(request_payload) if request_payload else None
        site = site_model_from_store(site_payload) if site_payload else None
        gensets = genset_design_from_store(genset_payload) if genset_payload else None
        placement = placement_plan_from_store(placement_payload) if placement_payload else None
        hybrid = hybrid_design_from_store(hybrid_payload) if hybrid_payload else None
        availability = (
            availability_report_from_store(availability_payload) if availability_payload else None
        )
        sim_result = simulation_result_from_store(sim_payload)
        des_config = _derive_config_from_metadata(sim_payload)

        context = build_ai_context(
            request,
            site,
            gensets,
            placement,
            hybrid,
            availability,
            des_config,
            sim_result,
        )
        response = generate_ai_response(context)
        info_panel = _info_panel_children(request, sim_result)
        return context, response, info_panel

    @app.callback(
        Output("ai-report-store", "data"),
        Output("ai-question-input", "value"),
        Input("ask-floragen-button", "n_clicks"),
        State("ai-context-store", "data"),
        State("ai-report-store", "data"),
        State("ai-question-input", "value"),
        prevent_initial_call=True,
    )
    def handle_question(n_clicks, context, current_report, question):
        if not n_clicks:
            raise PreventUpdate
        if not context:
            return current_report or "Run DES first.", question
        answer = generate_ai_response(context, question=question or None)
        if current_report:
            combined = f"{current_report}\n\n{answer}"
        else:
            combined = answer
        return combined, ""

    @app.callback(
        Output("ai-report-display", "children"),
        Input("ai-report-store", "data"),
    )
    def render_report(text):
        return text or "Floragen AI diagnostics will appear here after DES runs."

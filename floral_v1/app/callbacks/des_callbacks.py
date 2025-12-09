from __future__ import annotations

import json

from dash import Input, Output, State
from dash.exceptions import PreventUpdate

from floral_v1.app.state import (
    hybrid_design_from_store,
    serialize_dataclass,
    simulation_result_from_store,
)
from floral_v1.core.des.engine import run_des
from floral_v1.core.models import SimulationConfig
from floral_v1.core.visualization import (
    des_energy_split_pie,
    des_result_figure,
    des_timeline_figure,
)


def register(app):
    @app.callback(
        Output("simulation-result-store", "data"),
        Input("run-des-button", "n_clicks"),
        State("hybrid-design-store", "data"),
        State("simulation-hours-input", "value"),
        State("des-mode-dropdown", "value"),
    )
    def run_des_callback(n_clicks, hybrid_payload, hours_value, mode_value):
        if not n_clicks:
            raise PreventUpdate
        if not hybrid_payload:
            raise PreventUpdate

        hybrid = hybrid_design_from_store(hybrid_payload)
        hours = int(hours_value or 1)
        mode = (mode_value or "stochastic").lower()
        config = SimulationConfig(hours=hours, mode=mode)
        result = run_des(hybrid, config)
        payload = serialize_dataclass(result)
        return payload

    @app.callback(
        Output("des-summary", "children"),
        Output("des-graph", "figure"),
        Output("des-timeline-graph", "figure"),
        Output("des-energy-pie-graph", "figure"),
        Input("simulation-result-store", "data"),
    )
    def render_des_summary(sim_payload):
        if not sim_payload:
            placeholder = "Run DES to view simulation results."
            empty = des_result_figure(None)
            return placeholder, empty, des_timeline_figure(None), des_energy_split_pie(None)

        result = simulation_result_from_store(sim_payload)
        summary = json.dumps(
            {
                "availability": result.availability,
                "outage_hours": result.outage_hours,
                "unserved_energy_mwh": result.unserved_energy_mwh,
            },
            indent=2,
        )
        figure = des_result_figure(result)
        timeline_fig = des_timeline_figure(result)
        pie_fig = des_energy_split_pie(result)
        return summary, figure, timeline_fig, pie_fig

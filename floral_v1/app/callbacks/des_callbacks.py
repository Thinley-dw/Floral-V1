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


def register(app):
    @app.callback(
        Output("simulation-result-store", "data"),
        Output("des-summary", "children"),
        Input("run-des-button", "n_clicks"),
        State("hybrid-design-store", "data"),
        State("simulation-hours-input", "value"),
    )
    def run_des_callback(n_clicks, hybrid_payload, hours_value):
        if not n_clicks:
            raise PreventUpdate
        if not hybrid_payload:
            raise PreventUpdate

        hybrid = hybrid_design_from_store(hybrid_payload)
        hours = int(hours_value or 1)
        config = SimulationConfig(hours=hours)
        result = run_des(hybrid, config)
        payload = serialize_dataclass(result)
        summary = json.dumps(
            {
                "availability": result.availability,
                "outage_hours": result.outage_hours,
                "unserved_energy_mwh": result.unserved_energy_mwh,
            },
            indent=2,
        )
        return payload, summary

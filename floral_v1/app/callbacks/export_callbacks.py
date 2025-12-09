from __future__ import annotations

from pathlib import Path
from typing import Optional

from dash import Input, Output, State, no_update
from dash.exceptions import PreventUpdate

from floral_v1.ai_engine import simulation_config_from_metadata
from floral_v1.app.state import (
    availability_report_from_store,
    genset_design_from_store,
    hybrid_design_from_store,
    placement_plan_from_store,
    serialize_dataclass,
    site_model_from_store,
    simulation_result_from_store,
    user_request_from_store,
)
from floral_v1.core.site_plan.blender_export import build_blender_package
from floral_v1.scenarios import list_scenarios, load_scenario, save_scenario

EXPORT_ROOT = Path(__file__).resolve().parents[2] / "exports"


def register(app):
    @app.callback(
        Output("export-status", "children"),
        Input("export-button", "n_clicks"),
        State("site-model-store", "data"),
        State("hybrid-design-store", "data"),
    )
    def export_bundle(n_clicks, site_payload, hybrid_payload):
        if not n_clicks:
            raise PreventUpdate
        if not (site_payload and hybrid_payload):
            raise PreventUpdate

        site = site_model_from_store(site_payload)
        hybrid = hybrid_design_from_store(hybrid_payload)
        output_dir = EXPORT_ROOT / site.site.name.replace(" ", "_")
        output_dir.mkdir(parents=True, exist_ok=True)
        site_map_path = build_blender_package(site, hybrid, str(output_dir))
        return f"Blender bundle exported to {site_map_path}"

    @app.callback(
        Output("save-scenario-status", "children"),
        Output("scenario-file-dropdown", "options"),
        Output("scenario-file-dropdown", "value"),
        Input("save-scenario-button", "n_clicks"),
        State("scenario-name-input", "value"),
        State("user-request-store", "data"),
        State("site-model-store", "data"),
        State("genset-design-store", "data"),
        State("placement-plan-store", "data"),
        State("hybrid-design-store", "data"),
        State("availability-report-store", "data"),
        State("simulation-result-store", "data"),
    )
    def save_scenario_bundle(
        n_clicks,
        scenario_name,
        request_payload,
        site_payload,
        genset_payload,
        placement_payload,
        hybrid_payload,
        availability_payload,
        simulation_payload,
    ):
        if not n_clicks:
            raise PreventUpdate

        slug = _slugify_name(scenario_name)
        data = {
            "user_request": user_request_from_store(request_payload) if request_payload else None,
            "site_model": site_model_from_store(site_payload) if site_payload else None,
            "genset_design": genset_design_from_store(genset_payload) if genset_payload else None,
            "placement_plan": placement_plan_from_store(placement_payload) if placement_payload else None,
            "hybrid_design": hybrid_design_from_store(hybrid_payload) if hybrid_payload else None,
            "availability_report": availability_report_from_store(availability_payload) if availability_payload else None,
            "simulation_result": simulation_result_from_store(simulation_payload) if simulation_payload else None,
        }
        sim_result = data["simulation_result"]
        if sim_result:
            data["des_config"] = simulation_config_from_metadata(sim_result.metadata)
        else:
            data["des_config"] = None
        destination = save_scenario(f"{slug}.json", data)
        options = [
            {"label": path.name, "value": str(path)}
            for path in list_scenarios()
        ]
        status = f"Scenario saved to {destination}"
        return status, options, str(destination)

    @app.callback(
        Output("user-request-store", "data"),
        Output("genset-design-store", "data"),
        Output("site-model-store", "data"),
        Output("placement-plan-store", "data"),
        Output("hybrid-design-store", "data"),
        Output("availability-report-store", "data"),
        Output("simulation-result-store", "data"),
        Output("load-scenario-status", "children"),
        Input("load-scenario-button", "n_clicks"),
        State("scenario-file-dropdown", "value"),
    )
    def load_scenario_bundle(n_clicks, scenario_path):
        if not n_clicks:
            raise PreventUpdate
        if not scenario_path:
            return (no_update,) * 7 + ("Select a scenario to load.",)

        data = load_scenario(scenario_path)
        response = []
        for key in (
            "user_request",
            "genset_design",
            "site_model",
            "placement_plan",
            "hybrid_design",
            "availability_report",
            "simulation_result",
        ):
            value = data.get(key)
            response.append(serialize_dataclass(value) if value else None)
        response.append(f"Loaded scenario from {scenario_path}")
        return tuple(response)


def _slugify_name(name: Optional[str]) -> str:
    if not name:
        return "scenario"
    slug = name.strip().lower().replace(" ", "_")
    return slug or "scenario"

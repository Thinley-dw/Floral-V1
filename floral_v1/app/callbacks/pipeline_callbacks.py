from __future__ import annotations

from dash import Input, Output, State, ctx
from dash.exceptions import PreventUpdate

from floral_v1.app.forms import build_user_request
from floral_v1.app.paths import EXPORT_ROOT
from floral_v1.app.state import serialize_dataclass
from floral_v1.core.availability.analytical import verify_availability
from floral_v1.core.des.engine import run_des
from floral_v1.core.models import SimulationConfig
from floral_v1.core.optimizer.engine import optimize_hybrid
from floral_v1.core.sizing.engine import size_gensets
from floral_v1.core.site_plan.blender_export import build_blender_package
from floral_v1.core.site_plan.builder import build_site_model
from floral_v1.core.site_plan.placement import place_assets


def register(app):
    @app.callback(
        Output("pipeline-output-store", "data"),
        Output("pipeline-status", "children"),
        Input("run-full-pipeline-button", "n_clicks"),
        State("project-name-input", "value"),
        State("site-name-input", "value"),
        State("target-load-input", "value"),
        State("availability-target-input", "value"),
        State("genset-size-input", "value"),
        State("latitude-input", "value"),
        State("longitude-input", "value"),
        State("altitude-input", "value"),
        State("ambient-input", "value"),
        State("pv-land-input", "value"),
        State("load-profile-input", "value"),
        State("site-notes-input", "value"),
        State("objective-mode-radio", "value"),
        State("objective-weight-slider", "value"),
        State("site-geometry-store", "data"),
        State("simulation-hours-input", "value"),
        State("des-mode-dropdown", "value"),
        prevent_initial_call=True,
    )
    def run_pipeline(
        n_clicks,
        project_name,
        site_name,
        target_load,
        availability_target,
        genset_size,
        latitude,
        longitude,
        altitude,
        ambient_c,
        pv_land,
        load_profile_text,
        site_notes,
        objective_mode,
        objective_weight,
        geometry_store,
        sim_hours_value,
        mode_value,
    ):
        if not n_clicks:
            raise PreventUpdate

        try:
            request = build_user_request(
                project_name=project_name,
                site_name=site_name,
                target_load_mw=target_load,
                availability_target=availability_target,
                genset_size_mw=genset_size,
                latitude=latitude,
                longitude=longitude,
                altitude_m=altitude,
                ambient_c=ambient_c,
                pv_land_m2=pv_land,
                load_profile_text=load_profile_text or "",
                site_notes=site_notes,
                objective_mode=objective_mode,
                objective_weight=objective_weight,
                geometry=geometry_store,
            )
            gensets = size_gensets(request)
            site_model = build_site_model(request, gensets)
            placement = place_assets(site_model, gensets)
            hybrid = optimize_hybrid(
                site_model,
                gensets,
                placement,
                request.load_profile_kw,
                request.objectives,
            )
            availability_report = verify_availability(hybrid)
            hours = int(sim_hours_value or 168)
            mode = (mode_value or "stochastic").lower()
            sim_config = SimulationConfig(hours=hours, mode=mode)
            sim_result = run_des(hybrid, sim_config)

            output_dir = EXPORT_ROOT / site_model.site.name.replace(" ", "_")
            output_dir.mkdir(parents=True, exist_ok=True)
            bundle_path = build_blender_package(site_model, hybrid, str(output_dir))

            payload = {
                "user_request": serialize_dataclass(request),
                "genset_design": serialize_dataclass(gensets),
                "site_model": serialize_dataclass(site_model),
                "placement_plan": serialize_dataclass(placement),
                "hybrid_design": serialize_dataclass(hybrid),
                "availability_report": serialize_dataclass(availability_report),
                "simulation_result": serialize_dataclass(sim_result),
                "des_config": serialize_dataclass(sim_config),
                "export_path": str(bundle_path) if bundle_path else "",
            }
            status = (
                f"Pipeline complete · DES availability {sim_result.availability:.4f} "
                f"· Outage hours {sim_result.outage_hours:.2f}"
            )
            return payload, status
        except ValueError as exc:
            previous = ctx.states.get("pipeline-output-store.data")
            return previous, f"Input error: {exc}"
        except Exception as exc:
            previous = ctx.states.get("pipeline-output-store.data")
            return previous, f"Pipeline failed: {exc}"

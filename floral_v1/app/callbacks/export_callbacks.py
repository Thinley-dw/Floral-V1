from __future__ import annotations

from pathlib import Path

from dash import Input, Output, State
from dash.exceptions import PreventUpdate

from floral_v1.app.state import hybrid_design_from_store, site_model_from_store
from floral_v1.core.site_plan.blender_export import build_blender_package

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

from __future__ import annotations

from dash import dcc, html


STORE_IDS = [
    "user-request-store",
    "genset-design-store",
    "site-model-store",
    "placement-plan-store",
    "hybrid-design-store",
    "availability-report-store",
    "simulation-result-store",
]


def _default_load_profile() -> str:
    return ",".join(["45000"] * 24)


def get_layout():
    stores = [dcc.Store(id=store_id) for store_id in STORE_IDS]
    stores.append(dcc.Store(id="export-status-store"))

    return html.Div(
        [
            *stores,
            html.H1("Floral V1 Integrated Planner"),
            dcc.Tabs(
                id="main-tabs",
                value="inputs-tab",
                children=[
                    dcc.Tab(label="Inputs", value="inputs-tab", children=_inputs_tab()),
                    dcc.Tab(label="Site & Placement", value="site-tab", children=_site_tab()),
                    dcc.Tab(label="Optimization", value="optimizer-tab", children=_optimizer_tab()),
                    dcc.Tab(label="Availability & DES", value="des-tab", children=_availability_tab()),
                    dcc.Tab(label="Export", value="export-tab", children=_export_tab()),
                ],
            ),
        ],
        className="container",
    )


def _inputs_tab():
    return html.Div(
        className="tab-body",
        children=[
            html.H3("Project Inputs"),
            html.Div(
                className="form-grid",
                children=[
                    html.Label("Project Name"),
                    dcc.Input(id="project-name-input", type="text", value="floral_v1_demo"),
                    html.Label("Target Load (MW)"),
                    dcc.Input(id="target-load-input", type="number", value=45.0, min=1),
                    html.Label("Availability Target"),
                    dcc.Input(id="availability-target-input", type="number", value=0.999, step=0.001, min=0, max=1),
                    html.Label("Genset Size (MW)"),
                    dcc.Input(id="genset-size-input", type="number", value=2.5, step=0.1),
                    html.Label("Latitude"),
                    dcc.Input(id="latitude-input", type="number", value=1.3521, step=0.0001),
                    html.Label("Longitude"),
                    dcc.Input(id="longitude-input", type="number", value=103.8198, step=0.0001),
                    html.Label("Altitude (m)"),
                    dcc.Input(id="altitude-input", type="number", value=0.0, step=1),
                    html.Label("PV Land (m²)"),
                    dcc.Input(id="pv-land-input", type="number", value=20000, step=1000),
                    html.Label("LCOE Weight"),
                    dcc.Input(id="objective-lcoe-input", type="number", value=1.0, step=0.1),
                    html.Label("Emissions Weight"),
                    dcc.Input(id="objective-emissions-input", type="number", value=0.0, step=0.1),
                ],
            ),
            html.Label("Load Profile (kW, comma-separated)"),
            dcc.Textarea(
                id="load-profile-input",
                value=_default_load_profile(),
                style={"width": "100%", "height": "120px"},
            ),
            html.Div(
                className="button-row",
                children=[
                    html.Button("Save User Request", id="save-request-button", n_clicks=0),
                    html.Button("Size Gensets", id="size-gensets-button", n_clicks=0),
                ],
            ),
            html.Div(id="request-status", className="status-text"),
            html.Pre(id="request-preview", className="code-block"),
            html.H3("Sizing Output"),
            html.Div(id="genset-summary", className="summary-card"),
        ],
    )


def _site_tab():
    return html.Div(
        className="tab-body",
        children=[
            html.H3("Site & Placement"),
            html.Div(
                className="button-row",
                children=[
                    html.Button("Build Site & Place Assets", id="build-site-button", n_clicks=0),
                ],
            ),
            html.Div(id="site-summary", className="summary-card"),
            html.Div(id="placement-summary", className="summary-card"),
        ],
    )


def _optimizer_tab():
    return html.Div(
        className="tab-body",
        children=[
            html.H3("Hybrid Optimization"),
            html.Button("Optimize Hybrid", id="optimize-hybrid-button", n_clicks=0),
            html.Div(id="hybrid-summary", className="summary-card"),
        ],
    )


def _availability_tab():
    return html.Div(
        className="tab-body",
        children=[
            html.H3("Availability Analysis"),
            html.Button("Analyze Availability", id="availability-button", n_clicks=0),
            html.Div(id="availability-summary", className="summary-card"),
            html.H3("Discrete Event Simulation"),
            html.Label("Simulation Hours"),
            dcc.Input(id="simulation-hours-input", type="number", value=168, min=1, step=1),
            html.Button("Run DES", id="run-des-button", n_clicks=0),
            html.Div(id="des-summary", className="summary-card"),
        ],
    )


def _export_tab():
    return html.Div(
        className="tab-body",
        children=[
            html.H3("Blender Export"),
            html.Button("Export Blender Bundle", id="export-button", n_clicks=0),
            html.Div(id="export-status", className="summary-card"),
        ],
    )

from __future__ import annotations

from dash import dcc, html

from floral_v1.app.feature_flags import DASH_LEAFLET, HAS_DASH_LEAFLET

if HAS_DASH_LEAFLET:
    dl = DASH_LEAFLET
else:
    dl = None


def get_layout():
    return html.Div(
        className="floral-app",
        children=[
            _stores(),
            html.Div(
                className="app-shell",
                children=[
                    _header(),
                    html.Div(
                        className="app-content",
                        children=[
                            dcc.Tabs(
                                id="app-tabs",
                                className="floral-tabs",
                                value="inputs",
                                children=[
                                    dcc.Tab(
                                        label="Inputs",
                                        className="floral-tab",
                                        selected_className="floral-tab--selected",
                                        value="inputs",
                                        children=_inputs_tab(),
                                    ),
                                    dcc.Tab(
                                        label="Site & Placement",
                                        className="floral-tab",
                                        selected_className="floral-tab--selected",
                                        value="site",
                                        children=_site_tab(),
                                    ),
                                    dcc.Tab(
                                        label="Optimization",
                                        className="floral-tab",
                                        selected_className="floral-tab--selected",
                                        value="optimization",
                                        children=_optimization_tab(),
                                    ),
                                    dcc.Tab(
                                        label="Availability & DES",
                                        className="floral-tab",
                                        selected_className="floral-tab--selected",
                                        value="des",
                                        children=_availability_tab(),
                                    ),
                                    dcc.Tab(
                                        label="Export",
                                        className="floral-tab",
                                        selected_className="floral-tab--selected",
                                        value="export",
                                        children=_export_tab(),
                                    ),
                                    dcc.Tab(
                                        label="Floragen AI",
                                        className="floral-tab",
                                        selected_className="floral-tab--selected",
                                        value="ai",
                                        children=_ai_tab(),
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )


def _stores() -> html.Div:
    return html.Div(
        style={"display": "none"},
        children=[
            dcc.Store(id="user-request-store"),
            dcc.Store(id="genset-design-store"),
            dcc.Store(id="site-model-store"),
            dcc.Store(id="placement-plan-store"),
            dcc.Store(id="hybrid-design-store"),
            dcc.Store(id="availability-report-store"),
            dcc.Store(id="simulation-result-store"),
            dcc.Store(id="ai-context-store"),
            dcc.Store(id="ai-report-store"),
            dcc.Store(id="site-geometry-store", data={"boundary": None, "entrance": None, "gas_line": None}),
            dcc.Store(id="pipeline-output-store"),
        ],
    )


def _header() -> html.Div:
    return html.Div(
        className="app-header",
        children=[
            html.Div(
                className="brand",
                children=[
                    html.Div("⚡️", className="brand-mark"),
                    html.Div(
                        children=[
                            html.H1("Floral V1 Planner"),
                            html.P("CHP / PV / BESS availability, optimization, DES & AI"),
                        ]
                    ),
                ],
            ),
            html.Div(
                className="header-meta",
                children=[
                    html.Span("Integrated pipeline ready"),
                    html.Small("Size → Site → Optimize → Availability → DES → Export"),
                ],
            ),
        ],
    )


def _inputs_tab() -> html.Div:
    return html.Div(
        className="tab-pane",
        children=[
            _card(
                "Project & Site Setup",
                "Provide headline information for the project and site.",
                html.Div(
                    className="form-grid two-col",
                    children=[
                        html.Div(
                            className="form-column",
                            children=[
                                _input_field(
                                    "Project Name",
                                    dcc.Input(
                                        id="project-name-input",
                                        type="text",
                                        placeholder="Project Aurora",
                                        className="text-input",
                                    ),
                                ),
                                _input_field(
                                    "Site Name",
                                    dcc.Input(
                                        id="site-name-input",
                                        type="text",
                                        placeholder="Aurora Campus East",
                                        className="text-input",
                                    ),
                                ),
                                _input_field(
                                    "Site Notes",
                                    dcc.Textarea(
                                        id="site-notes-input",
                                        placeholder="e.g. brownfield redevelopment, close to LNG terminal...",
                                        className="textarea-input",
                                        spellCheck=False,
                                    ),
                                ),
                            ],
                        ),
                        html.Div(
                            className="form-column",
                            children=[
                                _input_field(
                                    "Latitude",
                                    dcc.Input(
                                        id="latitude-input",
                                        type="number",
                                        placeholder="1.3521",
                                        className="text-input",
                                    ),
                                ),
                                _input_field(
                                    "Longitude",
                                    dcc.Input(
                                        id="longitude-input",
                                        type="number",
                                        placeholder="103.8198",
                                        className="text-input",
                                    ),
                                ),
                                _input_field(
                                    "Altitude (m)",
                                    dcc.Input(
                                        id="altitude-input",
                                        type="number",
                                        placeholder="30",
                                        className="text-input",
                                    ),
                                ),
                                _input_field(
                                    "Ambient Temperature (°C)",
                                    dcc.Input(
                                        id="ambient-input",
                                        type="number",
                                        placeholder="25",
                                        className="text-input",
                                    ),
                                ),
                            ],
                        ),
                    ],
                ),
            ),
            _card(
                "Load & Environment",
                "Describe the target load, availability goal, and hourly demand profile.",
                html.Div(
                    className="form-grid two-col",
                    children=[
                        html.Div(
                            className="form-column",
                            children=[
                                _input_field(
                                    "Target Load (MW)",
                                    dcc.Input(id="target-load-input", type="number", placeholder="10", className="text-input"),
                                ),
                                _input_field(
                                    "Availability Target",
                                    dcc.Input(id="availability-target-input", type="number", placeholder="0.999", className="text-input"),
                                ),
                                _input_field(
                                    "Genset Size (MW)",
                                    dcc.Input(id="genset-size-input", type="number", placeholder="2.5", className="text-input"),
                                ),
                                _input_field(
                                    "PV Land (m²)",
                                    dcc.Input(id="pv-land-input", type="number", placeholder="100000", className="text-input"),
                                ),
                            ],
                        ),
                        html.Div(
                            className="form-column",
                            children=[
                                _input_field(
                                    "Load Profile (kW, csv or newline)",
                                    dcc.Textarea(
                                        id="load-profile-input",
                                        placeholder="1000, 1050, 1200, ...",
                                        className="textarea-input",
                                        spellCheck=False,
                                    ),
                                    "Enter at least 24 hourly values.",
                                ),
                            ],
                        ),
                    ],
                ),
            ),
            _card(
                "Optimization Objectives",
                "Choose whether to prioritize LCOE, emissions, or a weighted tradeoff.",
                html.Div(
                    className="form-grid",
                    children=[
                        _input_field(
                            "Objective Mode",
                            dcc.RadioItems(
                                id="objective-mode-radio",
                                options=[
                                    {"label": "Minimize LCOE", "value": "lcoe"},
                                    {"label": "Minimize Emissions", "value": "emissions"},
                                    {"label": "Weighted Tradeoff", "value": "weighted"},
                                ],
                                value="lcoe",
                                className="radio-input",
                                labelStyle={"display": "inline-block", "margin-right": "12px"},
                            ),
                        ),
                        _input_field(
                            "LCOE Weight (for weighted mode)",
                            dcc.Slider(
                                id="objective-weight-slider",
                                min=0.0,
                                max=1.0,
                                step=0.05,
                                value=0.5,
                                tooltip={"placement": "bottom", "always_visible": False},
                            ),
                            "Emissions weight becomes 1 - LCOE weight.",
                        ),
                    ],
                ),
            ),
            _geometry_card(),
            _card(
                "Run Optimization & Preview",
                "Save inputs, run single steps, or trigger the entire pipeline.",
                html.Div(
                    children=[
                        html.Div(
                            className="button-row",
                            children=[
                                html.Button("Save Request", id="save-request-button", className="btn primary"),
                                html.Button("Size Gensets", id="size-gensets-button", className="btn"),
                                html.Button("Optimize System", id="run-full-pipeline-button", className="btn primary"),
                            ],
                        ),
                        html.Div(
                            className="status-grid",
                            children=[
                                html.Div(
                                    className="status-card",
                                    children=[
                                        html.H4("Status"),
                                        html.Div("Awaiting input...", id="request-status"),
                                    ],
                                ),
                                html.Div(
                                    className="status-card",
                                    children=[
                                        html.H4("Pipeline"),
                                        html.Div("Run Optimize System to populate every stage.", id="pipeline-status"),
                                    ],
                                ),
                                html.Div(
                                    className="status-card",
                                    children=[
                                        html.H4("Request Payload"),
                                        html.Pre(id="request-preview", className="code-block"),
                                    ],
                                ),
                            ],
                        ),
                        dcc.Graph(id="load-profile-graph", config={"displayModeBar": False}),
                    ],
                ),
            ),
        ],
    )

def _site_tab() -> html.Div:
    return html.Div(
        className="tab-pane",
        children=[
            _card(
                "Site Modeling & Placement",
                "Build a 3D-aware site model and drop initial placements.",
                html.Div(
                    children=[
                        html.Div(
                            "Use heuristics to convert the request into a buildable footprint.",
                            className="card-description",
                        ),
                        html.Div(
                            className="button-row",
                            children=[
                                html.Button(
                                    "Build Site & Placement",
                                    id="build-site-button",
                                    className="btn primary",
                                )
                            ],
                        ),
                    ],
                ),
            ),
            html.Div(
                className="card-grid two-col",
                children=[
                    _card(
                        "Site Summary",
                        "Footprint, buildable acreage, metadata.",
                        html.Pre(id="site-summary", className="code-block"),
                    ),
                    _card(
                        "Placement Plan",
                        "Asset coordinates and constraints.",
                        html.Pre(id="placement-summary", className="code-block"),
                    ),
                ],
            ),
            _card(
                "Placement Map",
                "Spatial snapshot of asset layout.",
                dcc.Graph(id="placement-graph"),
            ),
        ],
    )


def _optimization_tab() -> html.Div:
    return html.Div(
        className="tab-pane",
        children=[
            _card(
                "Sizing Snapshots",
                "Monitor genset sizing alongside hybrid optimization outputs.",
                html.Div(
                    className="kpi-grid two-col",
                    children=[
                        html.Div(
                            className="kpi-card",
                            children=[
                                html.Span("Genset Design", className="kpi-label"),
                                html.Pre(id="genset-summary", className="code-block"),
                            ],
                        ),
                        html.Div(
                            className="kpi-card",
                            children=[
                                html.Span("Hybrid Design", className="kpi-label"),
                                html.Pre(id="hybrid-summary", className="code-block"),
                            ],
                        ),
                    ],
                ),
            ),
            _card(
                "Hybrid Optimization",
                "Run the optimizer to balance cost, emissions, and availability.",
                html.Div(
                    children=[
                        html.Div(
                            className="button-row",
                            children=[
                                html.Button("Optimize Hybrid", id="optimize-hybrid-button", className="btn primary"),
                            ],
                        ),
                        dcc.Graph(id="hybrid-capacity-graph"),
                    ],
                ),
            ),
        ],
    )


def _availability_tab() -> html.Div:
    return html.Div(
        className="tab-pane",
        children=[
            _card(
                "Analytical Availability",
                "K-of-N availability analytics from the hybrid architecture.",
                html.Div(
                    children=[
                        html.Div(
                            className="button-row",
                            children=[
                                html.Button("Verify Availability", id="availability-button", className="btn primary"),
                            ],
                        ),
                        html.Div(
                            className="kpi-grid",
                            children=[
                                html.Div(
                                    className="kpi-card",
                                    children=[
                                        html.Span("Availability Summary", className="kpi-label"),
                                        html.Pre(id="availability-summary", className="code-block"),
                                    ],
                                ),
                            ],
                        ),
                        dcc.Graph(id="availability-graph"),
                    ],
                ),
            ),
            _card(
                "DES Controls",
                "Configure the stochastic engine before running a full simulation.",
                html.Div(
                    className="form-grid two-col",
                    children=[
                        _input_field(
                            "Simulation Hours",
                            dcc.Input(
                                id="simulation-hours-input",
                                type="number",
                                placeholder="168",
                                className="text-input",
                                value=168,
                            ),
                        ),
                        _input_field(
                            "DES Mode",
                            dcc.Dropdown(
                                id="des-mode-dropdown",
                                options=[
                                    {"label": "Stochastic", "value": "stochastic"},
                                    {"label": "Scheduled", "value": "scheduled"},
                                    {"label": "Hybrid", "value": "hybrid"},
                                ],
                                value="stochastic",
                                clearable=False,
                                className="dropdown-input",
                            ),
                        ),
                        html.Div(
                            className="form-column full-width",
                            children=[
                                html.Button("Run DES", id="run-des-button", className="btn primary"),
                            ],
                        ),
                    ],
                ),
            ),
            _card(
                "DES Diagnostics",
                "SimPy power system KPIs and timeline.",
                html.Div(
                    children=[
                        html.Div(
                            className="kpi-grid",
                            children=[
                                html.Div(
                                    className="kpi-card",
                                    children=[
                                        html.Span("DES Summary", className="kpi-label"),
                                        html.Pre(id="des-summary", className="code-block"),
                                    ],
                                ),
                            ],
                        ),
                        dcc.Graph(id="des-graph"),
                        html.Div(
                            className="card-grid two-col",
                            children=[
                                dcc.Graph(id="des-timeline-graph"),
                                dcc.Graph(id="des-energy-pie-graph"),
                            ],
                        ),
                    ],
                ),
            ),
        ],
    )


def _export_tab() -> html.Div:
    return html.Div(
        className="tab-pane",
        children=[
            _card(
                "Export Blender Package",
                "Bundle terrain, placements, and hybrid assets for 3D visualization.",
                html.Div(
                    children=[
                        html.Button("Export Blender Bundle", id="export-button", className="btn primary"),
                        html.Div(id="export-status", className="status-text"),
                    ],
                ),
            ),
            html.Div(
                className="card-grid two-col",
                children=[
                    _card(
                        "Save Scenario",
                        "Persist the full pipeline state locally.",
                        html.Div(
                            children=[
                                _input_field(
                                    "Scenario Name",
                                    dcc.Input(
                                        id="scenario-name-input",
                                        type="text",
                                        placeholder="singapore_dc",
                                        className="text-input",
                                    ),
                                ),
                                html.Button("Save Scenario", id="save-scenario-button", className="btn"),
                                html.Div(id="save-scenario-status", className="status-text"),
                            ],
                        ),
                    ),
                    _card(
                        "Load Scenario",
                        "Reload a saved pipeline state for iteration.",
                        html.Div(
                            children=[
                                html.Div(
                                    [
                                        html.Span("Saved files", className="card-description"),
                                        dcc.Dropdown(
                                            id="scenario-file-dropdown",
                                            options=[],
                                            placeholder="scenario.json",
                                            className="dropdown-input",
                                        ),
                                    ]
                                ),
                                html.Div(
                                    "Select a saved file from the dropdown, then load.",
                                    className="card-description",
                                ),
                                html.Button("Load Scenario", id="load-scenario-button", className="btn primary"),
                                html.Div(id="load-scenario-status", className="status-text"),
                            ],
                        ),
                    ),
                ],
            ),
        ],
    )


def _ai_tab() -> html.Div:
    return html.Div(
        className="tab-pane",
        children=[
            html.Div(
                className="floragen-hero",
                children=[
                    html.H2("Floragen AI"),
                    html.P("Scenario-aware diagnostics powered by the Floral AI engine."),
                    html.Small("Configure a real LLM client inside floral_v1/ai_engine.py to replace the stub."),
                ],
            ),
            html.Div(
                className="card-grid two-col",
                children=[
                    _card(
                        "Scenario Snapshot",
                        "Key context passed to the AI engine.",
                        html.Div(id="ai-info-panel"),
                    ),
                    _card(
                        "Diagnostic Report",
                        "Auto-generated narrative after DES completes.",
                        html.Pre(id="ai-report-display", className="code-block tall"),
                    ),
                ],
            ),
            _card(
                "Ask Floragen",
                "Pose targeted questions about this scenario.",
                html.Div(
                    children=[
                        _input_field(
                            "Question",
                            dcc.Textarea(
                                id="ai-question-input",
                                placeholder="Where are the biggest reliability gaps?",
                                className="textarea-input",
                            ),
                        ),
                        html.Div(
                            className="button-row",
                            children=[
                                html.Button("Ask Floragen", id="ask-floragen-button", className="btn primary"),
                            ],
                        ),
                    ],
                ),
            ),
        ],
    )


def _card(title: str | None, subtitle: str | None, content, extra_class: str = "") -> html.Div:
    children = []
    if title or subtitle:
        children.append(
            html.Div(
                className="floral-card-header",
                children=[
                    html.H3(title) if title else None,
                    html.P(subtitle) if subtitle else None,
                ],
            )
        )
    children.append(html.Div(content, className="floral-card-body"))
    return html.Div(children=children, className=f"floral-card {extra_class}".strip())


def _input_field(label: str, control, description: str | None = None) -> html.Div:
    return html.Div(
        className="input-field",
        children=[
            html.Label(label),
            control,
            html.Small(description) if description else None,
        ],
    )


def _geometry_card() -> html.Div:
    if HAS_DASH_LEAFLET:
        geometry_control = dl.Map(
            id="site-geometry-map",
            center=[1.3521, 103.8198],
            zoom=4,
            style={"width": "100%", "height": "420px", "border-radius": "14px"},
            children=[
                dl.TileLayer(),
                dl.FeatureGroup(
                    children=[
                        dl.GeoJSON(
                            id="site-geometry-preview",
                            data={"type": "FeatureCollection", "features": []},
                        ),
                        dl.DrawControl(
                            id="geometry-draw-control",
                            draw={
                                "polyline": True,
                                "polygon": True,
                                "rectangle": False,
                                "circle": False,
                                "circlemarker": False,
                                "marker": True,
                            },
                            edit=True,
                            position="topleft",
                        ),
                    ]
                ),
            ],
        )
    else:
        geometry_control = html.Div(
            children=[
                html.Div(
                    [
                        html.P(
                            "dash-leaflet is not installed; enter GeoJSON manually or install the optional dependency.",
                            className="card-description",
                        ),
                        html.P(
                            "Install inside the active virtualenv: pip install dash-leaflet",
                            className="card-description",
                        ),
                    ]
                ),
                _input_field(
                    "Geometry JSON (FeatureCollection)",
                    dcc.Textarea(
                        id="geometry-json-input",
                        placeholder='{"boundary": {...}, "entrance": {...}, "gas_line": {...}}',
                        className="textarea-input",
                        spellCheck=False,
                    ),
                    "Provide GeoJSON for boundary (Polygon), entrance (Point), and gas_line (LineString).",
                ),
                html.Button("Load Geometry", id="geometry-json-button", className="btn"),
                html.Pre(id="site-geometry-preview", className="code-block"),
            ]
        )

    return _card(
        "Site Geometry",
        "Define the boundary polygon, entrance, and gas line.",
        html.Div(
            children=[
                html.Div(
                    "Use the interactive canvas when available or paste GeoJSON manually.",
                    className="card-description",
                ),
                geometry_control,
            ]
        ),
    )

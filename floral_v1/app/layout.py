from __future__ import annotations

from textwrap import dedent

from dash import dcc, html


def get_layout():
    return html.Div(
        className="floral-app",
        children=[
            html.Style(_GLOBAL_STYLES),
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
                "Define the fundamentals for your deployment.",
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
                                    "Target Load (MW)",
                                    dcc.Input(
                                        id="target-load-input",
                                        type="number",
                                        placeholder="10",
                                        className="text-input",
                                    ),
                                ),
                                _input_field(
                                    "Availability Target",
                                    dcc.Input(
                                        id="availability-target-input",
                                        type="number",
                                        placeholder="0.999",
                                        className="text-input",
                                    ),
                                ),
                                _input_field(
                                    "Genset Size (MW)",
                                    dcc.Input(
                                        id="genset-size-input",
                                        type="number",
                                        placeholder="2.5",
                                        className="text-input",
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
                                        placeholder="37.7749",
                                        className="text-input",
                                    ),
                                ),
                                _input_field(
                                    "Longitude",
                                    dcc.Input(
                                        id="longitude-input",
                                        type="number",
                                        placeholder="-122.4194",
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
                                    "PV Land (m²)",
                                    dcc.Input(
                                        id="pv-land-input",
                                        type="number",
                                        placeholder="100000",
                                        className="text-input",
                                    ),
                                ),
                            ],
                        ),
                    ],
                ),
            ),
            _card(
                "Load & Objectives",
                "Describe the expected demand shape and optimization priorities.",
                html.Div(
                    className="form-grid",
                    children=[
                        html.Div(
                            className="form-column full-width",
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
                        html.Div(
                            className="form-column two-col",
                            children=[
                                _input_field(
                                    "Objective Weight – LCOE",
                                    dcc.Input(
                                        id="objective-lcoe-input",
                                        type="number",
                                        placeholder="0.5",
                                        className="text-input",
                                    ),
                                ),
                                _input_field(
                                    "Objective Weight – Emissions",
                                    dcc.Input(
                                        id="objective-emissions-input",
                                        type="number",
                                        placeholder="0.5",
                                        className="text-input",
                                    ),
                                ),
                            ],
                        ),
                    ],
                ),
            ),
            _card(
                "Save Request & Size Gensets",
                "Persist the scenario before sizing and progressing downstream.",
                html.Div(
                    children=[
                        html.Div(
                            className="button-row",
                            children=[
                                html.Button("Save Request", id="save-request-button", className="btn primary"),
                                html.Button("Size Gensets", id="size-gensets-button", className="btn"),
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
                                        html.H4("Request Payload"),
                                        html.Pre(id="request-preview", className="code-block"),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
            ),
            _card(
                "Load Profile Preview",
                "Visual confirmation of the submitted load curve.",
                dcc.Graph(id="load-profile-graph", config={"displayModeBar": False}),
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


_GLOBAL_STYLES = dedent(
    """
    :root {
        --floral-bg: #0b1220;
        --floral-card: #151f32;
        --floral-card-border: rgba(255, 255, 255, 0.05);
        --floral-text: #e2e8f0;
        --floral-muted: #94a3b8;
        --floral-primary: #38bdf8;
        --floral-accent: #c084fc;
        --floral-card-shadow: 0 20px 45px rgba(2, 6, 23, 0.45);
        --floral-radius: 18px;
        --floral-font: "Inter", "SF Pro Display", "Segoe UI", -apple-system, BlinkMacSystemFont, sans-serif;
    }
    body {
        margin: 0;
        padding: 0;
        background-color: var(--floral-bg);
        font-family: var(--floral-font);
        color: var(--floral-text);
    }
    .floral-app {
        min-height: 100vh;
        background: radial-gradient(circle at top, rgba(56, 189, 248, 0.08), transparent 60%),
                    linear-gradient(180deg, rgba(15, 23, 42, 0.95), #05070f);
    }
    .app-shell {
        max-width: 1240px;
        margin: 0 auto;
        padding: 32px 24px 80px;
    }
    .app-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 24px 28px;
        border-radius: var(--floral-radius);
        background-color: rgba(15, 23, 42, 0.65);
        border: 1px solid rgba(255, 255, 255, 0.04);
        margin-bottom: 28px;
        backdrop-filter: blur(16px);
        box-shadow: var(--floral-card-shadow);
    }
    .brand {
        display: flex;
        align-items: center;
        gap: 14px;
    }
    .brand-mark {
        font-size: 32px;
        background: rgba(56, 189, 248, 0.15);
        padding: 12px;
        border-radius: 14px;
    }
    .header-meta {
        text-align: right;
        color: var(--floral-muted);
        font-size: 13px;
    }
    .app-content {
        background-color: rgba(15, 23, 42, 0.35);
        border-radius: var(--floral-radius);
        padding: 8px;
        border: 1px solid rgba(255, 255, 255, 0.04);
        box-shadow: var(--floral-card-shadow);
    }
    .floral-tabs {
        background-color: transparent;
        border-radius: var(--floral-radius);
    }
    .floral-tab {
        background-color: transparent !important;
        border: none !important;
        color: var(--floral-muted) !important;
        font-weight: 600;
    }
    .floral-tab--selected {
        background: rgba(56, 189, 248, 0.08) !important;
        color: var(--floral-text) !important;
        border-bottom: 2px solid var(--floral-primary) !important;
    }
    .tab-pane {
        padding: 24px;
        display: flex;
        flex-direction: column;
        gap: 24px;
    }
    .floral-card {
        background-color: var(--floral-card);
        border-radius: var(--floral-radius);
        padding: 20px 24px;
        border: 1px solid var(--floral-card-border);
        box-shadow: var(--floral-card-shadow);
    }
    .floral-card-header h3 {
        margin: 0;
        font-size: 20px;
    }
    .floral-card-header p {
        margin-top: 6px;
        color: var(--floral-muted);
        font-size: 14px;
    }
    .form-grid {
        display: grid;
        gap: 18px;
    }
    .form-grid.two-col {
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    }
    .form-column.full-width {
        grid-column: 1 / -1;
    }
    .form-column.two-col {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 16px;
    }
    .input-field {
        display: flex;
        flex-direction: column;
        gap: 6px;
        color: var(--floral-muted);
        font-size: 13px;
    }
    .input-field label {
        font-weight: 600;
        color: var(--floral-text);
    }
    .text-input, .textarea-input, .dropdown-input .Select-control {
        background-color: rgba(255, 255, 255, 0.04) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px;
        padding: 10px 12px;
        color: var(--floral-text);
    }
    .textarea-input {
        min-height: 120px;
        resize: vertical;
    }
    .btn {
        background: transparent;
        border: 1px solid rgba(255, 255, 255, 0.3);
        color: var(--floral-text);
        padding: 10px 18px;
        border-radius: 999px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    .btn.primary {
        background: linear-gradient(120deg, var(--floral-primary), var(--floral-accent));
        border: none;
        color: #0b1220;
        box-shadow: 0 10px 30px rgba(56, 189, 248, 0.35);
    }
    .btn:hover {
        transform: translateY(-1px);
    }
    .button-row {
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        margin-bottom: 20px;
    }
    .status-grid, .card-grid.two-col, .kpi-grid.two-col {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
        gap: 18px;
    }
    .status-card, .kpi-card {
        background-color: rgba(255, 255, 255, 0.02);
        border-radius: var(--floral-radius);
        padding: 16px;
        border: 1px solid rgba(255, 255, 255, 0.05);
        min-height: 140px;
    }
    .kpi-label {
        font-size: 13px;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--floral-muted);
    }
    .code-block {
        white-space: pre-wrap;
        word-break: break-word;
        background-color: rgba(0, 0, 0, 0.25);
        border-radius: 12px;
        padding: 12px;
        min-height: 80px;
        font-family: "JetBrains Mono", "SFMono-Regular", Consolas, monospace;
        font-size: 13px;
    }
    .code-block.tall {
        min-height: 220px;
        max-height: 360px;
        overflow-y: auto;
    }
    .status-text {
        color: var(--floral-muted);
        margin-top: 12px;
    }
    .floragen-hero {
        text-align: center;
        padding: 32px;
        border-radius: var(--floral-radius);
        background: linear-gradient(135deg, rgba(56, 189, 248, 0.2), rgba(124, 58, 237, 0.2));
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: var(--floral-card-shadow);
    }
    .card-description {
        color: var(--floral-muted);
        font-size: 14px;
        margin-bottom: 10px;
    }
    @media (max-width: 768px) {
        .app-header {
            flex-direction: column;
            gap: 16px;
            text-align: center;
        }
        .header-meta {
            text-align: center;
        }
    }
    """
)

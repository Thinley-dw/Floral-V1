from __future__ import annotations

from typing import Iterable, Optional

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from floral_v1.core.models import AvailabilityReport, HybridDesign, PlacementPlan, SimulationResult


FIG_BG = "#0b1220"
PLOT_BG = "#0f1a2c"
PALETTE = {
    "genset": "#fb7185",
    "pv": "#34d399",
    "bess": "#a78bfa",
    "load": "#38bdf8",
    "served": "#fde047",
    "unserved": "#f87171",
}


def _apply_theme(fig: go.Figure, title: Optional[str] = None) -> go.Figure:
    fig.update_layout(
        title=title,
        template="plotly_dark",
        paper_bgcolor=FIG_BG,
        plot_bgcolor=PLOT_BG,
        font={
            "family": "Inter, -apple-system, BlinkMacSystemFont, sans-serif",
            "color": "#e2e8f0",
        },
        margin={"l": 40, "r": 30, "t": 60, "b": 40},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
        },
    )
    fig.update_xaxes(
        showgrid=True,
        gridcolor="rgba(226, 232, 240, 0.15)",
        zerolinecolor="rgba(226, 232, 240, 0.2)",
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor="rgba(226, 232, 240, 0.15)",
        zerolinecolor="rgba(226, 232, 240, 0.2)",
    )
    return fig


def _empty_figure(title: str, message: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        x=0.5,
        y=0.5,
        showarrow=False,
        font={"size": 14, "color": "#94a3b8"},
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return _apply_theme(fig, title)


def load_profile_figure(load_profile_kw: Optional[Iterable[float]]) -> go.Figure:
    values = list(load_profile_kw or [])
    if not values:
        return _empty_figure("Load Profile", "No load profile available.")

    hours = list(range(len(values)))
    fig = go.Figure(
        data=[
            go.Scatter(
                x=hours,
                y=values,
                mode="lines+markers",
                name="Load (kW)",
            )
        ]
    )
    fig.update_layout(xaxis_title="Hour", yaxis_title="Power (kW)")
    return _apply_theme(fig, "Load Profile")


def hybrid_capacity_figure(hybrid: Optional[HybridDesign]) -> go.Figure:
    if not hybrid:
        return _empty_figure("Hybrid Assets", "Run optimization to view PV/BESS sizing.")

    labels = ["PV (kW)", "BESS Energy (MWh)", "BESS Power (MW)"]
    values = [
        max(hybrid.pv_capacity_kw, 0.0),
        max(hybrid.bess_energy_mwh, 0.0),
        max(hybrid.bess_power_mw, 0.0),
    ]
    fig = go.Figure(
        data=[
            go.Bar(x=labels, y=values, text=[f"{v:,.1f}" for v in values], textposition="auto")
        ]
    )
    fig.update_traces(
        marker_color=[PALETTE["pv"], PALETTE["bess"], "#fbbf24"],
        marker_line_color="rgba(15,23,42,0.6)",
        marker_line_width=1,
    )
    fig.update_layout(yaxis_title="Capacity")
    return _apply_theme(fig, "Hybrid Asset Summary")


def placement_map_figure(placement: Optional[PlacementPlan]) -> go.Figure:
    if not placement or not placement.asset_locations:
        return _empty_figure("Asset Placement", "Build the site to view placements.")

    names = []
    xs = []
    ys = []
    colors = []
    for name, data in placement.asset_locations.items():
        names.append(name)
        xs.append(float(data.get("x_m", 0.0)))
        ys.append(float(data.get("y_m", 0.0)))
        asset_type = data.get("type", "asset")
        colors.append(_asset_color(asset_type))

    fig = go.Figure(
        data=[
            go.Scatter(
                x=xs,
                y=ys,
                mode="markers+text",
                text=names,
                textposition="top center",
                marker={"size": 14, "color": colors, "line": {"color": "white", "width": 1}},
            )
        ]
    )
    fig.update_layout(xaxis_title="X (m)", yaxis_title="Y (m)")
    return _apply_theme(fig, "Asset Placement (meters)")


def _asset_color(asset_type: str) -> str:
    palette = {
        "genset": PALETTE["genset"],
        "bess": PALETTE["bess"],
        "pv": PALETTE["pv"],
    }
    return palette.get(asset_type.lower(), "#59A14F")


def availability_report_figure(
    report: Optional[AvailabilityReport], target: Optional[float] = None
) -> go.Figure:
    if not report:
        return _empty_figure("Analytical Availability", "Run availability analysis.")

    achieved_pct = report.achieved * 100.0
    target_pct = (target if target is not None else report.target) * 100.0
    fig = go.Figure(
        data=[
            go.Indicator(
                mode="gauge+number",
                value=achieved_pct,
                title={"text": "Analytical Availability (%)"},
                gauge={
                    "axis": {"range": [0, 100]},
                    "bar": {"color": PALETTE["pv"]},
                    "bgcolor": "rgba(255,255,255,0.05)",
                    "borderwidth": 0,
                    "threshold": {
                        "line": {"color": PALETTE["unserved"], "width": 4},
                        "thickness": 0.75,
                        "value": target_pct,
                    },
                },
            )
        ]
    )
    return _apply_theme(fig, "Analytical Availability")


def des_result_figure(result: Optional[SimulationResult]) -> go.Figure:
    if not result:
        return _empty_figure("DES Results", "Run the DES to view availability.")

    fig = make_subplots(
        cols=2,
        rows=1,
        column_widths=[0.5, 0.5],
        specs=[[{"type": "indicator"}, {"type": "bar"}]],
        subplot_titles=("Availability", "Reliability Impact"),
    )
    fig.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=result.availability * 100.0,
            title={"text": "Availability (%)"},
            gauge={"axis": {"range": [0, 100]}},
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Bar(
            x=["Outage Hours", "Unserved Energy (MWh)"],
            y=[result.outage_hours, result.unserved_energy_mwh],
            text=[f"{result.outage_hours:.2f}", f"{result.unserved_energy_mwh:.2f}"],
            textposition="auto",
            marker_color=[PALETTE["genset"], PALETTE["unserved"]],
        ),
        row=1,
        col=2,
    )
    fig.update_layout(showlegend=False)
    return _apply_theme(fig, "DES Results")


def des_energy_split_pie(result: Optional[SimulationResult]) -> go.Figure:
    if not result or not result.metadata:
        return _empty_figure("Energy Split", "Run DES to view energy allocation.")

    metadata = result.metadata
    slices = [
        ("CHP", float(metadata.get("energy_chp_mwh", 0.0))),
        ("PV", float(metadata.get("energy_pv_mwh", 0.0))),
        ("BESS", float(metadata.get("energy_bess_mwh", 0.0))),
        ("Unserved", float(metadata.get("energy_unserved_mwh", 0.0))),
    ]
    total = sum(value for _, value in slices)
    if total <= 1e-6:
        return _empty_figure("Energy Split", "No energy data available.")

    labels = [label for label, value in slices if value > 1e-6]
    values = [value for _, value in slices if value > 1e-6]
    color_map = {
        "CHP": PALETTE["genset"],
        "PV": PALETTE["pv"],
        "BESS": PALETTE["bess"],
        "Unserved": PALETTE["unserved"],
    }
    colors = [color_map.get(label, "#94a3b8") for label in labels]
    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.45,
                hoverinfo="label+percent",
                marker={"colors": colors},
            )
        ]
    )
    return _apply_theme(fig, "DES Energy Split")


def des_timeline_figure(result: Optional[SimulationResult]) -> go.Figure:
    if not result or not result.timeseries or not result.timeseries.get("hour"):
        return _empty_figure("DES Timeline", "Run DES to view timeline.")

    series = result.timeseries
    hours = series.get("hour", [])
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=hours, y=series.get("load_mw", []), name="Load", line={"color": PALETTE["load"]})
    )
    fig.add_trace(
        go.Scatter(
            x=hours,
            y=series.get("served_mw", []),
            name="Served",
            line={"color": PALETTE["served"]},
        )
    )
    fig.add_trace(
        go.Scatter(
            x=hours,
            y=series.get("chp_mw", []),
            name="CHP",
            line={"color": PALETTE["genset"]},
        )
    )
    fig.add_trace(
        go.Scatter(
            x=hours,
            y=series.get("pv_mw", []),
            name="PV",
            line={"color": PALETTE["pv"]},
        )
    )
    fig.add_trace(
        go.Scatter(
            x=hours,
            y=series.get("bess_mw", []),
            name="BESS Discharge",
            line={"color": PALETTE["bess"]},
        )
    )
    fig.add_trace(
        go.Scatter(
            x=hours,
            y=series.get("unserved_mw", []),
            name="Unserved",
            line={"color": PALETTE["unserved"]},
            fill="tozeroy",
            opacity=0.35,
        )
    )
    fig.update_layout(xaxis_title="Hour", yaxis_title="Power (MW)")
    return _apply_theme(fig, "DES Timeline")

from __future__ import annotations

from typing import Iterable, Optional

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from floral_v1.core.models import AvailabilityReport, HybridDesign, PlacementPlan, SimulationResult


def _empty_figure(title: str, message: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(title=title, template="plotly_white")
    fig.add_annotation(
        text=message,
        x=0.5,
        y=0.5,
        showarrow=False,
        font={"size": 14},
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return fig


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
    fig.update_layout(
        title="Load Profile",
        xaxis_title="Hour",
        yaxis_title="Power (kW)",
        template="plotly_white",
    )
    return fig


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
            go.Bar(
                x=labels,
                y=values,
                text=[f"{v:,.1f}" for v in values],
                textposition="auto",
                marker_color=["#2E86AB", "#F6C85F", "#6F4E7C"],
            )
        ]
    )
    fig.update_layout(
        title="Hybrid Asset Summary",
        yaxis_title="Capacity",
        template="plotly_white",
    )
    return fig


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
                marker={"size": 12, "color": colors},
            )
        ]
    )
    fig.update_layout(
        title="Asset Placement (meters)",
        xaxis_title="X (m)",
        yaxis_title="Y (m)",
        template="plotly_white",
    )
    return fig


def _asset_color(asset_type: str) -> str:
    palette = {
        "genset": "#E45756",
        "bess": "#4E79A7",
        "pv": "#76B7B2",
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
                    "threshold": {
                        "line": {"color": "#FF9F1C", "width": 4},
                        "thickness": 0.75,
                        "value": target_pct,
                    },
                },
            )
        ]
    )
    fig.update_layout(template="plotly_white")
    return fig


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
            marker_color=["#EDC948", "#FF9DA7"],
        ),
        row=1,
        col=2,
    )
    fig.update_layout(template="plotly_white", showlegend=False)
    return fig


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
    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.4,
                hoverinfo="label+percent",
            )
        ]
    )
    fig.update_layout(title="DES Energy Split", template="plotly_white")
    return fig


def des_timeline_figure(result: Optional[SimulationResult]) -> go.Figure:
    if not result or not result.timeseries or not result.timeseries.get("hour"):
        return _empty_figure("DES Timeline", "Run DES to view timeline.")

    series = result.timeseries
    hours = series.get("hour", [])
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=hours, y=series.get("load_mw", []), name="Load", line=dict(color="#1f77b4"))
    )
    fig.add_trace(
        go.Scatter(
            x=hours,
            y=series.get("served_mw", []),
            name="Served",
            line=dict(color="#2ca02c"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=hours,
            y=series.get("chp_mw", []),
            name="CHP",
            line=dict(color="#ff7f0e"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=hours,
            y=series.get("pv_mw", []),
            name="PV",
            line=dict(color="#bcbd22"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=hours,
            y=series.get("bess_mw", []),
            name="BESS Discharge",
            line=dict(color="#17becf"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=hours,
            y=series.get("unserved_mw", []),
            name="Unserved",
            line=dict(color="#d62728"),
            fill="tozeroy",
            opacity=0.3,
        )
    )
    fig.update_layout(
        title="DES Timeline",
        xaxis_title="Hour",
        yaxis_title="Power (MW)",
        template="plotly_white",
    )
    return fig

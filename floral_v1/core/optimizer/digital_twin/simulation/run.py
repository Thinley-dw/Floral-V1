from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from ..models.fleet_sizing import size_and_calculate
from ..models.g3520h_simple_derated import EKW_POINTS, derate_bilinear
from .bess_dispatch import (
    BessDispatchResult,
    BessParams,
    BessState,
    GensetState,
    update_bess_state,
)

TimeSeries = Sequence[Tuple[str, float]]


@dataclass
class SimulationSummary:
    hours_simulated: int = 0
    hours_infeasible: int = 0
    unserved_energy_kWh: float = 0.0
    total_site_energy_kWh: float = 0.0
    total_fuel_Btu: float = 0.0
    total_fuel_scf: float = 0.0
    total_CO2_kg: float = 0.0
    total_NOx_kg: float = 0.0
    max_engines: int = 0
    sum_active_gensets: float = 0.0
    peak_site_ekW: float = 0.0
    peak_site_timestamp: Optional[str] = None
    engine_runtime_hours: List[float] = field(default_factory=list)
    load_trace: List[float] = field(default_factory=list)
    pv_trace: List[float] = field(default_factory=list)
    genset_load_trace: List[float] = field(default_factory=list)
    bess_soc_trace: List[float] = field(default_factory=list)
    bess_discharge_trace: List[float] = field(default_factory=list)
    bess_charge_from_pv_trace: List[float] = field(default_factory=list)
    bess_charge_from_genset_trace: List[float] = field(default_factory=list)
    active_gensets_trace: List[int] = field(default_factory=list)


def run_hourly_simulation(
    loads: TimeSeries,
    pv_generation: Optional[TimeSeries] = None,
    temperatures: Optional[TimeSeries] = None,
    altitude_ft: float = 0.0,
    fuel_LHV_Btu_per_scf: float = 905.0,
    bess_params: Optional[Union[BessParams, Dict[str, Any]]] = None,
    initial_bess_soc_kwh: Optional[float] = None,
) -> SimulationSummary:
    """
    Dispatch gensets for each provided hour.

    Parameters
    ----------
    loads:
        Sequence of (timestamp, ekW demand) tuples. Only the value component is used
        for dispatch, but timestamps are propagated to the summary for reporting.
    temperatures:
        Optional sequence of (timestamp, degC) tuples aligned with the load series.
        If omitted, a flat 25 degC profile is assumed.
    pv_generation:
        Optional sequence of (timestamp, kW) PV generation aligned with the load
        series. If omitted, PV is treated as zero.
    bess_params:
        Optional BESS configuration. When provided, the BESS is dispatched once per
        hour and alters the net genset load.
    initial_bess_soc_kwh:
        Optional initial SoC for the BESS. Defaults to the minimum SoC if omitted.
    """

    load_series: List[Tuple[str, float]] = [(ts, float(val)) for ts, val in loads]
    temp_series: Optional[List[Tuple[str, float]]] = None
    if temperatures is not None:
        temp_series = [(ts, float(val)) for ts, val in temperatures]
    pv_series: List[float] = []
    if pv_generation is not None:
        pv_series = [float(val) for _, val in pv_generation]

    n_hours = len(load_series)
    summary = SimulationSummary(hours_simulated=n_hours)
    bess_config: Optional[BessParams] = None
    bess_state: Optional[BessState] = None
    if bess_params is not None:
        bess_config = bess_params if isinstance(bess_params, BessParams) else BessParams(**bess_params)
        start_soc = initial_bess_soc_kwh
        if start_soc is None:
            start_soc = bess_config.min_soc_fraction * bess_config.capacity_kwh
        bess_state = BessState(soc_kwh=float(start_soc))

    for idx in range(n_hours):
        ts, total_ekW = load_series[idx]
        ambient_C = temp_series[idx][1] if temp_series is not None and idx < len(temp_series) else 25.0
        pv_kw = pv_series[idx] if idx < len(pv_series) else 0.0

        bess_dispatch: Optional[BessDispatchResult] = None
        genset_load_kw = max(total_ekW - pv_kw, 0.0)
        if bess_config is not None and bess_state is not None:
            derate_factor = derate_bilinear(ambient_C * 9 / 5 + 32, altitude_ft)
            per_unit_max = derate_factor * EKW_POINTS[-1]
            genset_state = GensetState(per_unit_max_kw=per_unit_max, genset_rating_kw=EKW_POINTS[-1])
            bess_dispatch = update_bess_state(
                load_kw=total_ekW,
                pv_kw=pv_kw,
                genset_state=genset_state,
                bess_state=bess_state,
                params=bess_config,
            )
            genset_load_kw = max(total_ekW - pv_kw - bess_dispatch.bess_discharge_kw, 0.0)
            genset_load_kw += bess_dispatch.bess_charge_from_genset_kw
            summary.bess_soc_trace.append(bess_dispatch.soc_kwh)
            summary.bess_discharge_trace.append(bess_dispatch.bess_discharge_kw)
            summary.bess_charge_from_pv_trace.append(bess_dispatch.bess_charge_from_pv_kw)
            summary.bess_charge_from_genset_trace.append(bess_dispatch.bess_charge_from_genset_kw)

        summary.load_trace.append(total_ekW)
        summary.pv_trace.append(pv_kw)
        summary.genset_load_trace.append(genset_load_kw)

        results: Dict[str, Any] = size_and_calculate(
            total_ekW=genset_load_kw,
            ambient_C=ambient_C,
            altitude_ft=altitude_ft,
            fuel_LHV_Btu_per_scf=fuel_LHV_Btu_per_scf,
        )

        per_unit = results.get("per_unit", [])
        totals = results.get("totals", {})

        active_units = len(per_unit)
        summary.active_gensets_trace.append(active_units)

        if not per_unit or not totals:
            if genset_load_kw <= 1e-6:
                continue  # treat zero-load hours as satisfied without gensets
            summary.hours_infeasible += 1
            summary.unserved_energy_kWh += genset_load_kw
            continue

        if active_units > len(summary.engine_runtime_hours):
            summary.engine_runtime_hours.extend([0.0] * (active_units - len(summary.engine_runtime_hours)))
        for engine_idx in range(active_units):
            summary.engine_runtime_hours[engine_idx] += 1.0

        summary.sum_active_gensets += active_units
        summary.total_site_energy_kWh += totals["site_ekW"]
        summary.total_fuel_Btu += totals["fuel_Btu_per_hr"]
        summary.total_fuel_scf += totals["fuel_scf_per_hr"]
        summary.total_CO2_kg += totals["CO2_kg_per_hr"]
        summary.total_NOx_kg += totals["NOx_kg_per_hr"]

        if totals["site_ekW"] > summary.peak_site_ekW:
            summary.peak_site_ekW = totals["site_ekW"]
            summary.peak_site_timestamp = ts

        summary.max_engines = max(summary.max_engines, len(summary.engine_runtime_hours))

    return summary


def print_summary(summary: SimulationSummary) -> None:
    served_hours = max(summary.hours_simulated - summary.hours_infeasible, 0)
    avg_gensets = summary.sum_active_gensets / served_hours if served_hours else 0.0

    print(f"Simulated {summary.hours_simulated} hourly steps.")
    if summary.hours_infeasible:
        infeasible_pct = summary.hours_infeasible / summary.hours_simulated * 100.0
        print(f"  Infeasible hours: {summary.hours_infeasible} ({infeasible_pct:.2f}%)")
        print(f"  Unserved energy: {summary.unserved_energy_kWh / 1000.0:.2f} MWh")
    print(f"Peak delivered load: {summary.peak_site_ekW / 1000.0:.2f} MW at {summary.peak_site_timestamp}")
    print(f"Max gensets required: {summary.max_engines}")
    print(f"Average gensets online (served hours): {avg_gensets:.2f}")
    print("Totals across served load:")
    print(f"  Energy delivered: {summary.total_site_energy_kWh / 1000.0:.2f} MWh")
    print(f"  Fuel: {summary.total_fuel_scf:.0f} scf  |  {summary.total_fuel_Btu / 1e9:.2f} GBTU")
    print(f"  CO2: {summary.total_CO2_kg / 1000.0:.2f} metric tons")
    print(f"  NOx: {summary.total_NOx_kg / 1000.0:.3f} metric tons")
    if summary.engine_runtime_hours:
        print("Engine runtime hours:")
        for idx, hours in enumerate(summary.engine_runtime_hours, start=1):
            print(f"  Engine {idx:02d}: {hours:.0f} h")

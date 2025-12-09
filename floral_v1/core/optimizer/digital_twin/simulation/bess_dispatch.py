from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Optional


@dataclass
class BessParams:
    capacity_kwh: float
    max_charge_kw: Optional[float] = None
    max_discharge_kw: Optional[float] = None
    min_soc_fraction: float = 0.10
    primary_reserve_kwh: float = 5000.0
    charge_efficiency: float = 1.0
    discharge_efficiency: float = 1.0


@dataclass
class BessState:
    soc_kwh: float


@dataclass
class GensetState:
    per_unit_max_kw: float
    genset_rating_kw: float


@dataclass
class BessDispatchResult:
    bess_discharge_kw: float
    bess_charge_from_pv_kw: float
    bess_charge_from_genset_kw: float
    soc_kwh: float


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(value, upper))


def update_bess_state(
    load_kw: float,
    pv_kw: float,
    genset_state: GensetState,
    bess_state: BessState,
    params: BessParams,
) -> BessDispatchResult:
    """
    Advance the BESS by one hour using the provided dispatch rules.

    The priority order is enforced as:
      1) Honor the hard 10% SoC floor.
      2) Recharge to the primary reserve (10% + 5 MWh) using PV first, then gensets.
      3) Primary discharge to cover small residuals (< 40% of a genset).
      4) Secondary discharge to allow one genset to turn off; only energy above the
         primary reserve can be used here.
    """

    soc = _clamp(bess_state.soc_kwh, 0.0, params.capacity_kwh)
    min_soc = params.min_soc_fraction * params.capacity_kwh
    primary_target = min(params.capacity_kwh, min_soc + params.primary_reserve_kwh)
    max_charge_kw = params.max_charge_kw if params.max_charge_kw is not None else params.capacity_kwh
    max_discharge_kw = params.max_discharge_kw if params.max_discharge_kw is not None else params.capacity_kwh

    residual = load_kw - pv_kw  # positive when load exceeds PV
    pv_surplus_kw = max(-residual, 0.0)

    charge_from_pv_kw = 0.0
    charge_from_genset_kw = 0.0
    bess_discharge_kw = 0.0

    if params.charge_efficiency <= 0 or params.discharge_efficiency <= 0:
        raise ValueError("Charge/discharge efficiency must be positive.")

    if pv_surplus_kw > 0:
        charge_room_kw = (params.capacity_kwh - soc) / params.charge_efficiency
        charge_from_pv_kw = min(pv_surplus_kw, charge_room_kw, max_charge_kw)
        if charge_from_pv_kw > 0:
            soc += charge_from_pv_kw * params.charge_efficiency
            pv_surplus_kw = max(pv_surplus_kw - charge_from_pv_kw, 0.0)

    if soc < primary_target:
        target_gap_kw = (primary_target - soc) / params.charge_efficiency
        charge_room_kw = (params.capacity_kwh - soc) / params.charge_efficiency
        charge_from_genset_kw = min(target_gap_kw, charge_room_kw, max_charge_kw)
        if charge_from_genset_kw > 0:
            soc += charge_from_genset_kw * params.charge_efficiency

    available_discharge_kwh = max(soc - min_soc, 0.0)
    discharge_limit_kw = min(max_discharge_kw, available_discharge_kwh / params.discharge_efficiency)
    primary_threshold_kw = 0.4 * genset_state.genset_rating_kw

    potential_units = (
        ceil(residual / genset_state.per_unit_max_kw) if genset_state.per_unit_max_kw > 0 and residual > 0 else 0
    )

    if 0 < residual < primary_threshold_kw and discharge_limit_kw > 0 and potential_units <= 1:
        primary_kw = min(residual, discharge_limit_kw)
        bess_discharge_kw += primary_kw
        soc -= primary_kw / params.discharge_efficiency
        available_discharge_kwh = max(soc - min_soc, 0.0)
        discharge_limit_kw = min(max_discharge_kw, available_discharge_kwh / params.discharge_efficiency)

    base_genset_load_kw = max(residual - bess_discharge_kw, 0.0) + charge_from_genset_kw
    units_needed = ceil(base_genset_load_kw / genset_state.per_unit_max_kw) if genset_state.per_unit_max_kw > 0 else 0

    if (
        units_needed > 1
        and soc > primary_target
        and discharge_limit_kw > 0
    ):
        max_load_with_less_units = (units_needed - 1) * genset_state.per_unit_max_kw
        min_load_with_less_units = 0.5 * (units_needed - 1) * genset_state.per_unit_max_kw
        target_load_kw = min(base_genset_load_kw, max_load_with_less_units)
        target_load_kw = max(target_load_kw, min_load_with_less_units)
        discharge_needed_kw = max(base_genset_load_kw - target_load_kw, 0.0)
        available_secondary_kw = min(
            discharge_limit_kw,
            max(0.0, (soc - primary_target) / params.discharge_efficiency),
            discharge_needed_kw,
        )
        if available_secondary_kw > 0:
            bess_discharge_kw += available_secondary_kw
            soc -= available_secondary_kw / params.discharge_efficiency

    soc = _clamp(soc, min_soc, params.capacity_kwh)
    bess_state.soc_kwh = soc

    return BessDispatchResult(
        bess_discharge_kw=bess_discharge_kw,
        bess_charge_from_pv_kw=charge_from_pv_kw,
        bess_charge_from_genset_kw=charge_from_genset_kw,
        soc_kwh=soc,
    )

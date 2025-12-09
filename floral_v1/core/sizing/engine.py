from __future__ import annotations

from math import ceil, comb

from floral_v1.core.models import GensetDesign, UserRequest
from floral_v1.logging_config import get_logger

# Defaults derived from AvailabilityDesigner.py
DEFAULT_CHP_SIZE_MW = 2.5
MTBF_CHP = 12000
logger = get_logger(__name__)


def estimate_chp_availability() -> float:
    """Estimate single-CHP availability using the MTTR mix from the legacy model."""
    minor_mean = (8 + 24) / 2
    moderate_mean = (120 + 300) / 2
    major_mean = (600 + 1000) / 2
    expected_mttr = 0.4 * minor_mean + 0.3 * moderate_mean + 0.3 * major_mean
    return MTBF_CHP / (MTBF_CHP + expected_mttr)


def k_out_of_n_availability(n: int, k: int, availability: float) -> float:
    """Instantaneous k-out-of-n availability for identical components."""
    if k > n:
        return 0.0
    return sum(
        comb(n, i) * (availability**i) * ((1 - availability) ** (n - i))
        for i in range(k, n + 1)
    )


def size_chp_fleet(target_load_mw: float, target_availability: float, chp_size_mw: float) -> tuple[int, int]:
    """
    Mirror of AvailabilityDesigner sizing routine that searches for a k-out-of-n solution.
    """
    if target_load_mw <= 0:
        raise ValueError("Target load must be positive.")
    if chp_size_mw <= 0:
        raise ValueError("CHP size must be positive.")

    k = int(ceil(target_load_mw / chp_size_mw))
    engine_availability = estimate_chp_availability()
    n = max(k + 2, k)
    while (
        k_out_of_n_availability(n, k, engine_availability) < target_availability
        and n < 200
    ):
        n += 1
    return k, n


def size_gensets(request: UserRequest) -> GensetDesign:
    """
    Availability-driven genset sizing derived from AvailabilityDesigner.py.
    """
    logger.info(
        "Sizing gensets for project %s | target_load=%.2f MW availability_target=%.4f",
        request.project_name,
        request.target_load_mw,
        request.availability_target,
    )
    try:
        chp_size = request.genset_size_mw or DEFAULT_CHP_SIZE_MW
        required_units, installed_units = size_chp_fleet(
            request.target_load_mw, request.availability_target, chp_size
        )
        expected_availability = k_out_of_n_availability(
            installed_units, required_units, estimate_chp_availability()
        )
        notes = (
            f"Derived using AvailabilityDesigner logic with {chp_size:.2f} MW engines."
        )
        design = GensetDesign(
            required_units=required_units,
            installed_units=installed_units,
            per_unit_mw=chp_size,
            expected_availability=expected_availability,
            notes=notes,
        )
        logger.info(
            "Sized gensets: required=%d installed=%d per_unit=%.2f expected_avail=%.4f",
            design.required_units,
            design.installed_units,
            design.per_unit_mw,
            design.expected_availability,
        )
        return design
    except Exception:
        logger.exception("Failed to size gensets for project %s", request.project_name)
        raise

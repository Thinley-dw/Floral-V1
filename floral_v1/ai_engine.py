from __future__ import annotations

from typing import Dict, List, Optional

from floral_v1.core.models import (
    AvailabilityReport,
    GensetDesign,
    HybridDesign,
    PlacementPlan,
    SimulationConfig,
    SimulationResult,
    SiteModel,
    UserRequest,
)


def simulation_config_from_metadata(metadata: Optional[Dict[str, float]]) -> Optional[SimulationConfig]:
    """Best-effort reconstruction of SimulationConfig from DES metadata."""
    if not metadata:
        return None
    hours_raw = metadata.get("sim_hours") if isinstance(metadata, dict) else None
    mode = metadata.get("des_mode") if isinstance(metadata, dict) else None
    seed_raw = metadata.get("sim_seed") if isinstance(metadata, dict) else None
    has_any = any(val is not None for val in (hours_raw, mode, seed_raw))
    if not has_any:
        return None
    hours = int(hours_raw) if hours_raw not in (None, "") else 0
    seed = int(seed_raw) if seed_raw not in (None, "") else None
    return SimulationConfig(hours=hours or 0, seed=seed, mode=str(mode or "stochastic"))


def build_ai_context(
    request: Optional[UserRequest],
    site: Optional[SiteModel],
    gensets: Optional[GensetDesign],
    placement: Optional[PlacementPlan],
    hybrid: Optional[HybridDesign],
    availability: Optional[AvailabilityReport],
    des_config: Optional[SimulationConfig],
    des_result: Optional[SimulationResult],
) -> str:
    """Construct a structured textual context describing the current scenario."""

    sections: List[str] = []

    def add_section(title: str, lines: List[str]) -> None:
        if not lines:
            return
        body = "\n".join(lines)
        sections.append(f"{title}\n{body}")

    if request:
        proj_lines = [
            f"Project: {request.project_name}",
            f"Target load: {request.target_load_mw:.2f} MW",
            f"Availability target: {request.availability_target:.5f}",
        ]
        if request.site:
            proj_lines.append(
                f"Location: lat {request.site.latitude:.4f}, lon {request.site.longitude:.4f}"
            )
        if request.objectives:
            proj_lines.append(f"Objectives: {request.objectives}")
        add_section("Project Overview", proj_lines)

    if gensets:
        add_section(
            "Genset Sizing",
            [
                f"Required units: {gensets.required_units}",
                f"Installed units: {gensets.installed_units}",
                f"Per-unit rating: {gensets.per_unit_mw:.2f} MW",
                f"Expected availability: {gensets.expected_availability:.5f}",
            ],
        )

    if hybrid:
        hybrid_lines = [
            f"PV capacity: {hybrid.pv_capacity_kw:.1f} kW",
            f"BESS energy: {hybrid.bess_energy_mwh:.2f} MWh",
            f"BESS power: {hybrid.bess_power_mw:.2f} MW",
        ]
        if hybrid.metadata:
            hybrid_lines.append(f"Optimizer notes: {hybrid.metadata}")
        add_section("Hybrid Design", hybrid_lines)

    if availability:
        add_section(
            "Analytical Availability",
            [
                f"Achieved: {availability.achieved:.5f}",
                f"Target: {availability.target:.5f}",
                f"Meets target: {availability.meets_target}",
            ],
        )

    if des_config:
        cfg_lines = [
            f"Mode: {des_config.mode}",
            f"Simulation hours: {des_config.hours}",
        ]
        if des_config.seed is not None:
            cfg_lines.append(f"Seed: {des_config.seed}")
        add_section("DES Configuration", cfg_lines)

    if des_result:
        meta = des_result.metadata or {}
        energy_lines = [
            f"Availability: {des_result.availability:.5f}",
            f"Outage hours: {des_result.outage_hours:.2f}",
            f"Unserved energy: {des_result.unserved_energy_mwh:.3f} MWh",
        ]
        energy_lines.append(
            "Energy split (MWh): CHP={:.2f}, PV={:.2f}, BESS={:.2f}, Unserved={:.2f}".format(
                float(meta.get("energy_chp_mwh", 0.0)),
                float(meta.get("energy_pv_mwh", 0.0)),
                float(meta.get("energy_bess_mwh", 0.0)),
                float(meta.get("energy_unserved_mwh", 0.0)),
            )
        )
        add_section("DES Results", energy_lines)

    if not sections:
        return "No scenario data available. Run the pipeline first."
    return "\n\n".join(sections)


def generate_ai_response(
    context: str,
    question: Optional[str] = None,
    model: Optional[str] = None,
) -> str:
    """Stubbed AI response generator (replace with real LLM integration later)."""

    if not context.strip():
        return "AI Engine (stub): No context available. Run the full pipeline and DES first."

    prompt_parts = [
        "System: You are an expert microgrid reliability analyst. Review the scenario context and provide concise insights.",
        f"Context:\n{context}",
    ]
    if question:
        prompt_parts.append(f"User question: {question.strip()}")

    prompt = "\n\n".join(prompt_parts)

    # Placeholder response. Integrate a real LLM by sending `prompt` to your provider of choice.
    response_lines = [
        "AI Engine (stub): This is where a real AI model would analyze the scenario.",
        "Key observations:",
        "1. Review the project and genset sizing to ensure availability targets are feasible.",
        "2. Compare analytical availability vs DES availability to highlight gaps.",
        "3. Examine energy splits to understand CHP/PV/BESS contributions and any unserved energy.",
    ]
    if question:
        response_lines.append(f"User question echoed for reference: '{question.strip()}'")
    response_lines.append("(To enable live AI responses, update floral_v1/ai_engine.py to call your LLM API.)")

    return "\n".join(response_lines)

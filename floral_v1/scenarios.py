from __future__ import annotations

import json
from dataclasses import is_dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from floral_v1.app.state import (
    availability_report_from_store,
    genset_design_from_store,
    hybrid_design_from_store,
    placement_plan_from_store,
    serialize_dataclass,
    simulation_result_from_store,
    site_model_from_store,
    user_request_from_store,
)
from floral_v1.core.models import SimulationConfig
DEFAULT_SCENARIO_DIR = Path(__file__).resolve().parents[1] / "exports" / "scenarios"

SCENARIO_FIELDS = {
    "user_request": user_request_from_store,
    "site_model": site_model_from_store,
    "genset_design": genset_design_from_store,
    "placement_plan": placement_plan_from_store,
    "hybrid_design": hybrid_design_from_store,
    "availability_report": availability_report_from_store,
    "simulation_result": simulation_result_from_store,
    "des_config": lambda data: SimulationConfig(
        hours=int(data.get("hours", 0) or 0),
        seed=data.get("seed"),
        mode=data.get("mode", "stochastic"),
        schedule=data.get("schedule"),
    ),
}


def _resolve_path(path: str | Path) -> Path:
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = DEFAULT_SCENARIO_DIR / candidate
    candidate.parent.mkdir(parents=True, exist_ok=True)
    return candidate.resolve()


def _serialize_value(value: Any) -> Optional[Dict[str, Any]]:
    if value is None:
        return None
    if is_dataclass(value):
        return serialize_dataclass(value)
    if isinstance(value, dict):
        return value
    raise TypeError(f"Unsupported scenario payload type: {type(value).__name__}")


def save_scenario(path: str | Path, data: Dict[str, Any]) -> Path:
    payload: Dict[str, Any] = {}
    for field in SCENARIO_FIELDS:
        payload[field] = _serialize_value(data.get(field))
    payload["metadata"] = {
        "path": str(path),
    }
    destination = _resolve_path(path)
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return destination


def load_scenario(path: str | Path) -> Dict[str, Any]:
    source = _resolve_path(path)
    if not source.exists():
        raise FileNotFoundError(f"Scenario file not found: {source}")
    payload = json.loads(source.read_text(encoding="utf-8"))
    result: Dict[str, Any] = {}
    for field, parser in SCENARIO_FIELDS.items():
        section = payload.get(field)
        if section:
            result[field] = parser(section)
        else:
            result[field] = None
    return result


def list_scenarios(directory: str | Path | None = None) -> List[Path]:
    base = Path(directory).expanduser() if directory else DEFAULT_SCENARIO_DIR
    if not base.exists():
        return []
    return sorted(base.glob("*.json"))


def scenario_dict_from_outputs(outputs: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "user_request": outputs.get("request"),
        "site_model": outputs.get("site_model"),
        "genset_design": outputs.get("gensets"),
        "placement_plan": outputs.get("placement"),
        "hybrid_design": outputs.get("hybrid"),
        "availability_report": outputs.get("availability"),
        "simulation_result": outputs.get("simulation"),
        "des_config": outputs.get("des_config"),
    }


def outputs_from_scenario_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "request": data.get("user_request"),
        "site_model": data.get("site_model"),
        "gensets": data.get("genset_design"),
        "placement": data.get("placement_plan"),
        "hybrid": data.get("hybrid_design"),
        "availability": data.get("availability_report"),
        "simulation": data.get("simulation_result"),
        "des_config": data.get("des_config"),
    }

from __future__ import annotations

import argparse
from typing import List, Optional

from floral_v1.ai_engine import build_ai_context, generate_ai_response
from floral_v1.logging_config import get_logger
from floral_v1.scenarios import (
    load_scenario,
    outputs_from_scenario_dict,
    save_scenario,
    scenario_dict_from_outputs,
)
from floral_v1.scripts import smoke_pipeline

logger = get_logger(__name__)


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        prog="floral-smoke",
        description="Run integrated smoke scenarios (demo, small, large).",
    )
    parser.add_argument(
        "scenario",
        nargs="?",
        default="demo",
        choices=list(smoke_pipeline.SCENARIOS.keys()),
        help="Scenario to run (default: demo)",
    )
    parser.add_argument(
        "--save",
        help="Optional path to save the scenario JSON after running.",
    )
    parser.add_argument(
        "--load",
        help="Load an existing scenario JSON instead of running a pipeline.",
    )
    parser.add_argument(
        "--ai-diagnostic",
        action="store_true",
        help="Print the Floragen AI diagnostic after the scenario completes.",
    )
    args = parser.parse_args(argv)
    if args.load:
        logger.info("Loading scenario from %s", args.load)
        try:
            data = load_scenario(args.load)
            outputs = outputs_from_scenario_dict(data)
            smoke_pipeline.summarize_outputs("loaded", outputs)
            if args.ai_diagnostic:
                _print_ai_diagnostic(outputs)
            logger.info("Scenario %s loaded", args.load)
        except Exception:
            logger.exception("Failed to load scenario %s", args.load)
            raise
        return

    logger.info("Starting floral-smoke scenario=%s", args.scenario)
    try:
        outputs = smoke_pipeline.run_named_scenario(args.scenario)
        if args.save:
            scenario_payload = scenario_dict_from_outputs(outputs)
            destination = save_scenario(args.save, scenario_payload)
            logger.info("Scenario saved to %s", destination)
        if args.ai_diagnostic:
            _print_ai_diagnostic(outputs)
        logger.info("Scenario %s completed", args.scenario)
    except Exception:
        logger.exception("Scenario %s failed", args.scenario)
        raise


def _print_ai_diagnostic(outputs: dict) -> None:
    context = build_ai_context(
        outputs.get("request"),
        outputs.get("site_model"),
        outputs.get("gensets"),
        outputs.get("placement"),
        outputs.get("hybrid"),
        outputs.get("availability"),
        outputs.get("des_config"),
        outputs.get("simulation"),
    )
    response = generate_ai_response(context)
    print("\n--- Floragen AI Diagnostic (stub) ---")
    print(response)


if __name__ == "__main__":
    main()

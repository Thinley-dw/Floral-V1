from __future__ import annotations

import argparse
from typing import List, Optional

from floral_v1.app.app import create_app
from floral_v1.logging_config import get_logger

logger = get_logger(__name__)


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        prog="floral-dash", description="Launch the Floral V1 Dash interface."
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host interface (default 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8050, help="Port to bind (default 8050)")
    parser.add_argument("--debug", action="store_true", help="Enable Dash debug mode")
    args = parser.parse_args(argv)

    logger.info(
        "Launching Dash app host=%s port=%d debug=%s",
        args.host,
        args.port,
        args.debug,
    )
    try:
        app = create_app()
        app.run(host=args.host, port=args.port, debug=args.debug)
    except Exception:
        logger.exception("Dash app crashed")
        raise


if __name__ == "__main__":
    main()

from __future__ import annotations

import logging
import os
from typing import Optional

_CONFIGURED = False


def _determine_level() -> int:
    env_level = os.getenv("FLORAL_LOG_LEVEL", "").upper()
    if env_level == "DEBUG":
        return logging.DEBUG
    return logging.INFO


def configure_logging(level: Optional[int] = None) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    logging.basicConfig(
        level=level or _determine_level(),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)

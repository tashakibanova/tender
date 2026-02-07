"""Logging configuration for local audit trail."""

from __future__ import annotations

import logging
from pathlib import Path


def setup_logging(base_path: Path) -> None:
    log_path = base_path / "data" / "audit.log"
    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

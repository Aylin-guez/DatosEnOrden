"""Explicit QA-only locations for private test artifacts.

Private release packages must never be inferred from the public repository
layout or incorporated into a release candidate.
"""

from __future__ import annotations

import os
from pathlib import Path


CERTIFIED_DATA_PACKAGE_ENV = "DEO_QA_CERTIFIED_DATA_PACKAGE"


def certified_data_package_path() -> Path:
    """Return the explicitly configured, read-only certified QA package."""
    configured = os.getenv(CERTIFIED_DATA_PACKAGE_ENV, "")
    if not configured:
        raise RuntimeError(
            f"{CERTIFIED_DATA_PACKAGE_ENV} must point to a readable QA-only "
            "certified production package"
        )
    package = Path(configured)
    if not package.is_file():
        raise RuntimeError(
            f"{CERTIFIED_DATA_PACKAGE_ENV} does not point to a readable file"
        )
    return package

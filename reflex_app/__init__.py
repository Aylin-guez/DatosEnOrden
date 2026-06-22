"""Minimal Reflex prototype for DatosEnOrden."""

from __future__ import annotations

import sys
from pathlib import Path

_SRC_DIR = Path(__file__).resolve().parent.parent / "src"
_SRC_TEXT = str(_SRC_DIR)

if _SRC_DIR.exists() and _SRC_TEXT not in sys.path:
    sys.path.insert(0, _SRC_TEXT)

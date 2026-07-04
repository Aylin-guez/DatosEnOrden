from __future__ import annotations

from pathlib import Path
from typing import Sequence
import argparse
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from datosenorden.web.app_services import export_investigation_report
from datosenorden.web.app_services import resolve_investigation_target


MAIN_ENTITY = "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export the public demo citizen investigation report.")
    parser.add_argument("--target", default=MAIN_ENTITY, help="Canonical name, UUID, or related record id.")
    args = parser.parse_args(argv)

    resolved = resolve_investigation_target(args.target)
    if not resolved.get("found"):
        print(f"FAIL - target did not resolve: {resolved.get('warning', '')}", file=sys.stderr)
        return 1

    entity_id = str(resolved["entity_id"])
    output_path = export_investigation_report(entity_id)
    print(f"exported: {output_path}")
    print(f"entity: {resolved.get('entity_name', '')}")
    print(f"entity_id: {entity_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

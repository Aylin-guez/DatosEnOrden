from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from datosenorden.maintenance.platform_config import DEFAULT_PLATFORM_CONFIG_PATH
from datosenorden.maintenance.platform_config import load_platform_config
from datosenorden.maintenance.platform_config import summarize_platform_config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print a DatosEnOrden platform configuration summary.")
    parser.add_argument("path", nargs="?", default=str(DEFAULT_PLATFORM_CONFIG_PATH))
    args = parser.parse_args(argv)

    summary = summarize_platform_config(load_platform_config(args.path))
    print("platform_config_summary:")
    print(f"  nombre={summary['name']}")
    print("  vocabulario principal:")
    for key, value in summary["vocabulary"].items():
        print(f"    - {key}: {value}")
    print("  entidades:")
    for item in summary["entities"]:
        print(f"    - {item['id']}: {item['label']}")
    print("  relaciones:")
    for item in summary["relationships"]:
        print(f"    - {item['id']}: {item['label']}")
    print("  workflows:")
    for workflow in summary["workflows"]:
        states = ", ".join(state["id"] for state in workflow["states"])
        print(f"    - {workflow['id']}: {states}")
    print("  audiencias:")
    for item in summary["audiences"]:
        print(f"    - {item['id']}: {item['label']}")
    print("  templates:")
    for item in summary["templates"]:
        print(f"    - {item['id']}: {item['format']} / {item['audience_id']}")
    print("  features:")
    for key, value in summary["features"].items():
        print(f"    - {key}: {value}")
    if summary["validation_errors"]:
        print("  validation_errors:")
        for error in summary["validation_errors"]:
            print(f"    - {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

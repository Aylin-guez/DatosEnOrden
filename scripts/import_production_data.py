from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from datosenorden.application.data_release.importer import (  # noqa: E402
    TargetExpectation,
    import_package,
    verify_package,
)
from datosenorden.core.config import get_settings  # noqa: E402
from datosenorden.db.session import build_engine  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import a verified production data package.")
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--expected-database", required=True)
    parser.add_argument(
        "--target-environment",
        choices=("isolated-test", "production"),
        required=True,
    )
    parser.add_argument("--code-release", required=True)
    parser.add_argument("--confirm-production")
    args = parser.parse_args(argv)
    package = verify_package(args.package, expected_sha256=args.sha256)
    expectation = TargetExpectation(
        database_name=args.expected_database,
        environment=args.target_environment,
        code_release=args.code_release,
        production_confirmation=args.confirm_production,
    )
    result = import_package(
        build_engine(get_settings().database_url),
        package,
        expectation=expectation,
    )
    print(
        json.dumps(
            {
                "imported_at": result.imported_at,
                "inserted": result.inserted,
                "package_id": result.package_id,
                "public_metrics": result.public_metrics,
                "target_counts": result.target_counts,
                "unchanged": result.unchanged,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

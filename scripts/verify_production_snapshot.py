from __future__ import annotations

# ruff: noqa: E402, I001 -- deployment scripts add the repository src path before imports.

import argparse
import json
import sys
from pathlib import Path

from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from datosenorden.application.data_release.exporter import (
    build_serialized_public_release_rows,  # noqa: E402
)
from datosenorden.application.data_release.importer import verify_package  # noqa: E402
from datosenorden.application.data_release.materialization import (
    APPROVED_REAL_EXPEDIENT_IDS,  # noqa: E402
)
from datosenorden.core.config import get_settings  # noqa: E402
from datosenorden.db.session import build_engine  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify a restored production snapshot exactly.")
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--expected-database", required=True)
    parser.add_argument("--code-release", required=True)
    args = parser.parse_args(argv)
    package = verify_package(args.package, expected_sha256=args.sha256)
    allowed = package.manifest["code_compatibility"]["compatible_code_releases"]
    if args.code_release not in allowed:
        raise RuntimeError("code release is not explicitly compatible with snapshot")
    settings = get_settings()
    if make_url(settings.database_url).database != args.expected_database:
        raise RuntimeError("runtime database identity does not match expected snapshot target")
    engine = build_engine(settings.database_url)
    with Session(engine) as session:
        actual_rows = build_serialized_public_release_rows(session)
        if actual_rows != package.rows:
            raise RuntimeError("restored database does not exactly match package snapshot")
        real_ids = tuple(row["expedient_id"] for row in actual_rows["real_expedient"])
        if real_ids != tuple(sorted(APPROVED_REAL_EXPEDIENT_IDS)):
            raise RuntimeError("restored REAL corpus does not match approved registry")
    print(
        json.dumps(
            {
                "database": args.expected_database,
                "package_id": package.manifest["package_id"],
                "real_count": len(real_ids),
                "real_ids": real_ids,
                "row_counts": package.manifest["row_counts"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from datosenorden.application.data_release.contract import (  # noqa: E402
    BASELINE_CODE_RELEASE,
)
from datosenorden.application.data_release.exporter import (  # noqa: E402
    export_production_data_package,
)
from datosenorden.core.config import get_settings  # noqa: E402
from datosenorden.db.session import build_engine  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export a verified REAL public data package.")
    parser.add_argument("--release-number", type=int, default=1)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "private" / "releases" / "data")
    parser.add_argument("--created-at", type=datetime.fromisoformat)
    parser.add_argument(
        "--compatible-code-release",
        action="append",
        dest="compatible_code_releases",
        help="40-hex consuming application release; repeat to create an explicit allowlist",
    )
    args = parser.parse_args(argv)
    engine = build_engine(get_settings().database_url)
    with Session(engine) as session:
        result = export_production_data_package(
            session,
            output_dir=args.output_dir,
            release_number=args.release_number,
            created_at=args.created_at,
            compatible_code_releases=(
                tuple(args.compatible_code_releases)
                if args.compatible_code_releases
                else (BASELINE_CODE_RELEASE,)
            ),
        )
    print(
        json.dumps(
            {
                "archive_sha256": result.archive_sha256,
                "logical_content_hash": result.logical_content_hash,
                "package_id": result.package_id,
                "package_path": str(result.package_path.relative_to(ROOT)),
                "row_counts": result.row_counts,
                "sidecar_path": str(result.sidecar_path.relative_to(ROOT)),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from datosenorden.application.data_release.contract import (  # noqa: E402
    TABLE_CONTRACTS,
)
from datosenorden.application.data_release.exporter import (  # noqa: E402
    MODEL_BY_TABLE,
    build_serialized_public_release_rows,
    export_production_data_package,
)
from datosenorden.application.data_release.importer import (  # noqa: E402
    TargetExpectation,
    import_package,
    verify_package,
)
from datosenorden.application.data_release.materialization import (  # noqa: E402
    APPROVED_REAL_IDS,
    BASELINE_REAL_IDS,
    assert_approved_corpus_complete,
    materialize_approved_real_corpus,
)
from datosenorden.infrastructure.real_expedient.repository import (  # noqa: E402
    PostgresExpedientRepository,
)

DATABASE_URL_ENV = "DEO_MATERIALIZATION_DATABASE_URL"
DATABASE_PREFIX = "datosenorden_materialization_"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Restore, materialize, validate, and export the approved REAL corpus."
    )
    parser.add_argument("--base-package", type=Path, required=True)
    parser.add_argument("--base-package-sha256", required=True)
    parser.add_argument("--expected-base-package-id", required=True)
    parser.add_argument("--base-code-release", required=True)
    parser.add_argument("--compatible-code-release", required=True)
    parser.add_argument("--release-number", type=int, required=True)
    parser.add_argument("--created-at", type=datetime.fromisoformat, required=True)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "private" / "releases" / "data")
    args = parser.parse_args(argv)

    database_url = os.getenv(DATABASE_URL_ENV, "")
    _validate_target_url(database_url, os.getenv("DATABASE_URL"))
    engine = create_engine(database_url)
    try:
        package = verify_package(
            args.base_package,
            expected_sha256=args.base_package_sha256,
        )
        if package.manifest["package_id"] != args.expected_base_package_id:
            raise RuntimeError("base package identity does not match the approved release input")
        database_name = str(make_url(database_url).database)
        _require_empty_release_tables(engine)
        imported = import_package(
            engine,
            package,
            expectation=TargetExpectation(
                database_name=database_name,
                environment="release-staging",
                code_release=args.base_code_release,
            ),
        )
        with Session(engine) as session:
            initial_ids = tuple(
                sorted(
                    row.specification.expedient_id
                    for row in PostgresExpedientRepository(session).list_public()
                )
            )
            if initial_ids != tuple(sorted(BASELINE_REAL_IDS)):
                raise RuntimeError(
                    "imported package does not match the certified four-REAL baseline"
                )
            baseline_rows = build_serialized_public_release_rows(session)
            materialized = materialize_approved_real_corpus(session)
            assert_approved_corpus_complete(session)
            _require_base_rows_unchanged(
                baseline_rows,
                build_serialized_public_release_rows(session),
            )
            exported = export_production_data_package(
                session,
                output_dir=args.output_dir,
                release_number=args.release_number,
                created_at=args.created_at,
                compatible_code_releases=(args.compatible_code_release,),
            )
        print(
            json.dumps(
                {
                    "approved_real_ids": list(APPROVED_REAL_IDS),
                    "archive_sha256": exported.archive_sha256,
                    "base_package_id": package.manifest["package_id"],
                    "compatible_code_release": args.compatible_code_release,
                    "imported_rows": imported.inserted,
                    "initial_real_ids": list(materialized.initial_ids),
                    "materialization_statuses": dict(materialized.statuses),
                    "original_fingerprints": dict(materialized.original_fingerprints),
                    "original_unchanged": materialized.original_unchanged,
                    "package_id": exported.package_id,
                    "package_path": str(exported.package_path),
                    "row_counts": exported.row_counts,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    finally:
        engine.dispose()


def _validate_target_url(database_url: str, runtime_url: str | None) -> None:
    if not database_url:
        raise RuntimeError(f"{DATABASE_URL_ENV} is required")
    parsed = make_url(database_url)
    host = (parsed.host or "").lower()
    port = parsed.port or 5432
    database = str(parsed.database or "")
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise RuntimeError("materialization database must be loopback-only")
    if port in {5432, 55432}:
        raise RuntimeError("materialization database must not use a runtime or persistent QA port")
    if not database.startswith(DATABASE_PREFIX):
        raise RuntimeError(f"materialization database must use {DATABASE_PREFIX} prefix")
    if runtime_url and make_url(runtime_url) == parsed:
        raise RuntimeError("materialization database must differ from the runtime database")


def _require_empty_release_tables(engine) -> None:  # noqa: ANN001
    with engine.connect() as connection:
        for contract in TABLE_CONTRACTS:
            table = MODEL_BY_TABLE[contract.name].__table__
            count = int(connection.scalar(select(func.count()).select_from(table)) or 0)
            if count:
                raise RuntimeError(
                    f"materialization target is not empty: {contract.name} has {count} rows"
                )


def _require_base_rows_unchanged(base_rows, current_rows) -> None:  # noqa: ANN001
    for contract in TABLE_CONTRACTS:
        primary_key = contract.primary_key
        current_by_key = {
            tuple(row[name] for name in primary_key): row
            for row in current_rows[contract.name]
        }
        for base_row in base_rows[contract.name]:
            key = tuple(base_row[name] for name in primary_key)
            if current_by_key.get(key) != base_row:
                raise RuntimeError(
                    f"materialization changed certified base row: {contract.name}:{key}"
                )


if __name__ == "__main__":
    raise SystemExit(main())

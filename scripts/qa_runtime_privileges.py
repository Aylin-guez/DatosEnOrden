"""Apply the isolated QA database's least-privilege runtime grants.

This script is deliberately limited to a named local QA database.  Its runtime
role is for citizen/read application processes; provisioning and migrations
continue to use the database owner.
"""

from __future__ import annotations

import argparse
import os

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url


RUNTIME_ROLE = "deo_qa_runtime"
QA_DATABASE = "datosenorden_pytest_goldenqa"


def apply_runtime_privileges(database_url: str) -> None:
    url = make_url(database_url)
    if url.database != QA_DATABASE:
        raise ValueError("QA runtime grants may only target datosenorden_pytest_goldenqa")
    engine = create_engine(url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    f"DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{RUNTIME_ROLE}') "
                    f"THEN CREATE ROLE {RUNTIME_ROLE} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT; END IF; END $$"
                )
            )
            connection.execute(text(f"REVOKE ALL PRIVILEGES ON DATABASE {QA_DATABASE} FROM {RUNTIME_ROLE}"))
            connection.execute(text(f"GRANT CONNECT ON DATABASE {QA_DATABASE} TO {RUNTIME_ROLE}"))
            connection.execute(text(f"REVOKE ALL PRIVILEGES ON SCHEMA public FROM {RUNTIME_ROLE}"))
            connection.execute(text(f"GRANT USAGE ON SCHEMA public TO {RUNTIME_ROLE}"))
            connection.execute(text(f"REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM {RUNTIME_ROLE}"))
            connection.execute(text(f"GRANT SELECT ON ALL TABLES IN SCHEMA public TO {RUNTIME_ROLE}"))
            connection.execute(text(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO {RUNTIME_ROLE}"))
    finally:
        engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL", ""))
    args = parser.parse_args()
    if not args.database_url:
        raise SystemExit("DATABASE_URL is required")
    apply_runtime_privileges(args.database_url)


if __name__ == "__main__":
    main()

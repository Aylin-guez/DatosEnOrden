from __future__ import annotations

from pathlib import Path
import sys
from typing import Callable

from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from datosenorden.maintenance.demo_pack import build_demo_status
from streamlit_app import SessionLocal
from streamlit_app import get_settings
from streamlit_app import list_cross_dataset_organizations
from streamlit_app import list_datasets
from streamlit_app import sanitize_diagnostic_text
from streamlit_app import sanitized_database_url


def _run_step(name: str, step: Callable[[], object]) -> bool:
    print(f"{name}: ", end="")
    try:
        result = step()
    except Exception as exc:  # noqa: BLE001
        print("FAIL")
        print(f"  exception_type={type(exc).__name__}")
        print(f"  exception_message={sanitize_diagnostic_text(exc)}")
        return False

    print("OK")
    if result is not None:
        print(f"  {result}")
    return True


def main() -> int:
    results: list[bool] = []

    results.append(
        _run_step(
            "config load",
            lambda: f"DATABASE_URL={sanitized_database_url()}",
        )
    )
    results.append(
        _run_step(
            "engine/session creation",
            lambda: _check_session(),
        )
    )

    def _with_session(loader: Callable[[object], object]) -> object:
        with SessionLocal() as session:
            return loader(session)

    results.append(
        _run_step(
            "dataset registry load",
            lambda: _with_session(lambda session: f"datasets={len(list_datasets(session))}"),
        )
    )
    results.append(
        _run_step(
            "cross dataset summary load",
            lambda: _with_session(
                lambda session: f"cross_dataset_organizations={len(list_cross_dataset_organizations(session))}"
            ),
        )
    )
    results.append(
        _run_step(
            "demo status load",
            lambda: _with_session(lambda session: _format_demo_status(build_demo_status(session))),
        )
    )

    return 0 if all(results) else 1


def _check_session() -> str:
    _ = get_settings().database_url
    with SessionLocal() as session:
        session.execute(text("select 1")).scalar_one()
    return "select_1=1"


def _format_demo_status(report) -> str:  # noqa: ANN001
    return (
        f"database_connected={report.database_connected}, "
        f"required_datasets_loaded={report.required_datasets_loaded}, "
        f"cross_dataset_organization={report.cross_dataset_organization or 'missing'}, "
        f"timeline_entity={report.timeline_entity or 'missing'}"
    )


if __name__ == "__main__":
    raise SystemExit(main())

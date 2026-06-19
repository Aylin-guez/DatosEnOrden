from pathlib import Path
import sys
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.dataset_exploration import explore_dataset
from datosenorden.maintenance.dataset_exploration import render_dataset_report_html

DEFAULT_OUTPUT_PATH = Path("reports/dataset_report.html")


def main(argv: Sequence[str] | None = None) -> int:
    _ = argv
    output_path = DEFAULT_OUTPUT_PATH

    try:
        with SessionLocal() as session:
            exploration = explore_dataset(session)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(render_dataset_report_html(exploration), encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        print("No se pudo exportar el reporte del dataset.", file=sys.stderr)
        print(f"Detalle: {exc}", file=sys.stderr)
        return 1

    print(f"dataset_report_exported: path={output_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

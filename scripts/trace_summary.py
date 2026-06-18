from argparse import ArgumentParser
from pathlib import Path
import sys
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.traceability_inspector import inspect_traceability_chain
from datosenorden.maintenance.traceability_inspector import render_trace_summary
from datosenorden.maintenance.traceability_inspector import summarize_traceability_chain


def parse_args(argv: Sequence[str] | None = None):
    parser = ArgumentParser(description="Render a compact persisted trace summary")
    parser.add_argument("--external-id", required=True, help="Purchase order external id")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        with SessionLocal() as session:
            traces = inspect_traceability_chain(session, args.external_id)
    except Exception as exc:  # noqa: BLE001
        print("No se pudo resumir la traza persistida.", file=sys.stderr)
        print(f"Detalle: {exc}", file=sys.stderr)
        return 1

    if not traces:
        print(
            f"No se encontro source_record persistido para external_id={args.external_id}",
            file=sys.stderr,
        )
        return 1

    summaries = summarize_traceability_chain(traces)
    print(render_trace_summary(summaries, args.external_id))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

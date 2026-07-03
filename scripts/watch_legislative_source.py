from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from datosenorden.studio.source_watcher import summarize_watch_result, watch_legislative_source


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Watch a small official legislative source window and print review candidates.",
    )
    parser.add_argument("--since", help="Only surface source records dated on or after YYYY-MM-DD when dates are available.")
    parser.add_argument("--limit", type=int, default=5, help="Maximum number of candidates to print. Default: 5.")
    parser.add_argument(
        "--bill",
        action="append",
        dest="bills",
        help="Optional bulletin id to review. Can be passed more than once. Defaults to the current seed bulletin.",
    )
    args = parser.parse_args(argv)

    try:
        since = date.fromisoformat(args.since) if args.since else None
    except ValueError:
        print("error: --since must use YYYY-MM-DD", file=sys.stderr)
        return 2
    if args.limit is not None and args.limit < 0:
        print("error: --limit must be >= 0", file=sys.stderr)
        return 2

    result = watch_legislative_source(since=since, limit=args.limit, bulletins=args.bills)
    print(summarize_watch_result(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
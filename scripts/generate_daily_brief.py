from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from datosenorden.studio.daily_brief import build_daily_brief, save_daily_brief
from datosenorden.studio.state_events import load_state_events


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a local Daily Brief from state events.")
    parser.add_argument("--events-dir", default="data/state_events", help="Directory with generated state event JSON files.")
    parser.add_argument("--output-dir", default="data/daily_briefs", help="Directory for generated daily brief JSON files.")
    parser.add_argument("--limit", type=int, default=10, help="Maximum entries in the brief. Default: 10.")
    parser.add_argument("--max-age-days", type=int, default=1, help="Recent event window. Default: 1 day.")
    args = parser.parse_args(argv)

    if args.limit < 0:
        print("error: --limit must be >= 0", file=sys.stderr)
        return 2
    if args.max_age_days < 0:
        print("error: --max-age-days must be >= 0", file=sys.stderr)
        return 2

    events = load_state_events(root=Path(args.events_dir), limit=100)
    brief = build_daily_brief(events, now=datetime.now(UTC), max_age_days=args.max_age_days, limit=args.limit)
    output_path = save_daily_brief(brief, output_dir=Path(args.output_dir))
    entries = [entry for section in brief.sections for entry in section.entries]

    print("daily_brief:")
    print(f"  events_read={len(events)}")
    print(f"  entries={len(entries)}")
    print(f"  output={output_path}")
    print("  importance=")
    counts: dict[str, int] = {}
    for entry in entries:
        counts[entry.importance] = counts.get(entry.importance, 0) + 1
    for importance, count in sorted(counts.items()):
        print(f"    - {importance}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
from __future__ import annotations

import argparse
from datetime import date, datetime, UTC
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from datosenorden.studio.source_watcher import watch_legislative_source
from datosenorden.studio.topic_classifier import classify_candidate, load_topic_classifier_config
from datosenorden.studio.state_events import build_state_events, save_state_events
from datosenorden.studio.topic_update import build_topic_updates, save_topic_updates


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Detect official source changes and update local topic state.")
    parser.add_argument("--since", help="Only consider source records dated on or after YYYY-MM-DD when dates are available.")
    parser.add_argument("--limit", type=int, default=10, help="Maximum number of candidates to process. Default: 10.")
    parser.add_argument("--config", default="config/topics/topics.json", help="Topic classifier config path.")
    parser.add_argument("--output-dir", default="data/topic_updates", help="Local output directory for generated topic updates.")
    parser.add_argument("--events-output-dir", default="data/state_events", help="Local output directory for generated state events.")
    args = parser.parse_args(argv)

    try:
        since = date.fromisoformat(args.since) if args.since else None
    except ValueError:
        print("error: --since must use YYYY-MM-DD", file=sys.stderr)
        return 2
    if args.limit < 0:
        print("error: --limit must be >= 0", file=sys.stderr)
        return 2

    config = load_topic_classifier_config(Path(args.config))
    watch_result = watch_legislative_source(since=since, limit=args.limit)
    classifications = [classify_candidate(candidate, config) for candidate in watch_result.candidates]
    pairs = tuple(zip(watch_result.candidates, classifications))
    updates = build_topic_updates(pairs)
    state_events = build_state_events(pairs, config_path=Path(args.config))
    generated_at = datetime.now(UTC)
    output_path = save_topic_updates(updates, output_dir=Path(args.output_dir), generated_at=generated_at)
    events_output_path = save_state_events(state_events, output_dir=Path(args.events_output_dir), generated_at=generated_at)

    print("auto_topic_update:")
    print(f"  candidates={len(watch_result.candidates)}")
    print(f"  updates={len(updates)}")
    print(f"  ignored={len(watch_result.ignored_candidates)}")
    print(f"  output={output_path}")
    print(f"  events={len(state_events)}")
    print(f"  events_output={events_output_path}")
    print("  topics=")
    topic_counts: dict[str, int] = {}
    for update in updates:
        topic_counts[update.topic_id] = topic_counts.get(update.topic_id, 0) + 1
    for topic_id, count in sorted(topic_counts.items()):
        print(f"    - {topic_id}: {count}")
    print("  actions=")
    action_counts: dict[str, int] = {}
    for update in updates:
        action_counts[update.suggested_action] = action_counts.get(update.suggested_action, 0) + 1
    for action, count in sorted(action_counts.items()):
        print(f"    - {action}: {count}")
    print("  event_types=")
    event_type_counts: dict[str, int] = {}
    for event in state_events:
        event_type_counts[event.event_type.value] = event_type_counts.get(event.event_type.value, 0) + 1
    for event_type, count in sorted(event_type_counts.items()):
        print(f"    - {event_type}: {count}")
    print("  importance=")
    importance_counts: dict[str, int] = {}
    for event in state_events:
        importance_counts[event.importance.value] = importance_counts.get(event.importance.value, 0) + 1
    for importance, count in sorted(importance_counts.items()):
        print(f"    - {importance}: {count}")
    if watch_result.errors:
        print("  watcher_errors=")
        for error in watch_result.errors:
            print(f"    - {error}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
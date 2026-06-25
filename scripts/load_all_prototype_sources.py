from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
import subprocess
import sys
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from datosenorden.maintenance.source_plugins import list_prototype_sources


def prototype_loader_commands() -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for plugin in list_prototype_sources():
        for command in plugin.commands:
            if command.kind == "loader":
                rows.append((plugin.id, command.command))
    return rows


def run_loaders(*, keep_going: bool = False, dry_run: bool = False) -> list[tuple[str, int, str]]:
    results: list[tuple[str, int, str]] = []
    for source_id, command in prototype_loader_commands():
        if dry_run:
            results.append((source_id, 0, f"dry_run: {command}"))
            continue
        completed = subprocess.run(command.split(), cwd=ROOT, text=True, capture_output=True, check=False)
        output = (completed.stdout + completed.stderr).strip()
        results.append((source_id, completed.returncode, output))
        if completed.returncode != 0 and not keep_going:
            break
    return results


def main(argv: Sequence[str] | None = None) -> int:
    parser = ArgumentParser(description="Load all local prototype source samples")
    parser.add_argument("--keep-going", action="store_true", help="Continue after loader failures")
    parser.add_argument("--dry-run", action="store_true", help="Print planned loaders without mutating data")
    args = parser.parse_args(argv)

    results = run_loaders(keep_going=args.keep_going, dry_run=args.dry_run)
    print("prototype_source_load:")
    for source_id, code, output in results:
        status = "ok" if code == 0 else "FAIL"
        print(f"- {source_id}: {status}")
        if output:
            for line in output.splitlines():
                print(f"  {line}")
    print("next: python scripts/verify_mvp_demo.py")
    return 1 if any(code != 0 for _, code, _ in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())


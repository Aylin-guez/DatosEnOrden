from __future__ import annotations

from pathlib import Path
import subprocess
import sys
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def main(argv: Sequence[str] | None = None) -> int:
    _ = argv
    root = Path(__file__).resolve().parents[1]
    python = sys.executable

    print("mvp_demo_loader:")
    print("  mode=non_destructive")
    print("  note=This script does not reset, truncate, or delete database data.")
    print("  action=load complete local demo case, then verify MVP demo")

    load_result = subprocess.run([python, str(root / "scripts" / "load_complete_demo_case.py")], cwd=root, check=False)
    if load_result.returncode != 0:
        print("  FAIL - load_complete_demo_case.py did not finish successfully.", file=sys.stderr)
        return load_result.returncode or 1

    verify_command = [python, str(root / "scripts" / "verify_mvp_demo.py")]
    verify_result = subprocess.run(verify_command, cwd=root, check=False)
    print("  final_verification_command=python scripts/verify_mvp_demo.py")
    return verify_result.returncode


if __name__ == "__main__":
    raise SystemExit(main())

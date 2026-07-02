from __future__ import annotations

from pathlib import Path
import py_compile
import subprocess
import sys
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def main() -> int:
    checks: list[tuple[str, bool, str]] = []
    checks.append(_platform_compiles_check())
    checks.append(_official_document_demo_check())
    checks.append(_import_check("reading pipeline", "datosenorden.studio.document_reading_pipeline", "publish_document_experience"))
    checks.append(_import_check("publication engine", "datosenorden.studio.publication_engine", "publish_document"))
    checks.append(_import_check("actualidad engine", "datosenorden.studio.actualidad_engine", "publish_current_topic"))
    checks.append(_legislative_adapter_check())
    checks.append(_directory_check("data/real_imports", ROOT / "data" / "real_imports"))
    checks.append(_directory_check("documents", ROOT / "documents"))
    checks.append(_official_documents_structure_check())
    checks.append(_real_imports_not_tracked_check())
    checks.append(_run_demo_check())

    _print_report(checks)
    return 1 if any(not ok for _, ok, _ in checks) else 0


def _platform_compiles_check() -> tuple[str, bool, str]:
    files = [
        ROOT / "reflex_app" / "reflex_app.py",
        ROOT / "src" / "datosenorden" / "studio" / "document_reading_pipeline.py",
        ROOT / "src" / "datosenorden" / "studio" / "publication_engine.py",
        ROOT / "src" / "datosenorden" / "studio" / "actualidad_engine.py",
        ROOT / "src" / "datosenorden" / "web" / "app_services.py",
    ]
    try:
        for file in files:
            py_compile.compile(str(file), doraise=True)
        return ("platform compiles", True, f"files={len(files)}")
    except Exception as exc:  # noqa: BLE001
        return ("platform compiles", False, f"{type(exc).__name__}: {exc}")


def _official_document_demo_check() -> tuple[str, bool, str]:
    try:
        from datosenorden.web.app_services import get_knowledge_demo

        demo = get_knowledge_demo()
        document = demo.get("document", {})
        ok = bool(document.get("id")) and bool(demo.get("fragments")) and bool(demo.get("references", demo.get("evidence", [])))
        return ("official document demo available", ok, str(document.get("id", "")))
    except Exception as exc:  # noqa: BLE001
        return ("official document demo available", False, f"{type(exc).__name__}: {exc}")


def _import_check(label: str, module_name: str, attr: str) -> tuple[str, bool, str]:
    try:
        module = __import__(module_name, fromlist=[attr])
        value = getattr(module, attr)
        return (f"{label} available", callable(value), attr)
    except Exception as exc:  # noqa: BLE001
        return (f"{label} available", False, f"{type(exc).__name__}: {exc}")


def _legislative_adapter_check() -> tuple[str, bool, str]:
    try:
        from datosenorden.adapters.legislature import LegislativeAdapter

        adapter = LegislativeAdapter()
        return ("legislative adapter available", callable(getattr(adapter, "load_bill", None)), "load_bill")
    except Exception as exc:  # noqa: BLE001
        return ("legislative adapter available", False, f"{type(exc).__name__}: {exc}")


def _directory_check(label: str, path: Path) -> tuple[str, bool, str]:
    return (f"{label} exists", path.exists() and path.is_dir(), str(path.relative_to(ROOT)) if path.exists() else "missing")



def _official_documents_structure_check() -> tuple[str, bool, str]:
    root = ROOT / "data" / "official_documents"
    required = [root / name for name in ("incoming", "processing", "published", "archived")]
    required.append(root / "metadata.schema.json")
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    return ("official documents structure exists", not missing, "ok" if not missing else " | ".join(missing))

def _real_imports_not_tracked_check() -> tuple[str, bool, str]:
    result = subprocess.run(
        ["git", "ls-files", "data/real_imports"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        return ("no real imports tracked", False, (result.stderr or result.stdout).strip())
    tracked = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    unexpected = [path for path in tracked if path != "data/real_imports/.gitkeep"]
    return ("no real imports tracked", not unexpected, "none" if not unexpected else " | ".join(unexpected))


def _run_demo_check() -> tuple[str, bool, str]:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run_demo_check.py")],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=240,
    )
    output = (result.stdout or result.stderr or "").strip().splitlines()
    detail = output[-1] if output else f"exit={result.returncode}"
    return ("run_demo_check OK", result.returncode == 0, detail)


def _print_report(checks: list[tuple[str, bool, str]]) -> None:
    print("content_readiness:")
    for label, ok, detail in checks:
        print(f"  {'ok' if ok else 'FAIL'} - {label}: {detail}")


if __name__ == "__main__":
    raise SystemExit(main())

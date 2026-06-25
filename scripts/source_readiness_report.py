from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datosenorden.maintenance.source_plugins import get_source_plugins
from datosenorden.maintenance.source_plugins import plugin_concept_names
from datosenorden.maintenance.source_plugins import plugin_status_value
from datosenorden.maintenance.source_plugins import SourceStatus


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    print("source_readiness_report:")
    for plugin in get_source_plugins():
        commands = plugin.commands
        loader_commands = [command.command for command in commands if command.kind == "loader"]
        summary_commands = [command.command for command in commands if command.kind == "summary"]
        loader_exists = any(_command_script_exists(command) for command in loader_commands)
        summary_exists = any(_command_script_exists(command) for command in summary_commands)
        sample_exists = _sample_exists(plugin)
        tests_exist = _tests_exist(plugin.id)
        missing = _missing_items(plugin_status_value(plugin), plugin.concepts, loader_exists, summary_exists, sample_exists, tests_exist)

        print(f"- {plugin.id}")
        print(f"  name: {plugin.display_name}")
        print(f"  status: {plugin_status_value(plugin)}")
        print(f"  category: {plugin.category}")
        print(f"  concepts: {', '.join(plugin_concept_names(plugin)) or 'none'}")
        print(f"  commands: {len(commands)}")
        for command in commands:
            print(f"    - {command.kind}: {command.command}")
        print(f"  sample_data_exists: {_yes_no(sample_exists)}")
        print(f"  loader_script_exists: {_yes_no(loader_exists)}")
        print(f"  summary_script_exists: {_yes_no(summary_exists)}")
        print(f"  tests_exist: {_yes_no(tests_exist)}")
        print(f"  missing: {', '.join(missing) if missing else 'none'}")
    return 0


def _command_script_exists(command: str) -> bool:
    parts = command.split()
    script = next((part for part in parts if part.startswith("scripts/")), "")
    return bool(script) and (ROOT / script).exists()


def _sample_exists(plugin) -> bool:  # noqa: ANN001
    if plugin.status == SourceStatus.PLANNED:
        return False
    candidates = [
        ROOT / "data" / "sample" / f"{plugin.id}.json",
        ROOT / "data" / "sample" / f"{plugin.id.replace('_', '-')}.json",
        ROOT / "data" / "demo_cases" / "servicio_salud_arauco_complete.json",
    ]
    technical_names = str(plugin.technical_metadata.get("dataset_names", ""))
    if technical_names:
        candidates.extend((ROOT / "data" / "sample").glob(f"*{technical_names.split(',')[0].strip()}*.json"))
    candidates.extend((ROOT / "data" / "sample").glob(f"*{plugin.id.split('_')[0]}*.json"))
    return any(path.exists() for path in candidates)


def _tests_exist(plugin_id: str) -> bool:
    patterns = {plugin_id, plugin_id.replace("_", "-"), plugin_id.split("_")[0]}
    for path in (ROOT / "tests").glob("test_*.py"):
        name = path.name.lower()
        if any(pattern.lower().replace("-", "_") in name for pattern in patterns):
            return True
    return False


def _missing_items(status: str, concepts: tuple, loader_exists: bool, summary_exists: bool, sample_exists: bool, tests_exist: bool) -> list[str]:
    missing: list[str] = []
    if not concepts:
        missing.append("concepts")
    if status != "planned":
        if not loader_exists:
            missing.append("loader_script")
        if not summary_exists:
            missing.append("summary_script")
        if not sample_exists:
            missing.append("sample_or_demo_data")
        if not tests_exist:
            missing.append("tests")
    return missing


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


if __name__ == "__main__":
    raise SystemExit(main())

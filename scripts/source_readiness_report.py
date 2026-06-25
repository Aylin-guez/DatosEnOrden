from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datosenorden.maintenance.source_plugins import get_source_plugins
from datosenorden.maintenance.source_plugins import plugin_concept_names
from datosenorden.maintenance.source_plugins import plugin_status_value
from validate_source_plugin import command_script_exists
from validate_source_plugin import sample_file_exists
from validate_source_plugin import test_file_exists
from validate_source_plugin import validate_plugin


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    print("source_readiness_report:")
    for plugin in get_source_plugins():
        commands = plugin.commands
        validation = validate_plugin(plugin)
        loader_exists = command_script_exists(plugin, "loader")
        summary_exists = command_script_exists(plugin, "summary")
        sample_exists = sample_file_exists(plugin)
        tests_exist = test_file_exists(plugin.id)
        missing = [*validation.critical_failures]

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


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


if __name__ == "__main__":
    raise SystemExit(main())

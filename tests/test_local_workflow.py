from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import reset_migrate_seed_verify as workflow_script  # noqa: E402
from datosenorden.maintenance import local_workflow  # noqa: E402
from datosenorden.maintenance.local_workflow import LocalWorkflowCounts  # noqa: E402


def test_local_workflow_runs_reset_migrate_seed_and_verify(monkeypatch) -> None:
    commands = []

    def fake_run_step(command):  # noqa: ANN001
        commands.append(command)

    class DummySession:
        def close(self):
            return None

    monkeypatch.setattr(local_workflow, "_run_step", fake_run_step)
    monkeypatch.setattr(local_workflow, "SessionLocal", lambda: DummySession())
    monkeypatch.setattr(
        local_workflow,
        "_read_counts",
        lambda session: LocalWorkflowCounts(source_record=1, claim=1, evidence=1, relationship_public=1),
    )

    counts = local_workflow.run_local_reset_migrate_seed_verify()

    assert counts == LocalWorkflowCounts(source_record=1, claim=1, evidence=1, relationship_public=1)
    assert commands[0][:4] == [sys.executable, "-m", "alembic", "downgrade"]
    assert commands[0][4] == "base"
    assert commands[1][:4] == [sys.executable, "-m", "alembic", "upgrade"]
    assert commands[1][4] == "head"
    assert commands[2][0] == sys.executable
    assert Path(commands[2][1]).name == "seed_traceability_flow.py"


def test_helper_script_prints_counts(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        workflow_script,
        "run_local_reset_migrate_seed_verify",
        lambda: LocalWorkflowCounts(source_record=1, claim=1, evidence=1, relationship_public=1),
    )

    exit_code = workflow_script.main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "local_reset_migrate_seed_verify:" in captured.out
    assert "source_record=1" in captured.out
    assert "claim=1" in captured.out
    assert "evidence=1" in captured.out
    assert "relationship_public=1" in captured.out

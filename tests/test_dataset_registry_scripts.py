from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sys

from datosenorden.maintenance.dataset_registry import DatasetCountRow
from datosenorden.maintenance.dataset_registry import DatasetDetails
from datosenorden.maintenance.dataset_registry import DatasetSummary

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import dataset_details
import export_dataset_profile
import list_datasets


def _session_manager(session):
    @contextmanager
    def _manager():
        yield session

    return _manager()


def test_list_datasets_script_prints_rows(monkeypatch, capsys) -> None:
    monkeypatch.setattr(list_datasets, "SessionLocal", lambda: _session_manager(object()))
    monkeypatch.setattr(
        list_datasets,
        "list_datasets",
        lambda session: (
            DatasetSummary(
                slug="chilecompra",
                name="ChileCompra",
                source_records=11,
                entities=7,
                claims=19,
                evidence=19,
                relationships=6,
                health="active",
                planned=False,
            ),
        ),
    )

    exit_code = list_datasets.main([])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "dataset:" in captured.out
    assert "name=ChileCompra" in captured.out
    assert "relationships=6" in captured.out
    assert captured.err == ""


def test_dataset_details_script_prints_sections(monkeypatch, capsys) -> None:
    monkeypatch.setattr(dataset_details, "SessionLocal", lambda: _session_manager(object()))
    monkeypatch.setattr(
        dataset_details,
        "get_dataset_details",
        lambda session, slug: DatasetDetails(  # noqa: ARG005
            slug="chilecompra",
            name="ChileCompra",
            health="active",
            source_records=11,
            entities=7,
            claims=19,
            evidence=19,
            relationships=6,
            source_names=("ChileCompra API Mercado Publico",),
            dataset_names=("chilecompra-licitaciones", "chilecompra-ordenes-compra"),
            entities_by_type=(DatasetCountRow("PUBLIC_ORGANIZATION", 4),),
            claims_by_type=(DatasetCountRow("ISSUES_PURCHASE_ORDER", 12),),
            relationship_types=(DatasetCountRow("RECEIVES_CONTRACT", 6),),
            ingestion_stats=(DatasetCountRow("source_records", 11),),
            planned=False,
        ),
    )

    exit_code = dataset_details.main(["--dataset", "chilecompra"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "dataset_details:" in captured.out
    assert "health=active" in captured.out
    assert "entities_by_type:" in captured.out
    assert captured.err == ""


def test_dataset_details_script_reports_missing_dataset(monkeypatch, capsys) -> None:
    monkeypatch.setattr(dataset_details, "SessionLocal", lambda: _session_manager(object()))
    monkeypatch.setattr(dataset_details, "get_dataset_details", lambda session, slug: None)  # noqa: ARG005

    exit_code = dataset_details.main(["--dataset", "unknown"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Dataset no encontrado: unknown" in captured.err


def test_export_dataset_profile_script_writes_html(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(export_dataset_profile, "DEFAULT_OUTPUT_DIR", tmp_path / "reports")
    monkeypatch.setattr(export_dataset_profile, "SessionLocal", lambda: _session_manager(object()))
    monkeypatch.setattr(
        export_dataset_profile,
        "get_dataset_details",
        lambda session, slug: DatasetDetails(  # noqa: ARG005
            slug="chilecompra",
            name="ChileCompra",
            health="active",
            source_records=11,
            entities=7,
            claims=19,
            evidence=19,
            relationships=6,
            source_names=("ChileCompra API Mercado Publico",),
            dataset_names=("chilecompra-licitaciones", "chilecompra-ordenes-compra"),
            entities_by_type=(DatasetCountRow("PUBLIC_ORGANIZATION", 4),),
            claims_by_type=(DatasetCountRow("ISSUES_PURCHASE_ORDER", 12),),
            relationship_types=(DatasetCountRow("RECEIVES_CONTRACT", 6),),
            ingestion_stats=(DatasetCountRow("source_records", 11),),
            planned=False,
        ),
    )

    exit_code = export_dataset_profile.main(["--dataset", "chilecompra"])

    captured = capsys.readouterr()
    output_path = tmp_path / "reports" / "dataset_chilecompra.html"
    assert exit_code == 0
    assert output_path.exists()
    assert "dataset_profile_exported: path=" in captured.out
    assert "dataset_chilecompra.html" in captured.out
    assert "ChileCompra" in output_path.read_text(encoding="utf-8")
    assert captured.err == ""

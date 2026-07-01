from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import datosenorden.maintenance.search_workspace as search_workspace


class _ScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


@dataclass
class _FakeSession:
    entity_types: tuple[str, ...]
    direct_rows: tuple[SimpleNamespace, ...]
    call_count: int = 0

    def scalars(self, statement):  # noqa: ANN001
        self.call_count += 1
        if self.call_count == 1:
            return _ScalarResult(self.entity_types)
        return _ScalarResult(self.direct_rows)


class _SessionContext:
    def __init__(self, session):
        self.session = session

    def __enter__(self):  # noqa: ANN001
        return self.session

    def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
        _ = (exc_type, exc, tb)
        return False


def test_search_workspace_returns_partial_matches_across_entity_types(monkeypatch) -> None:
    session = _FakeSession(
        entity_types=("PUBLIC_ORGANIZATION", "PERSON"),
        direct_rows=(
            SimpleNamespace(id="2", entity_type="PERSON", name="Autoridad Electa de Muestra"),
        ),
    )
    monkeypatch.setattr(search_workspace, "SessionLocal", lambda: _SessionContext(session))
    monkeypatch.setattr(
        search_workspace,
        "match_entity_candidates",
        lambda session, entity_type, name, limit=20: (
            SimpleNamespace(candidate_entity_id="1", candidate_name="SERVICIO DE SALUD ARAUCO", entity_type=entity_type, score=0.95),
        )
        if entity_type == "PUBLIC_ORGANIZATION"
        else (),
    )
    monkeypatch.setattr(
        search_workspace,
        "get_entity_profile",
        lambda session, entity_id: SimpleNamespace(evidences=(1, 2), relationships=(1,)),
    )
    monkeypatch.setattr(
        search_workspace,
        "build_entity_comparison",
        lambda entity_id: {"datasets_present": ["ChileCompra", "SERVEL"]},
    )
    monkeypatch.setattr(search_workspace, "list_knowledge_documents", lambda: [])
    monkeypatch.setattr(search_workspace, "list_citizen_reports", lambda: [])
    monkeypatch.setattr(search_workspace, "list_tracking_items", lambda: [])

    report = search_workspace.search_workspace("arauco")

    assert len(report["matches"]) == 2
    assert report["matches"][0]["entity_name"] in {"SERVICIO DE SALUD ARAUCO", "Autoridad Electa de Muestra"}
    assert report["matches"][0]["datasets"]
    assert report["matches"][0]["evidence_count"] == 2
    assert report["matches"][0]["relationship_count"] == 1
    assert report["matches"][0]["result_type"] in {"entidad", "proveedor"}
    assert report["matches"][0]["action_label"] == "Abrir expediente"
    assert report["matches"][0]["action_href"].startswith("/investigation?id=")


def test_search_workspace_adds_document_report_and_tracking_matches(monkeypatch) -> None:
    session = _FakeSession(entity_types=(), direct_rows=())
    monkeypatch.setattr(search_workspace, "SessionLocal", lambda: _SessionContext(session))
    monkeypatch.setattr(search_workspace, "resolve_entity", lambda query: SimpleNamespace(found=False, entity=None))
    monkeypatch.setattr(search_workspace, "match_entity_candidates", lambda session, entity_type, name, limit=20: ())
    monkeypatch.setattr(search_workspace, "get_entity_profile", lambda session, entity_id: None)
    monkeypatch.setattr(search_workspace, "build_entity_comparison", lambda entity_id: {"datasets_present": []})
    monkeypatch.setattr(
        search_workspace,
        "list_knowledge_documents",
        lambda: [
            SimpleNamespace(
                id="doc-1",
                title="Documento Arauco",
                summary="Resumen local",
                source="Biblioteca",
                document_type="documento",
                official_status="NOT_OFFICIAL_DATA",
                classification="LOCAL_TEST_DATA",
                related_expediente_target="Entidad Arauco",
                official_url="local://doc",
                sections=(1, 2),
            )
        ],
    )
    monkeypatch.setattr(
        search_workspace,
        "list_citizen_reports",
        lambda: [
            SimpleNamespace(
                id="rep-1",
                title="Reporte Arauco",
                summary="Resumen",
                subject="Entidad Arauco",
                sources=("Fuente",),
                evidence_refs=("ev-1",),
            )
        ],
    )
    monkeypatch.setattr(
        search_workspace,
        "list_tracking_items",
        lambda: [
            SimpleNamespace(
                id="track-1",
                title="Seguimiento Arauco",
                summary="Resumen",
                related_expediente_target="Entidad Arauco",
                related_sources=("Fuente",),
            )
        ],
    )

    report = search_workspace.search_workspace("arauco")

    result_types = {match["result_type"] for match in report["matches"]}
    action_labels = {match["action_label"] for match in report["matches"]}
    assert {"documento", "reporte", "seguimiento"}.issubset(result_types)
    assert {"Ver documento", "Ver reporte", "Ver seguimiento"}.issubset(action_labels)


def test_search_workspace_handles_empty_query() -> None:
    assert search_workspace.search_workspace("") == {"matches": []}

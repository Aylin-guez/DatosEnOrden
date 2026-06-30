from datosenorden.db.session import SessionLocal
from datosenorden.maintenance.sanciones_procedimientos_prototype import (
    LOCAL_TEST_DATA,
    NOT_OFFICIAL_DATA,
    PROCEDURE_HAS_RESOLUTION,
    PROCEDURE_INVOLVES_COMPANY,
    PROCEDURE_INVOLVES_ORGANIZATION,
    PROCEDURE_INVOLVES_PERSON,
    build_sanciones_procedimientos_sample_batch,
    load_sanciones_procedimientos_sample_payload,
    persist_sanciones_procedimientos_sample,
    read_sanciones_procedimientos_summary,
)
from datosenorden.maintenance.source_plugins import SourceStatus
from datosenorden.maintenance.source_plugins import get_source_plugin


def test_sanciones_procedimientos_payload_is_marked_local() -> None:
    payload = load_sanciones_procedimientos_sample_payload()

    assert payload["classification"] == LOCAL_TEST_DATA
    assert payload["official_status"] == NOT_OFFICIAL_DATA
    assert payload["records"]


def test_sanciones_procedimientos_batch_connects_required_entities() -> None:
    payload = load_sanciones_procedimientos_sample_payload()
    batch = build_sanciones_procedimientos_sample_batch(_NullSession(), payload)

    entity_types = {entity.entity_type.value for entity in batch.entities}
    predicates = {claim.predicate for claim in batch.claims}
    relationship_types = {relationship.relationship_type.value for relationship in batch.public_relationships}

    assert {
        "PUBLIC_ORGANIZATION",
        "COMPANY",
        "PERSON",
        "ADMINISTRATIVE_PROCEDURE",
        "ADMINISTRATIVE_RESOLUTION",
    } <= entity_types
    assert {
        PROCEDURE_INVOLVES_ORGANIZATION,
        PROCEDURE_INVOLVES_COMPANY,
        PROCEDURE_INVOLVES_PERSON,
        PROCEDURE_HAS_RESOLUTION,
    } <= predicates
    assert predicates == relationship_types
    assert len(batch.evidence) == 2


def test_sanciones_procedimientos_plugin_is_prototype() -> None:
    plugin = get_source_plugin("sanciones_procedimientos")

    assert plugin is not None
    assert plugin.status == SourceStatus.PROTOTYPE
    assert any(command.kind == "loader" for command in plugin.commands)
    assert any(command.kind == "summary" for command in plugin.commands)


def test_sanciones_procedimientos_persist_and_summary() -> None:
    with SessionLocal() as session:
        persist_sanciones_procedimientos_sample(session)
        summary = read_sanciones_procedimientos_summary(session)

    assert summary.procedures >= 1
    assert summary.resolutions >= 1
    assert summary.evidence >= 2
    assert any(row.organization_name == "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO" for row in summary.rows)


class _NullScalars:
    @staticmethod
    def all():
        return []


class _NullSession:
    @staticmethod
    def get(*args, **kwargs):  # noqa: ANN002, ANN003
        return None

    @staticmethod
    def scalar(*args, **kwargs):  # noqa: ANN002, ANN003
        return None

    @staticmethod
    def scalars(*args, **kwargs):  # noqa: ANN002, ANN003
        return _NullScalars()

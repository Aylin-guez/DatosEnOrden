from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from html import escape
from typing import Iterable

from sqlalchemy import distinct, func, select, union_all
from sqlalchemy.orm import Session

from datosenorden.datasets import dataset_definition_for_name
from datosenorden.datasets import dataset_catalog
from datosenorden.maintenance.human_readable import explain_dataset
from datosenorden.maintenance.human_readable import render_dataset_explanation_html
from datosenorden.models import Claim, Dataset, Entity, Evidence, RelationshipPublic, SourceRecord


@dataclass(frozen=True)
class DatasetRegistryEntry:
    slug: str
    name: str
    dataset_names: tuple[str, ...]
    source_names: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()
    planned: bool = False


@dataclass(frozen=True)
class RealDatasetRegistryEntry:
    id: str
    display_name: str
    description: str
    status: str
    official_url: str
    expected_format: str
    loader_script: str
    last_loaded: str
    supports_incremental: bool
    entity_types: tuple[str, ...]
    coverage: str
    demo_available: bool
    sample_dataset: str
    priority: str = "medium"
    difficulty: str = "medium"


@dataclass(frozen=True)
class DatasetSummary:
    slug: str
    name: str
    source_records: int
    entities: int
    claims: int
    evidence: int
    relationships: int
    health: str
    planned: bool


@dataclass(frozen=True)
class DatasetCountRow:
    label: str
    count: int


@dataclass(frozen=True)
class DatasetDetails:
    slug: str
    name: str
    health: str
    source_records: int
    entities: int
    claims: int
    evidence: int
    relationships: int
    source_names: tuple[str, ...]
    dataset_names: tuple[str, ...]
    entities_by_type: tuple[DatasetCountRow, ...]
    claims_by_type: tuple[DatasetCountRow, ...]
    relationship_types: tuple[DatasetCountRow, ...]
    ingestion_stats: tuple[DatasetCountRow, ...]
    planned: bool


DATASET_REGISTRY: tuple[DatasetRegistryEntry, ...] = tuple(
    DatasetRegistryEntry(
        slug=definition.dataset_slug,
        name=definition.dataset_name,
        dataset_names=definition.dataset_names,
        source_names=definition.source_names,
        aliases=definition.aliases,
        planned=definition.planned,
    )
    for definition in dataset_catalog()
)


REAL_DATASET_REGISTRY: tuple[RealDatasetRegistryEntry, ...] = (
    RealDatasetRegistryEntry(
        id="chilecompra",
        display_name="ChileCompra",
        description="Compras publicas y ordenes de compra cargables desde archivo local exportado o payload compatible.",
        status="connected_file_loader",
        official_url="https://www.mercadopublico.cl/",
        expected_format="JSON compatible con ChileCompra, objeto con Listado o lista de ordenes de compra.",
        loader_script="scripts/load_chilecompra_file.py",
        last_loaded="from_database",
        supports_incremental=False,
        entity_types=("PUBLIC_ORGANIZATION", "COMPANY", "CONTRACT"),
        coverage="Ordenes de compra, compradores, proveedores, evidencia y relaciones basicas.",
        demo_available=True,
        sample_dataset="data/sample/chilecompra_purchase_orders_sample.json",
        priority="high",
        difficulty="medium",
    ),
    RealDatasetRegistryEntry(
        id="lobby",
        display_name="Lobby",
        description="Registros de reuniones de lobby desde archivo local de muestra; pendiente ruta real descargable.",
        status="prototype_sample_loader",
        official_url="https://www.leylobby.gob.cl/",
        expected_format="JSON local normalizado de reuniones.",
        loader_script="scripts/load_lobby_sample.py",
        last_loaded="from_database",
        supports_incremental=False,
        entity_types=("PUBLIC_ORGANIZATION", "PERSON", "LOBBY_MEETING"),
        coverage="Reuniones, contraparte, organismo y materia cuando el archivo local existe.",
        demo_available=True,
        sample_dataset="data/sample/lobby_meeting_sample.json",
        priority="medium",
        difficulty="medium",
    ),
    RealDatasetRegistryEntry(
        id="dipres",
        display_name="DIPRES",
        description="Presupuesto publico desde archivo local de muestra; falta contrato de dataset descargable real.",
        status="prototype_sample_loader",
        official_url="https://www.dipres.gob.cl/",
        expected_format="JSON local normalizado de presupuesto.",
        loader_script="scripts/load_dipres_sample.py",
        last_loaded="from_database",
        supports_incremental=False,
        entity_types=("PUBLIC_ORGANIZATION", "BUDGET"),
        coverage="Asignaciones presupuestarias de prueba y relaciones con organismo.",
        demo_available=True,
        sample_dataset="data/sample/dipres_budget_sample.json",
        priority="medium",
        difficulty="medium",
    ),
    RealDatasetRegistryEntry(
        id="transparencia-activa",
        display_name="Transparencia Activa",
        description="Cargos y roles publicos desde archivo local de muestra; pendiente fuente descargable estable.",
        status="prototype_sample_loader",
        official_url="https://www.portaltransparencia.cl/",
        expected_format="JSON local normalizado de cargos/roles.",
        loader_script="scripts/load_transparencia_sample.py",
        last_loaded="from_database",
        supports_incremental=False,
        entity_types=("PUBLIC_ORGANIZATION", "PERSON", "ROLE"),
        coverage="Roles, titulares y periodos cuando el sample esta cargado.",
        demo_available=True,
        sample_dataset="data/sample/transparencia_activa_sample.json",
        priority="medium",
        difficulty="high",
    ),
    RealDatasetRegistryEntry(
        id="diario-oficial",
        display_name="Diario Oficial",
        description="Publicaciones oficiales desde archivo local de muestra; no descargar PDFs en esta fase.",
        status="prototype_sample_loader",
        official_url="https://www.diariooficial.interior.gob.cl/",
        expected_format="JSON local normalizado de publicaciones.",
        loader_script="scripts/load_diario_oficial_sample.py",
        last_loaded="from_database",
        supports_incremental=False,
        entity_types=("PUBLIC_OBSERVATION", "PUBLIC_ORGANIZATION", "PERSON"),
        coverage="Publicaciones, actos y entidades mencionadas en datos de prueba.",
        demo_available=True,
        sample_dataset="data/sample/diario_oficial_sample.json",
        priority="medium",
        difficulty="high",
    ),
    RealDatasetRegistryEntry(
        id="registro-empresas",
        display_name="Registro Empresas",
        description="Relaciones societarias desde archivo local de muestra; pendiente fuente publica descargable verificable.",
        status="prototype_sample_loader",
        official_url="",
        expected_format="JSON local normalizado de empresas, personas y relaciones.",
        loader_script="scripts/load_registro_empresas_sample.py",
        last_loaded="from_database",
        supports_incremental=False,
        entity_types=("COMPANY", "PERSON"),
        coverage="Representantes, propietarios y modificaciones de muestra.",
        demo_available=True,
        sample_dataset="data/sample/registro_empresas_sample.json",
        priority="low",
        difficulty="high",
    ),
    RealDatasetRegistryEntry(
        id="contraloria",
        display_name="Contraloria",
        description="Informes y observaciones desde archivo local de muestra.",
        status="prototype_sample_loader",
        official_url="https://www.contraloria.cl/",
        expected_format="JSON local normalizado de informes.",
        loader_script="scripts/load_contraloria_sample.py",
        last_loaded="from_database",
        supports_incremental=False,
        entity_types=("PUBLIC_ORGANIZATION", "CONTROL_REPORT", "PUBLIC_OBSERVATION"),
        coverage="Informes y observaciones de prueba.",
        demo_available=True,
        sample_dataset="data/sample/contraloria_sample.json",
        priority="medium",
        difficulty="high",
    ),
    RealDatasetRegistryEntry(
        id="servel",
        display_name="SERVEL",
        description="Autoridades y periodos desde archivo local de muestra.",
        status="prototype_sample_loader",
        official_url="https://www.servel.cl/",
        expected_format="JSON local normalizado de autoridades.",
        loader_script="scripts/load_servel_sample.py",
        last_loaded="from_database",
        supports_incremental=False,
        entity_types=("PERSON", "ROLE", "ELECTORAL_PERIOD"),
        coverage="Autoridades electas y periodos de prueba.",
        demo_available=True,
        sample_dataset="data/sample/servel_authorities_sample.json",
        priority="low",
        difficulty="medium",
    ),
)


def list_datasets(session: Session) -> tuple[DatasetSummary, ...]:
    return tuple(_summarize_dataset(session, entry) for entry in DATASET_REGISTRY)


def list_real_dataset_registry() -> tuple[RealDatasetRegistryEntry, ...]:
    return REAL_DATASET_REGISTRY


def get_real_dataset_entry(dataset_id: str) -> RealDatasetRegistryEntry | None:
    cleaned = dataset_id.strip().lower()
    return next((entry for entry in REAL_DATASET_REGISTRY if entry.id == cleaned), None)


def summarize_real_dataset_registry(session: Session | None = None) -> dict[str, object]:
    entries = []
    source_stats = {row.slug: row for row in list_datasets(session)} if session is not None else {}
    for entry in REAL_DATASET_REGISTRY:
        row = source_stats.get(entry.id)
        entries.append(
            {
                **asdict(entry),
                "source_records": row.source_records if row is not None else 0,
                "entities": row.entities if row is not None else 0,
                "claims": row.claims if row is not None else 0,
                "evidence": row.evidence if row is not None else 0,
                "relationships": row.relationships if row is not None else 0,
                "health": row.health if row is not None else "unknown",
                "ready_for_real_data": entry.status == "connected_file_loader" and bool(entry.loader_script),
            }
        )
    return {
        "entries": entries,
        "totals": {
            "sources": len(entries),
            "ready": sum(1 for entry in entries if entry["ready_for_real_data"]),
            "partial": sum(1 for entry in entries if str(entry["status"]).startswith("prototype")),
            "demo": sum(1 for entry in entries if bool(entry["demo_available"])),
            "without_loader": sum(1 for entry in entries if not str(entry["loader_script"]).strip()),
        },
    }


def get_dataset_details(session: Session, dataset_slug: str) -> DatasetDetails | None:
    entry = resolve_dataset(dataset_slug)
    if entry is None:
        return None

    summary = _summarize_dataset(session, entry)
    if summary.planned:
        return DatasetDetails(
            slug=summary.slug,
            name=summary.name,
            health=summary.health,
            source_records=summary.source_records,
            entities=summary.entities,
            claims=summary.claims,
            evidence=summary.evidence,
            relationships=summary.relationships,
            source_names=entry.source_names,
            dataset_names=entry.dataset_names,
            entities_by_type=(),
            claims_by_type=(),
            relationship_types=(),
            ingestion_stats=_build_ingestion_stats(entry, summary, tuple()),
            planned=True,
        )

    entity_id_scope = _dataset_entity_scope(entry)
    return DatasetDetails(
        slug=summary.slug,
        name=summary.name,
        health=summary.health,
        source_records=summary.source_records,
        entities=summary.entities,
        claims=summary.claims,
        evidence=summary.evidence,
        relationships=summary.relationships,
        source_names=entry.source_names,
        dataset_names=entry.dataset_names,
        entities_by_type=_entity_type_counts(session, entity_id_scope),
        claims_by_type=_claim_type_counts(session, entry),
        relationship_types=_relationship_type_counts(session, entry),
        ingestion_stats=_build_ingestion_stats(
            entry,
            summary,
            _source_record_status_counts(session, entry),
        ),
        planned=entry.planned,
    )


def render_dataset_list_text(rows: tuple[DatasetSummary, ...]) -> str:
    lines: list[str] = []
    for row in rows:
        lines.extend(
            [
                "dataset:",
                f"name={row.name}",
                f"source_records={row.source_records}",
                f"entities={row.entities}",
                f"claims={row.claims}",
                f"evidence={row.evidence}",
                f"relationships={row.relationships}",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def render_dataset_details_text(details: DatasetDetails) -> str:
    lines = [
        "dataset_details:",
        f"slug={details.slug}",
        f"name={details.name}",
        f"health={details.health}",
        "",
        "ingestion_stats:",
    ]
    for row in details.ingestion_stats:
        lines.append(f"  {row.label}={row.count}")

    lines.append("")
    lines.append("entities_by_type:")
    lines.extend(_render_count_rows(details.entities_by_type))
    lines.append("")
    lines.append("claims_by_type:")
    lines.extend(_render_count_rows(details.claims_by_type))
    lines.append("")
    lines.append("relationship_types:")
    lines.extend(_render_count_rows(details.relationship_types))
    return "\n".join(lines)


def render_dataset_profile_html(details: DatasetDetails) -> str:
    summary_cards = [
        ("health", details.health),
        ("source_records", str(details.source_records)),
        ("entities", str(details.entities)),
        ("claims", str(details.claims)),
        ("evidence", str(details.evidence)),
        ("relationships", str(details.relationships)),
    ]
    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Dataset profile: {escape(details.name)}</title>
  <style>
    :root {{
      --bg: #f7f7f5;
      --panel: #ffffff;
      --ink: #1f2933;
      --muted: #52616b;
      --line: #d8dee4;
      --accent: #0f766e;
      --accent-soft: rgba(15, 118, 110, 0.08);
      --shadow: 0 16px 44px rgba(31, 41, 51, 0.12);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      font-family: "Segoe UI", Arial, sans-serif;
      background:
        radial-gradient(circle at top left, rgba(15, 118, 110, 0.10), transparent 30%),
        linear-gradient(180deg, #fbf8f2, var(--bg));
    }}
    main {{
      max-width: 1280px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }}
    header {{
      background: rgba(255, 255, 255, 0.85);
      border: 1px solid rgba(82, 97, 107, 0.14);
      border-radius: 24px;
      box-shadow: var(--shadow);
      padding: 24px 28px;
      margin-bottom: 22px;
    }}
    h1, h2 {{ margin: 0; }}
    h1 {{
      font-size: clamp(28px, 3vw, 40px);
      line-height: 1.1;
      margin-bottom: 8px;
    }}
    .meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px 18px;
      color: var(--muted);
      font-size: 0.95rem;
      margin-top: 8px;
    }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      margin-bottom: 20px;
    }}
    @media (min-width: 1280px) {{
      .metrics {{ grid-template-columns: repeat(6, minmax(0, 1fr)); }}
    }}
    .metric, section {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 20px;
      box-shadow: var(--shadow);
    }}
    .metric {{ padding: 14px; }}
    .metric strong {{ display: block; font-size: 1.5rem; }}
    .metric span {{ color: var(--muted); }}
    .grid {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 18px;
      align-items: start;
    }}
    @media (min-width: 900px) {{
      .grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    }}
    section {{ padding: 16px; overflow: hidden; }}
    .wide {{ grid-column: 1 / -1; }}
    .table-wrap {{
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 8px;
      max-height: 420px;
    }}
    table {{
      width: 100%;
      min-width: 520px;
      border-collapse: collapse;
      font-size: 0.92rem;
    }}
    th, td {{
      border-bottom: 1px solid var(--line);
      padding: 8px 6px;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      position: sticky;
      top: 0;
      background: var(--panel);
      color: var(--muted);
      z-index: 1;
    }}
    a {{ color: var(--accent); }}
    footer {{
      margin-top: 26px;
      padding-top: 16px;
      border-top: 1px solid var(--line);
      color: var(--muted);
      display: flex;
      flex-wrap: wrap;
      gap: 12px 24px;
      font-size: 0.92rem;
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>{escape(details.name)}</h1>
      <div class="meta">
        <span><strong>slug:</strong> {escape(details.slug)}</span>
        <span><strong>health:</strong> {escape(details.health)}</span>
      </div>
    </header>
    <div class="metrics">
      {"".join(f'<div class="metric"><strong>{escape(value)}</strong><span>{escape(label)}</span></div>' for label, value in summary_cards)}
    </div>
    {render_dataset_explanation_html(explain_dataset(details))}
    <div class="grid">
      <section class="wide">
        <h2>Ingestion stats</h2>
        <div class="table-wrap">{_render_table(("Label", "Count"), details.ingestion_stats)}</div>
      </section>
      <section>
        <h2>Entities by type</h2>
        <div class="table-wrap">{_render_table(("Type", "Count"), details.entities_by_type)}</div>
      </section>
      <section>
        <h2>Claims by type</h2>
        <div class="table-wrap">{_render_table(("Type", "Count"), details.claims_by_type)}</div>
      </section>
      <section class="wide">
        <h2>Relationship types</h2>
        <div class="table-wrap">{_render_table(("Type", "Count"), details.relationship_types)}</div>
      </section>
    </div>
    <footer>
      <span>Generated at {escape(datetime.now(timezone.utc).isoformat())}</span>
      <span>Source: DatosEnOrden local dataset registry</span>
    </footer>
  </main>
</body>
</html>
"""


def resolve_dataset(dataset_slug: str) -> DatasetRegistryEntry | None:
    definition = dataset_definition_for_name(dataset_slug)
    if definition is None:
        return None
    return DatasetRegistryEntry(
        slug=definition.dataset_slug,
        name=definition.dataset_name,
        dataset_names=definition.dataset_names,
        source_names=definition.source_names,
        aliases=definition.aliases,
        planned=definition.planned,
    )


def _summarize_dataset(session: Session, entry: DatasetRegistryEntry) -> DatasetSummary:
    if not entry.dataset_names or entry.planned:
        return DatasetSummary(
            slug=entry.slug,
            name=entry.name,
            source_records=0,
            entities=0,
            claims=0,
            evidence=0,
            relationships=0,
            health="empty",
            planned=entry.planned,
        )

    source_records = _count_source_records(session, entry)
    entities = _count_entities(session, entry)
    claims = _count_claims(session, entry)
    evidence = _count_evidence(session, entry)
    relationships = _count_relationships(session, entry)
    health = _dataset_health(source_records, entities, claims, evidence, relationships)
    return DatasetSummary(
        slug=entry.slug,
        name=entry.name,
        source_records=source_records,
        entities=entities,
        claims=claims,
        evidence=evidence,
        relationships=relationships,
        health=health,
        planned=entry.planned,
    )


def _count_source_records(session: Session, entry: DatasetRegistryEntry) -> int:
    return _scalar_count(
        session,
        select(func.count()).select_from(SourceRecord).join(Dataset, SourceRecord.dataset_id == Dataset.id).where(
            Dataset.name.in_(entry.dataset_names)
        ),
    )


def _count_claims(session: Session, entry: DatasetRegistryEntry) -> int:
    return _scalar_count(
        session,
        select(func.count()).select_from(Claim).join(SourceRecord, Claim.source_record_id == SourceRecord.id).join(
            Dataset, SourceRecord.dataset_id == Dataset.id
        ).where(Dataset.name.in_(entry.dataset_names)),
    )


def _count_evidence(session: Session, entry: DatasetRegistryEntry) -> int:
    return _scalar_count(
        session,
        select(func.count()).select_from(Evidence).join(Claim, Evidence.claim_id == Claim.id).join(
            SourceRecord, Claim.source_record_id == SourceRecord.id
        ).join(Dataset, SourceRecord.dataset_id == Dataset.id).where(Dataset.name.in_(entry.dataset_names)),
    )


def _count_relationships(session: Session, entry: DatasetRegistryEntry) -> int:
    return _scalar_count(
        session,
        select(func.count()).select_from(RelationshipPublic).join(Claim, RelationshipPublic.claim_id == Claim.id).join(
            SourceRecord, Claim.source_record_id == SourceRecord.id
        ).join(Dataset, SourceRecord.dataset_id == Dataset.id).where(Dataset.name.in_(entry.dataset_names)),
    )


def _count_entities(session: Session, entry: DatasetRegistryEntry) -> int:
    entity_scope = _dataset_entity_scope(entry)
    return _scalar_count(
        session,
        select(func.count(distinct(entity_scope.c.entity_id))).select_from(entity_scope).where(
            entity_scope.c.entity_id.is_not(None)
        ),
    )


def _dataset_entity_scope(entry: DatasetRegistryEntry):
    claims_subject = select(Claim.subject_entity_id.label("entity_id")).join(
        SourceRecord, Claim.source_record_id == SourceRecord.id
    ).join(Dataset, SourceRecord.dataset_id == Dataset.id).where(Dataset.name.in_(entry.dataset_names))
    claims_object = select(Claim.object_entity_id.label("entity_id")).join(
        SourceRecord, Claim.source_record_id == SourceRecord.id
    ).join(Dataset, SourceRecord.dataset_id == Dataset.id).where(
        Dataset.name.in_(entry.dataset_names),
        Claim.object_entity_id.is_not(None),
    )
    relationships_source = select(RelationshipPublic.source_entity_id.label("entity_id")).join(
        Claim, RelationshipPublic.claim_id == Claim.id
    ).join(SourceRecord, Claim.source_record_id == SourceRecord.id).join(Dataset, SourceRecord.dataset_id == Dataset.id).where(
        Dataset.name.in_(entry.dataset_names)
    )
    relationships_target = select(RelationshipPublic.target_entity_id.label("entity_id")).join(
        Claim, RelationshipPublic.claim_id == Claim.id
    ).join(SourceRecord, Claim.source_record_id == SourceRecord.id).join(Dataset, SourceRecord.dataset_id == Dataset.id).where(
        Dataset.name.in_(entry.dataset_names)
    )
    return union_all(claims_subject, claims_object, relationships_source, relationships_target).subquery()


def _entity_type_counts(session: Session, entity_scope) -> tuple[DatasetCountRow, ...]:  # type: ignore[no-untyped-def]
    statement = (
        select(Entity.entity_type, func.count(distinct(Entity.id)).label("entity_count"))
        .select_from(Entity)
        .join(entity_scope, Entity.id == entity_scope.c.entity_id)
        .group_by(Entity.entity_type)
        .order_by(func.count(distinct(Entity.id)).desc(), Entity.entity_type.asc())
    )
    return _count_rows(session.execute(statement).all())


def _claim_type_counts(session: Session, entry: DatasetRegistryEntry) -> tuple[DatasetCountRow, ...]:
    statement = (
        select(Claim.predicate, func.count(distinct(Claim.id)).label("claim_count"))
        .select_from(Claim)
        .join(SourceRecord, Claim.source_record_id == SourceRecord.id)
        .join(Dataset, SourceRecord.dataset_id == Dataset.id)
        .where(Dataset.name.in_(entry.dataset_names))
        .group_by(Claim.predicate)
        .order_by(func.count(distinct(Claim.id)).desc(), Claim.predicate.asc())
    )
    return _count_rows(session.execute(statement).all())


def _relationship_type_counts(session: Session, entry: DatasetRegistryEntry) -> tuple[DatasetCountRow, ...]:
    statement = (
        select(
            RelationshipPublic.relationship_type,
            func.count(distinct(RelationshipPublic.id)).label("relationship_count"),
        )
        .select_from(RelationshipPublic)
        .join(Claim, RelationshipPublic.claim_id == Claim.id)
        .join(SourceRecord, Claim.source_record_id == SourceRecord.id)
        .join(Dataset, SourceRecord.dataset_id == Dataset.id)
        .where(Dataset.name.in_(entry.dataset_names))
        .group_by(RelationshipPublic.relationship_type)
        .order_by(func.count(distinct(RelationshipPublic.id)).desc(), RelationshipPublic.relationship_type.asc())
    )
    return _count_rows(session.execute(statement).all())


def _source_record_status_counts(session: Session, entry: DatasetRegistryEntry) -> tuple[DatasetCountRow, ...]:
    statement = (
        select(SourceRecord.status, func.count().label("status_count"))
        .select_from(SourceRecord)
        .join(Dataset, SourceRecord.dataset_id == Dataset.id)
        .where(Dataset.name.in_(entry.dataset_names))
        .group_by(SourceRecord.status)
        .order_by(func.count().desc(), SourceRecord.status.asc())
    )
    return _count_rows(session.execute(statement).all())


def _build_ingestion_stats(
    entry: DatasetRegistryEntry,
    summary: DatasetSummary,
    status_rows: tuple[DatasetCountRow, ...],
) -> tuple[DatasetCountRow, ...]:
    stats = [
        DatasetCountRow("source_records", summary.source_records),
        DatasetCountRow("entities", summary.entities),
        DatasetCountRow("claims", summary.claims),
        DatasetCountRow("evidence", summary.evidence),
        DatasetCountRow("relationships", summary.relationships),
        DatasetCountRow("source_names", len(entry.source_names)),
        DatasetCountRow("dataset_names", len(entry.dataset_names)),
    ]
    stats.extend(status_rows)
    return tuple(stats)


def _dataset_health(source_records: int, entities: int, claims: int, evidence: int, relationships: int) -> str:
    counts = (source_records, entities, claims, evidence, relationships)
    if all(count == 0 for count in counts):
        return "empty"
    if all(count > 0 for count in counts):
        return "active"
    return "partially_loaded"


def _render_count_rows(rows: tuple[DatasetCountRow, ...]) -> list[str]:
    if not rows:
        return ["  (no rows)"]
    return [f"  {row.label}={row.count}" for row in rows]


def _render_table(headers: tuple[str, str], rows: tuple[DatasetCountRow, ...]) -> str:
    header_cells = "".join(f"<th>{escape(header)}</th>" for header in headers)
    if rows:
        body = "".join(
            f"<tr><td>{escape(row.label)}</td><td>{row.count}</td></tr>" for row in rows
        )
    else:
        body = f'<tr><td colspan="{len(headers)}">No rows</td></tr>'
    return f"<table><thead><tr>{header_cells}</tr></thead><tbody>{body}</tbody></table>"


def _scalar_count(session: Session, statement) -> int:  # type: ignore[no-untyped-def]
    return int(session.scalar(statement) or 0)


def _count_rows(rows: Iterable[tuple[object, object]]) -> tuple[DatasetCountRow, ...]:
    return tuple(DatasetCountRow(str(label), int(count or 0)) for label, count in rows)

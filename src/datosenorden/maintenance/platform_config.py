from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PLATFORM_CONFIG_PATH = PROJECT_ROOT / "config" / "platform" / "datosenorden_public.json"


@dataclass(frozen=True)
class EntityTypeConfig:
    id: str
    label: str
    description: str = ""
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class RelationshipTypeConfig:
    id: str
    label: str
    description: str = ""
    source_entity_types: tuple[str, ...] = ()
    target_entity_types: tuple[str, ...] = ()


@dataclass(frozen=True)
class WorkflowStateConfig:
    id: str
    label: str
    order: int
    terminal: bool = False
    description: str = ""


@dataclass(frozen=True)
class WorkflowConfig:
    id: str
    label: str
    states: tuple[WorkflowStateConfig, ...]
    description: str = ""


@dataclass(frozen=True)
class DocumentTypeConfig:
    id: str
    label: str
    description: str = ""


@dataclass(frozen=True)
class EvidenceTypeConfig:
    id: str
    label: str
    description: str = ""


@dataclass(frozen=True)
class AudienceConfig:
    id: str
    label: str
    description: str = ""


@dataclass(frozen=True)
class OutputTemplateConfig:
    id: str
    label: str
    format: str
    audience_id: str = ""
    description: str = ""


@dataclass(frozen=True)
class FeatureFlagsConfig:
    knowledge_engine: bool = True
    tracking_engine: bool = True
    report_engine: bool = True
    source_plugins: bool = True
    public_app: bool = True
    external_apis: bool = False
    scraping: bool = False
    auth: bool = False
    payments: bool = False


@dataclass(frozen=True)
class BrandingConfig:
    product_name: str
    studio_name: str
    tone: str
    tagline: str = ""
    primary_color: str = ""


@dataclass(frozen=True)
class VocabularyConfig:
    terms: dict[str, str]
    entity_types: tuple[EntityTypeConfig, ...]
    relationship_types: tuple[RelationshipTypeConfig, ...]
    document_types: tuple[DocumentTypeConfig, ...]
    evidence_types: tuple[EvidenceTypeConfig, ...]


@dataclass(frozen=True)
class PlatformConfig:
    id: str
    name: str
    description: str
    vocabulary: VocabularyConfig
    workflows: tuple[WorkflowConfig, ...]
    audiences: tuple[AudienceConfig, ...]
    output_templates: tuple[OutputTemplateConfig, ...]
    feature_flags: FeatureFlagsConfig
    branding: BrandingConfig
    version: str = "1"


def load_platform_config(path: Path | str) -> PlatformConfig:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return _platform_config_from_dict(payload)


def get_default_platform_config() -> PlatformConfig:
    return load_platform_config(DEFAULT_PLATFORM_CONFIG_PATH)


def validate_platform_config(config: PlatformConfig) -> tuple[str, ...]:
    errors: list[str] = []
    _require(config.id, "config.id", errors)
    _require(config.name, "config.name", errors)
    _require(config.branding.product_name, "branding.product_name", errors)

    entity_ids = _unique_ids(config.vocabulary.entity_types, "entity_type", errors)
    relationship_ids = _unique_ids(config.vocabulary.relationship_types, "relationship_type", errors)
    document_ids = _unique_ids(config.vocabulary.document_types, "document_type", errors)
    evidence_ids = _unique_ids(config.vocabulary.evidence_types, "evidence_type", errors)
    audience_ids = _unique_ids(config.audiences, "audience", errors)
    template_ids = _unique_ids(config.output_templates, "output_template", errors)
    workflow_ids = _unique_ids(config.workflows, "workflow", errors)

    if not entity_ids:
        errors.append("at least one entity type is required")
    if not relationship_ids:
        errors.append("at least one relationship type is required")
    if not document_ids:
        errors.append("at least one document type is required")
    if not evidence_ids:
        errors.append("at least one evidence type is required")
    if not audience_ids:
        errors.append("at least one audience is required")
    if not template_ids:
        errors.append("at least one output template is required")
    if not workflow_ids:
        errors.append("at least one workflow is required")

    for template in config.output_templates:
        if template.audience_id and template.audience_id not in audience_ids:
            errors.append(f"template {template.id} references unknown audience {template.audience_id}")

    for workflow in config.workflows:
        state_ids = _unique_ids(workflow.states, f"workflow_state:{workflow.id}", errors)
        if not state_ids:
            errors.append(f"workflow {workflow.id} requires states")

    return tuple(errors)


def summarize_platform_config(config: PlatformConfig) -> dict[str, Any]:
    return {
        "id": config.id,
        "name": config.name,
        "description": config.description,
        "version": config.version,
        "branding": asdict(config.branding),
        "vocabulary": dict(config.vocabulary.terms),
        "entities": [asdict(item) for item in config.vocabulary.entity_types],
        "relationships": [asdict(item) for item in config.vocabulary.relationship_types],
        "document_types": [asdict(item) for item in config.vocabulary.document_types],
        "evidence_types": [asdict(item) for item in config.vocabulary.evidence_types],
        "workflows": [
            {
                "id": workflow.id,
                "label": workflow.label,
                "description": workflow.description,
                "states": [asdict(state) for state in workflow.states],
            }
            for workflow in config.workflows
        ],
        "audiences": [asdict(item) for item in config.audiences],
        "templates": [asdict(item) for item in config.output_templates],
        "features": asdict(config.feature_flags),
        "validation_errors": list(validate_platform_config(config)),
    }


def workflow_state_values(config: PlatformConfig, workflow_id: str | None = None) -> tuple[str, ...]:
    workflow = _find_workflow(config, workflow_id)
    return tuple(state.id for state in workflow.states) if workflow is not None else ()


def output_template_ids(config: PlatformConfig, audience_id: str | None = None) -> tuple[str, ...]:
    templates = config.output_templates
    if audience_id is not None:
        templates = tuple(template for template in templates if template.audience_id == audience_id)
    return tuple(template.id for template in templates)


def vocabulary_labels(config: PlatformConfig) -> dict[str, str]:
    labels = dict(config.vocabulary.terms)
    labels.update({item.id: item.label for item in config.vocabulary.entity_types})
    labels.update({item.id: item.label for item in config.vocabulary.relationship_types})
    labels.update({item.id: item.label for item in config.vocabulary.document_types})
    labels.update({item.id: item.label for item in config.vocabulary.evidence_types})
    return labels


def _platform_config_from_dict(payload: dict[str, Any]) -> PlatformConfig:
    vocabulary_payload = payload.get("vocabulary", {})
    vocabulary = VocabularyConfig(
        terms={str(key): str(value) for key, value in vocabulary_payload.get("terms", {}).items()},
        entity_types=tuple(_entity_type_from_dict(row) for row in vocabulary_payload.get("entity_types", [])),
        relationship_types=tuple(
            _relationship_type_from_dict(row) for row in vocabulary_payload.get("relationship_types", [])
        ),
        document_types=tuple(_document_type_from_dict(row) for row in vocabulary_payload.get("document_types", [])),
        evidence_types=tuple(_evidence_type_from_dict(row) for row in vocabulary_payload.get("evidence_types", [])),
    )
    return PlatformConfig(
        id=str(payload.get("id", "")),
        name=str(payload.get("name", "")),
        description=str(payload.get("description", "")),
        version=str(payload.get("version", "1")),
        vocabulary=vocabulary,
        workflows=tuple(_workflow_from_dict(row) for row in payload.get("workflows", [])),
        audiences=tuple(_audience_from_dict(row) for row in payload.get("audiences", [])),
        output_templates=tuple(_output_template_from_dict(row) for row in payload.get("output_templates", [])),
        feature_flags=_feature_flags_from_dict(payload.get("feature_flags", {})),
        branding=_branding_from_dict(payload.get("branding", {})),
    )


def _entity_type_from_dict(row: dict[str, Any]) -> EntityTypeConfig:
    return EntityTypeConfig(
        id=str(row.get("id", "")),
        label=str(row.get("label", "")),
        description=str(row.get("description", "")),
        aliases=tuple(str(item) for item in row.get("aliases", [])),
    )


def _relationship_type_from_dict(row: dict[str, Any]) -> RelationshipTypeConfig:
    return RelationshipTypeConfig(
        id=str(row.get("id", "")),
        label=str(row.get("label", "")),
        description=str(row.get("description", "")),
        source_entity_types=tuple(str(item) for item in row.get("source_entity_types", [])),
        target_entity_types=tuple(str(item) for item in row.get("target_entity_types", [])),
    )


def _workflow_from_dict(row: dict[str, Any]) -> WorkflowConfig:
    states = tuple(
        WorkflowStateConfig(
            id=str(state.get("id", "")),
            label=str(state.get("label", "")),
            order=int(state.get("order", index + 1) or index + 1),
            terminal=bool(state.get("terminal", False)),
            description=str(state.get("description", "")),
        )
        for index, state in enumerate(row.get("states", []))
    )
    return WorkflowConfig(
        id=str(row.get("id", "")),
        label=str(row.get("label", "")),
        description=str(row.get("description", "")),
        states=tuple(sorted(states, key=lambda state: state.order)),
    )


def _document_type_from_dict(row: dict[str, Any]) -> DocumentTypeConfig:
    return DocumentTypeConfig(
        id=str(row.get("id", "")),
        label=str(row.get("label", "")),
        description=str(row.get("description", "")),
    )


def _evidence_type_from_dict(row: dict[str, Any]) -> EvidenceTypeConfig:
    return EvidenceTypeConfig(
        id=str(row.get("id", "")),
        label=str(row.get("label", "")),
        description=str(row.get("description", "")),
    )


def _audience_from_dict(row: dict[str, Any]) -> AudienceConfig:
    return AudienceConfig(
        id=str(row.get("id", "")),
        label=str(row.get("label", "")),
        description=str(row.get("description", "")),
    )


def _output_template_from_dict(row: dict[str, Any]) -> OutputTemplateConfig:
    return OutputTemplateConfig(
        id=str(row.get("id", "")),
        label=str(row.get("label", "")),
        format=str(row.get("format", "")),
        audience_id=str(row.get("audience_id", "")),
        description=str(row.get("description", "")),
    )


def _feature_flags_from_dict(row: dict[str, Any]) -> FeatureFlagsConfig:
    defaults = FeatureFlagsConfig()
    values = asdict(defaults)
    values.update({key: bool(value) for key, value in row.items() if key in values})
    return FeatureFlagsConfig(**values)


def _branding_from_dict(row: dict[str, Any]) -> BrandingConfig:
    return BrandingConfig(
        product_name=str(row.get("product_name", "")),
        studio_name=str(row.get("studio_name", "")),
        tone=str(row.get("tone", "")),
        tagline=str(row.get("tagline", "")),
        primary_color=str(row.get("primary_color", "")),
    )


def _find_workflow(config: PlatformConfig, workflow_id: str | None) -> WorkflowConfig | None:
    if workflow_id is None:
        return config.workflows[0] if config.workflows else None
    return next((workflow for workflow in config.workflows if workflow.id == workflow_id), None)


def _unique_ids(items: tuple[Any, ...], label: str, errors: list[str]) -> set[str]:
    seen: set[str] = set()
    for item in items:
        item_id = str(getattr(item, "id", ""))
        if not item_id:
            errors.append(f"{label} has empty id")
            continue
        if item_id in seen:
            errors.append(f"{label} duplicates id {item_id}")
        seen.add(item_id)
    return seen


def _require(value: str, label: str, errors: list[str]) -> None:
    if not value:
        errors.append(f"{label} is required")

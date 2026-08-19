"""Explicit, source-backed public-name authority; never spelling heuristics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class CanonicalNameAuthorityError(ValueError):
    pass


class VerificationStatus(StrEnum):
    MANUAL_VERIFIED = "MANUAL_VERIFIED"


@dataclass(frozen=True)
class CanonicalEntityNameRecord:
    entity_identity: str
    canonical_name: str
    observed_aliases: tuple[str, ...]
    source_authority: str
    source_reference: str
    verification_status: VerificationStatus
    operator: str
    verified_on: date
    version: int = 1
    language: str = "es"

    def __post_init__(self) -> None:
        if not all(str(value).strip() for value in (self.entity_identity, self.canonical_name, self.source_authority, self.source_reference, self.operator)):
            raise CanonicalNameAuthorityError("canonical name records require identity, name, authority, reference and operator")
        if not self.source_reference.startswith("https://") or self.version < 1:
            raise CanonicalNameAuthorityError("canonical name records require HTTPS evidence and positive version")
        if not self.observed_aliases:
            raise CanonicalNameAuthorityError("canonical name records require an observed source alias")


class CanonicalPublicNameRegistry:
    def __init__(self, records: tuple[CanonicalEntityNameRecord, ...]) -> None:
        self._records = {record.entity_identity: record for record in records}
        if len(self._records) != len(records):
            raise CanonicalNameAuthorityError("canonical identity records must be unique")

    def get_canonical_public_name(self, entity_identity: str) -> str:
        try:
            return self._records[entity_identity].canonical_name
        except KeyError as exc:
            raise CanonicalNameAuthorityError("CANONICAL_IDENTITY_REVIEW_REQUIRED") from exc


def bootstrap_public_name_registry() -> CanonicalPublicNameRegistry:
    """Initial manually verified records, backed by official institutional pages."""
    return CanonicalPublicNameRegistry(
        (
            CanonicalEntityNameRecord(
                "chilecompra:buyer:111870", "División Logística del Ejército",
                ("DIVISION LOGISTICA DEL EJERCITO",), "Ejército de Chile",
                "https://www.ejercito.cl/prensa/descargable/MTU3NDA3ODkwNV8xNjI4NDU1MTIwMS01ZTk5YmNlODllMDY4LnBkZg%3D%3D",
                VerificationStatus.MANUAL_VERIFIED, "DEO-Codex bootstrap", date(2026, 8, 19),
            ),
            CanonicalEntityNameRecord(
                "chilecompra:buyer:1593363", "Dirección de Educación Pública",
                ("DIRECCION DE EDUCACION PUBLICA",), "Dirección de Educación Pública",
                "https://educacionpublica.gob.cl/la-nueva-educacion-publica/preguntas-frecuentes/",
                VerificationStatus.MANUAL_VERIFIED, "DEO-Codex bootstrap", date(2026, 8, 19),
            ),
            CanonicalEntityNameRecord(
                "chilecompra:buyer:7383", "Hospital Clínico Dr. Félix Bulnes Cerda",
                ("SERVICIO SALUD OCCIDENTE HOSPITAL DR FELIX BULNES CERDA",), "Servicio de Salud Metropolitano Occidente",
                "https://ssmoc.redsalud.gob.cl/hospital-felix-bulnes/",
                VerificationStatus.MANUAL_VERIFIED, "DEO-Codex bootstrap", date(2026, 8, 19),
            ),
        )
    )

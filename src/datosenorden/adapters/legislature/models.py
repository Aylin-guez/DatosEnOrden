from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


CONGRESS_SOURCE_NAME = "Datos Abiertos Legislativos Congreso Nacional"
CONGRESS_SOURCE_URL = "https://opendata.camara.cl/"
CAMARA_SERVICE_URL = "https://opendata.camara.cl/wscamaradiputados.asmx"


@dataclass(frozen=True)
class LegislativeXmlResponse:
    url: str
    params: dict[str, str]
    xml_text: str
    retrieved_at: datetime


@dataclass(frozen=True)
class LegislativeSession:
    source_id: str
    number: int | None = None
    date: datetime | None = None
    end_date: datetime | None = None
    chamber: str = "camara"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LegislativeVote:
    source_id: str
    bulletin_id: str
    date: datetime | None = None
    vote_type: str | None = None
    result: str | None = None
    quorum: str | None = None
    article: str | None = None
    procedure_stage: str | None = None
    report: str | None = None
    affirmative_total: int | None = None
    negative_total: int | None = None
    abstention_total: int | None = None
    excused_total: int | None = None
    session: LegislativeSession | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LegislativeBill:
    bulletin_id: str
    canonical_id: str
    aliases: tuple[str, ...]
    source_url: str = CONGRESS_SOURCE_URL
    title: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LegislativeBillBundle:
    bill: LegislativeBill
    votes: tuple[LegislativeVote, ...]
    source_response: LegislativeXmlResponse

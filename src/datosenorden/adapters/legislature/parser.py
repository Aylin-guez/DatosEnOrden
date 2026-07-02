from datetime import datetime
import re
from xml.etree import ElementTree

from datosenorden.adapters.legislature.models import (
    LegislativeBill,
    LegislativeBillBundle,
    LegislativeSession,
    LegislativeVote,
    LegislativeXmlResponse,
)

_BULLETIN_RE = re.compile(r"^\d+(?:-[A-Za-z0-9]+)?$")


class LegislativeXmlParser:
    """Parse official XML into adapter-owned Python objects."""

    def parse_bill_votes(
        self, bulletin_id: str, response: LegislativeXmlResponse
    ) -> LegislativeBillBundle:
        normalized_bulletin = normalize_bulletin_id(bulletin_id)
        root = ElementTree.fromstring(response.xml_text)
        votes = tuple(
            self._parse_vote(node, default_bulletin=normalized_bulletin)
            for node in _children(root, "Votacion")
        )
        bill = LegislativeBill(
            bulletin_id=normalized_bulletin,
            canonical_id=canonical_bill_id(normalized_bulletin),
            aliases=bulletin_aliases(normalized_bulletin),
            metadata={"source_operation": "getVotaciones_Boletin"},
        )
        return LegislativeBillBundle(bill=bill, votes=votes, source_response=response)

    def _parse_vote(self, node: ElementTree.Element, default_bulletin: str) -> LegislativeVote:
        vote_id = _required_text(node, "ID")
        bulletin_id = normalize_bulletin_id(_text(node, "Boletin") or default_bulletin)
        session_node = _child(node, "Sesion")
        session = self._parse_session(session_node) if session_node is not None else None
        return LegislativeVote(
            source_id=f"camara-votacion-{vote_id}",
            bulletin_id=bulletin_id,
            date=_parse_datetime(_text(node, "Fecha")),
            vote_type=_text(node, "Tipo"),
            result=_text(node, "Resultado"),
            quorum=_text(node, "Quorum"),
            article=_text(node, "Articulo"),
            procedure_stage=_text(node, "Tramite"),
            report=_text(node, "Informe"),
            affirmative_total=_parse_int(_text(node, "TotalAfirmativos")),
            negative_total=_parse_int(_text(node, "TotalNegativos")),
            abstention_total=_parse_int(_text(node, "TotalAbstenciones")),
            excused_total=_parse_int(_text(node, "TotalDispensados")),
            session=session,
            metadata={"raw_vote_id": vote_id},
        )

    def _parse_session(self, node: ElementTree.Element) -> LegislativeSession:
        session_id = _required_text(node, "ID")
        return LegislativeSession(
            source_id=f"camara-sesion-{session_id}",
            number=_parse_int(_text(node, "Numero")),
            date=_parse_datetime(_text(node, "Fecha")),
            end_date=_parse_datetime(_text(node, "FechaTermino")),
            metadata={"raw_session_id": session_id},
        )


def normalize_bulletin_id(value: str) -> str:
    normalized = value.strip().upper()
    if not normalized:
        raise ValueError("bulletin_id is required")
    if not _BULLETIN_RE.match(normalized):
        raise ValueError(f"Invalid bulletin_id format: {value}")
    return normalized


def canonical_bill_id(bulletin_id: str) -> str:
    return f"cl-congreso-boletin-{normalize_bulletin_id(bulletin_id)}"


def bulletin_aliases(bulletin_id: str) -> tuple[str, ...]:
    normalized = normalize_bulletin_id(bulletin_id)
    aliases = [normalized]
    if "-" in normalized:
        aliases.append(normalized.split("-", 1)[0])
    return tuple(dict.fromkeys(aliases))


def _children(node: ElementTree.Element, name: str) -> list[ElementTree.Element]:
    return [child for child in node.iter() if _local_name(child.tag) == name]


def _child(node: ElementTree.Element, name: str) -> ElementTree.Element | None:
    for child in node:
        if _local_name(child.tag) == name:
            return child
    return None


def _text(node: ElementTree.Element, name: str) -> str | None:
    child = _child(node, name)
    if child is None or child.text is None:
        return None
    value = child.text.strip()
    return value or None


def _required_text(node: ElementTree.Element, name: str) -> str:
    value = _text(node, name)
    if value is None:
        raise ValueError(f"Missing required XML field: {name}")
    return value


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _parse_int(value: str | None) -> int | None:
    if value is None:
        return None
    return int(value)


def _parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))

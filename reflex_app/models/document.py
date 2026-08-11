from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PDFHighlightTarget:
    fragment_id: str
    page: int
    text_snippet: str
    coordinates: None = None

    def to_dict(self) -> dict:
        return {
            "fragment_id": self.fragment_id,
            "page": self.page,
            "text_snippet": self.text_snippet,
            "coordinates": self.coordinates,
        }

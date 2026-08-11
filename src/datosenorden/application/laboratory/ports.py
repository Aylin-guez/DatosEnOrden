from __future__ import annotations

from typing import Protocol


class LaboratorySourcePort(Protocol):
    def load_expedient_catalog(self) -> list[dict]: ...

    def get_expedient(self, expedient_id: str) -> dict | None: ...

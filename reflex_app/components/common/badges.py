from __future__ import annotations


def _accent_badge_class(status: str) -> str:
    accents = {
        "active": "badge badge-teal",
        "prototype": "badge badge-purple",
        "planned": "badge badge-amber",
        "covered": "badge badge-teal",
        "partial": "badge badge-purple",
        "future": "badge badge-amber",
        "activo con datos": "badge badge-teal",
        "prototipo con datos": "badge badge-purple",
        "prototipo sin datos": "badge badge-amber",
        "planificado": "badge badge-amber",
    }
    return accents.get(status, "badge")

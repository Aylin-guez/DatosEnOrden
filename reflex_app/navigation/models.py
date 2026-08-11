from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NavigationItem:
    id: str
    label: str
    href: str
    icon: str
    group: str
    order: int
    active_page: str
    exact_match: bool = True
    visibility: str = "visible"
    external: bool = False
    contextual: bool = False


@dataclass(frozen=True)
class NavigationGroup:
    id: str
    label: str
    order: int
    items: tuple[NavigationItem, ...]

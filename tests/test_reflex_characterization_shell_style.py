from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import reflex as rx

import reflex_app.reflex_app as entrypoint
from reflex_app.app.styles import style
from reflex_app.constants.routes import PAGE_HOME
from reflex_app.features.pulse.state import PulseState
from reflex_app.layouts.shell import shell


def _render_nodes(value: Any) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.get("children", []):
            yield from _render_nodes(child)
        for conditional_branch in ("true_value", "false_value"):
            if conditional_branch in value:
                yield from _render_nodes(value[conditional_branch])
        return

    if isinstance(value, list):
        for item in value:
            yield from _render_nodes(item)


def _rendered_props(value: dict[str, Any]) -> list[str]:
    return [
        prop
        for node in _render_nodes(value)
        for prop in node.get("props", [])
    ]


def test_shell_forwards_lifecycle_and_keeps_chrome_structure_without_footer_copy() -> None:
    component = shell(
        rx.box(id="characterization-slot"),
        active_page=PAGE_HOME,
        on_mount=PulseState.load_home,
    )
    rendered = component.render()
    props = _rendered_props(rendered)

    assert component.event_triggers["on_mount"].events[0].handler.fn is PulseState.load_home.fn
    assert any("shell theme-dark" in prop and "page-home" in prop for prop in props)
    assert any("app-sidebar" in prop for prop in props)
    assert any("sidebar-menu-button" in prop for prop in props)
    assert any("shell-header" in prop for prop in props)
    assert any("header-search" in prop for prop in props)
    assert any("shell-main" in prop for prop in props)
    assert any("shell-alert" in prop for prop in props)
    assert any("site-footer" in prop for prop in props)
    assert any('id:"scroll-top-button"' in prop for prop in props)
    assert any('id:"characterization-slot"' in prop for prop in props)


def test_final_style_contract_preserves_shell_reader_document_timeline_and_responsive_overrides() -> None:
    mobile = style["@media (max-width: 900px)"]
    reader_breakpoint = style["@media (max-width: 1100px)"]

    assert entrypoint.app.style is style

    # Shell and footer: final values after the existing literal and update merge.
    assert style[".shell"]["min_height"] == "100vh"
    assert style[".shell-main"]["margin_left"] == "236px"
    assert style[".app-sidebar"]["position"] == "fixed"
    assert style[".site-footer"]["padding"] == "26px 22px 18px"
    assert style[".footer-grid"]["grid_template_columns"] == "repeat(2, minmax(0, 1fr))"
    assert mobile[".shell-main"]["margin_left"] == "0"
    assert mobile[".app-sidebar"]["display"] == "none"
    assert mobile[".footer-grid"]["grid_template_columns"] == "1fr"

    # Reader and document: preserve the final selected layout and PDF rules.
    assert style[".topic-source-panel"]["position"] == "relative"
    assert style[".topic-pdf-frame"]["min_height"] == "76vh"
    assert style[".official-document-pdf-frame"]["min_height"] == "78vh"
    assert style[".reading-document-workspace"]["grid_template_columns"] == (
        "minmax(0, 1.7fr) minmax(300px, 0.78fr)"
    )
    assert style[".reading-document-side"]["position"] == "sticky"
    assert style[".document-fragment-active"]["animation"] == "document-pulse 2.8s ease-out"
    assert reader_breakpoint[".reading-document-workspace"]["grid_template_columns"] == "1fr"
    assert reader_breakpoint[".reading-document-side"]["position"] == "static"

    # Timeline: protect its current scroll and tracking emphasis without a full CSS snapshot.
    assert style[".live-timeline-strip"]["overflow_x"] == "auto"
    assert style[".live-timeline-strip"]["scroll_snap_type"] == "x proximity"
    assert style[".live-timeline-strip .tracking-event-card"]["flex"] == "0 0 270px"
    assert style[".timeline-list"]["position"] == "relative"
    assert style[".page-tracking .timeline-list"]["padding_left"] == "18px"

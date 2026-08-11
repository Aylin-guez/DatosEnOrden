from __future__ import annotations

import reflex as rx

from reflex_app.constants.public import (
    PUBLIC_OG_IMAGE_ALT,
    PUBLIC_OG_IMAGE_PATH,
    PUBLIC_SITE_AUTHOR,
    PUBLIC_SITE_NAME,
    PUBLIC_SITE_URL,
    PUBLIC_THEME_COLOR,
)


def _public_url(path: str) -> str:
    normalized = path if path.startswith("/") else f"/{path}"
    return f"{PUBLIC_SITE_URL}{normalized}"


PUBLIC_OG_IMAGE_URL = _public_url(PUBLIC_OG_IMAGE_PATH)


def _page_meta(path: str, keywords: str, title: str, description: str, *, og_type: str = "website") -> list[dict | rx.Component]:
    canonical_url = _public_url(path)
    return [
        {"name": "keywords", "content": keywords},
        {"name": "author", "content": PUBLIC_SITE_AUTHOR},
        {"name": "theme-color", "content": PUBLIC_THEME_COLOR},
        {"property": "og:type", "content": og_type},
        {"property": "og:site_name", "content": PUBLIC_SITE_NAME},
        {"property": "og:locale", "content": "es_CL"},
        {"property": "og:url", "content": canonical_url},
        {"property": "og:title", "content": title},
        {"property": "og:description", "content": description},
        {"property": "og:image", "content": PUBLIC_OG_IMAGE_URL},
        {"property": "og:image:alt", "content": PUBLIC_OG_IMAGE_ALT},
        {"name": "twitter:card", "content": "summary_large_image"},
        {"name": "twitter:title", "content": title},
        {"name": "twitter:description", "content": description},
        {"name": "twitter:image", "content": PUBLIC_OG_IMAGE_URL},
        rx.el.link(rel="canonical", href=canonical_url),
    ]

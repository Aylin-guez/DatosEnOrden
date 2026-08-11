from __future__ import annotations

from reflex_app.app.bootstrap import (
    create_app as _create_app,
    global_head_components as _global_head_components,
    public_hydrate_fallback as _public_hydrate_fallback,
)
from reflex_app.app.registry import registered_page_modules as _registered_page_modules
from reflex_app.app.styles import style as _style

# This explicit call is the sole route-registration trigger for the public app.
_registered_page_modules()

app = _create_app(
    style=_style,
    head_components=_global_head_components,
    hydrate_fallback=_public_hydrate_fallback(),
)

# Do not leave bootstrap imports as accidental legacy reexports.
del _create_app, _global_head_components, _public_hydrate_fallback, _registered_page_modules, _style

__all__ = ("app",)

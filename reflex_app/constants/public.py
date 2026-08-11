from __future__ import annotations

import os

PUBLIC_SITE_URL = os.getenv("DATOSENORDEN_PUBLIC_BASE_URL", "https://datosenorden.cl").rstrip("/")
PUBLIC_SITE_NAME = "DatosEnOrden Ciudadano"
PUBLIC_SITE_AUTHOR = "DatosEnOrden Studio"
PUBLIC_THEME_COLOR = "#0f766e"
PUBLIC_OG_IMAGE_PATH = "/og-image.png"
PUBLIC_MANIFEST_PATH = "/site.webmanifest"
PUBLIC_OG_IMAGE_ALT = "DatosEnOrden Ciudadano: informacion publica conectada, verificable y comprensible."

SUPPORT_DONATION_URL = os.getenv("DATOSENORDEN_SUPPORT_URL", "https://link.mercadopago.cl/datosenorden")
SUPPORT_SOURCE_SUGGESTION_URL = "mailto:datosenorden@gmail.com?subject=Sugerir%20fuente%20oficial"
STUDIO_CONVERSATION_URL = "mailto:datosenorden@gmail.com?subject=DatosEnOrden%20Studio"
STUDIO_CONTACT_EMAIL = "datosenorden@gmail.com"

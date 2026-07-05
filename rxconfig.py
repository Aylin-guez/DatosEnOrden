import os

import reflex as rx


PUBLIC_BASE_URL = os.getenv("DATOSENORDEN_PUBLIC_BASE_URL", "https://datosenorden.cl").rstrip("/")
API_URL = os.getenv("API_URL", os.getenv("REFLEX_API_URL", "http://localhost:8000")).rstrip("/")
BACKEND_PATH = os.getenv("REFLEX_BACKEND_PATH", "").strip()
if BACKEND_PATH in {"", "/"}:
    BACKEND_PATH = ""
elif not BACKEND_PATH.startswith("/"):
    BACKEND_PATH = f"/{BACKEND_PATH.rstrip('/')}"
else:
    BACKEND_PATH = BACKEND_PATH.rstrip("/")


config = rx.Config(
    app_name="reflex_app",
    deploy_url=PUBLIC_BASE_URL,
    api_url=API_URL,
    backend_path=BACKEND_PATH,
    plugins=[
        rx.plugins.SitemapPlugin(trailing_slash="never"),
        rx.plugins.TailwindV4Plugin(),
    ],
)

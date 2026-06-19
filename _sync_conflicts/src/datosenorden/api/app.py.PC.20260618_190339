from fastapi import FastAPI

from datosenorden import __version__


def create_app() -> FastAPI:
    app = FastAPI(
        title="DatosEnOrden API",
        version=__version__,
        description="API base para una infraestructura publica de datos verificables.",
    )

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    return app


app = create_app()

from functools import lru_cache
import os
from pathlib import Path


def _load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


class Settings:
    def __init__(self) -> None:
        _load_dotenv()
        self.environment = os.getenv("DATOSENORDEN_ENV", "local")
        self.database_url = os.getenv(
            "DATOSENORDEN_DATABASE_URL",
            "postgresql+psycopg://datosenorden:datosenorden@localhost:5432/datosenorden",
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()

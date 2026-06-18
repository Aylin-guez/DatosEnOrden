from functools import lru_cache
import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _dotenv_candidates() -> tuple[Path, ...]:
    return (
        PROJECT_ROOT / ".env",
        Path.cwd() / ".env",
    )


def _load_dotenv() -> None:
    for path in _dotenv_candidates():
        if not path.exists():
            continue

        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
        return


class Settings:
    def __init__(self) -> None:
        _load_dotenv()
        self.environment = os.getenv("DATOSENORDEN_ENV", "local")
        self.database_url = os.getenv(
            "DATABASE_URL",
            os.getenv(
                "DATOSENORDEN_DATABASE_URL",
                "postgresql+psycopg://datosenorden:datosenorden@localhost:5432/datosenorden",
            ),
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()

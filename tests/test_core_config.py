from datosenorden.core import config


def test_settings_loads_repo_root_dotenv_before_cwd(monkeypatch, tmp_path) -> None:
    root_dotenv = tmp_path / "repo-root.env"
    cwd_dotenv = tmp_path / "cwd.env"

    root_dotenv.write_text(
        "DATABASE_URL=postgresql+psycopg://root_user:root_pass@localhost:5432/root_db\n",
        encoding="utf-8",
    )
    cwd_dotenv.write_text(
        "DATABASE_URL=postgresql+psycopg://cwd_user:cwd_pass@localhost:5432/cwd_db\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(config, "_dotenv_candidates", lambda: (root_dotenv, cwd_dotenv))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DATOSENORDEN_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATOSENORDEN_ENV", raising=False)
    config.get_settings.cache_clear()

    settings = config.get_settings()

    assert settings.database_url == "postgresql+psycopg://root_user:root_pass@localhost:5432/root_db"


def test_settings_prefers_database_url_over_legacy_alias(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://preferred_user:preferred_pass@localhost:5432/preferred_db")
    monkeypatch.setenv(
        "DATOSENORDEN_DATABASE_URL",
        "postgresql+psycopg://legacy_user:legacy_pass@localhost:5432/legacy_db",
    )
    monkeypatch.setattr(config, "_dotenv_candidates", lambda: tuple())
    config.get_settings.cache_clear()

    settings = config.get_settings()

    assert settings.database_url == "postgresql+psycopg://preferred_user:preferred_pass@localhost:5432/preferred_db"

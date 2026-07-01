from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from datosenorden.maintenance.citizen_reports import list_report_template_ids
from datosenorden.maintenance.knowledge_engine import get_knowledge_vocabulary
from datosenorden.maintenance.platform_config import get_default_platform_config
from datosenorden.maintenance.platform_config import load_platform_config
from datosenorden.maintenance.platform_config import summarize_platform_config
from datosenorden.maintenance.platform_config import validate_platform_config
from datosenorden.maintenance.platform_config import workflow_state_values
from datosenorden.maintenance.tracking import tracking_state_values_from_config
from datosenorden.web import app_services


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_CONFIG = ROOT / "config" / "platform" / "datosenorden_public.json"
CLIENT_CONFIG = ROOT / "config" / "platform" / "client_example.json"


def test_default_config_loads_and_validates() -> None:
    config = get_default_platform_config()

    assert config.id == "datosenorden_public"
    assert config.branding.product_name == "DatosEnOrden"
    assert validate_platform_config(config) == ()


def test_public_config_validates() -> None:
    config = load_platform_config(PUBLIC_CONFIG)

    assert validate_platform_config(config) == ()
    assert "reporte_ciudadano" in config.vocabulary.terms
    assert "seguimiento_html" in {template.id for template in config.output_templates}


def test_client_example_config_validates_without_public_domain_terms() -> None:
    config = load_platform_config(CLIENT_CONFIG)
    summary = summarize_platform_config(config)
    serialized = str(summary).lower()

    assert validate_platform_config(config) == ()
    assert "project_tracking" in {workflow["id"] for workflow in summary["workflows"]}
    assert "chile" not in serialized
    assert "politica" not in serialized
    assert "politica" not in serialized
    assert "ciudadano" not in serialized


def test_summarize_platform_config_returns_json_safe_payload() -> None:
    summary = summarize_platform_config(get_default_platform_config())

    assert summary["name"] == "DatosEnOrden publico"
    assert isinstance(summary["entities"], list)
    assert isinstance(summary["features"], dict)
    assert summary["validation_errors"] == []


def test_workflow_states_are_configurable() -> None:
    public = get_default_platform_config()
    client = load_platform_config(CLIENT_CONFIG)

    assert workflow_state_values(public, "seguimiento") == (
        "propuesto",
        "publicado",
        "en_revision",
        "aprobado",
        "implementado",
        "actualizado",
        "archivado",
    )
    assert tracking_state_values_from_config(client, "project_tracking") == (
        "creado",
        "revisado",
        "aprobado",
        "en_ejecucion",
        "finalizado",
    )


def test_engine_helpers_use_platform_config_without_rewriting_engines() -> None:
    config = get_default_platform_config()

    vocabulary = get_knowledge_vocabulary(config)
    templates = list_report_template_ids(config, "ciudadano")

    assert vocabulary["documento_oficial"] == "Documento oficial"
    assert "reporte_ciudadano_html" in templates


def test_app_services_exposes_platform_summary_and_examples() -> None:
    summary = app_services.get_platform_config_summary()
    examples = app_services.get_platform_examples()

    assert summary["id"] == "datosenorden_public"
    assert {example["id"] for example in examples} >= {"datosenorden_public", "client_example"}


def test_platform_config_summary_script_runs() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "platform_config_summary.py"), str(CLIENT_CONFIG)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0
    assert "platform_config_summary:" in result.stdout
    assert "Cliente ficticio" in result.stdout

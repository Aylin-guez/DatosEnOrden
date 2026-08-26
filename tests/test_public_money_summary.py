from __future__ import annotations

from datosenorden.application.public_money import (
    MoneyEpistemicStatus,
    MoneyMetric,
    PublicMoneyObservation,
    PublicMoneySummary,
    PublicMoneySnapshot,
    public_money_projection,
)
from datosenorden.application.real_expedient.citizen_projection import CitizenProjectionContext
from datosenorden.application.real_expedient.democracia_viva_antofagasta import (
    democracia_viva_citizen_context,
)


def _projection() -> dict[str, object]:
    context = democracia_viva_citizen_context()
    assert context.public_money_summary is not None
    evidence = {
        item.evidence_id: {"title": item.title, "official_url": item.official_url}
        for item in context.evidence
    }
    return public_money_projection(context.public_money_summary, evidence)


def test_democracia_viva_summary_keeps_metrics_and_cutoff_separate() -> None:
    summary = _projection()
    snapshot = summary["snapshots"][0]
    assert summary["universe"]["metric"] == "TRANSFERRED"
    assert summary["universe"]["display_amount"] == "$426.000.000"
    assert snapshot["as_of_date"] == "2023-06-30"
    assert snapshot["authority"] == "Contraloría General de la República"
    values = {item["metric"]: item["display_amount"] for item in snapshot["observations"]}
    assert values == {
        "TRANSFERRED": "$426.000.000",
        "RENDERED": "$116.963.639",
        "APPROVED": "$12.146.280",
        "UNRENDERED": "$309.036.361",
    }
    assert "balance" not in snapshot
    assert "sum" not in snapshot


def test_public_money_boundaries_do_not_collapse_into_each_other() -> None:
    summary = _projection()
    snapshot = summary["snapshots"][0]
    values = {item["metric"]: item for item in snapshot["observations"]}
    assert values["TRANSFERRED"]["amount"] != values["RENDERED"]["amount"]
    assert values["RENDERED"]["amount"] != values["APPROVED"]["amount"]
    assert values["UNRENDERED"]["metric_label"] == "Por rendir"
    action_values = {item["metric"]: item for item in summary["subsequent_actions"][0]["observations"]}
    assert action_values["RESTITUTION_ORDERED"]["amount"] == 391_768_516
    assert action_values["RECOVERED"]["epistemic_status"] == "UNKNOWN"
    assert action_values["RECOVERED"]["display_amount"] == "No acreditada en el corpus disponible."
    assert summary["proceedings"][0]["kind"] == "CRIMINAL_PROCEEDING"
    assert "no equivale a condena" in summary["proceedings"][0]["text"]


def test_each_money_observation_preserves_currency_date_and_evidence() -> None:
    summary = _projection()
    for instrument in summary["instruments"]:
        observation = instrument["observations"][0]
        assert observation["currency"] == "CLP"
        assert observation["as_of_date"]
        assert observation["evidence"]
        assert observation["evidence"][0]["official_url"].startswith("https://")
    assert summary["comparability_notice"] == "Estas cifras describen estados y momentos distintos; no deben sumarse entre sí."


def test_not_comparable_is_representable_without_calculation() -> None:
    value = PublicMoneyObservation(
        MoneyMetric.INVESTIGATED_AMOUNT,
        70_000_000,
        "CLP",
        "Universo distinto",
        "Autoridad pública",
        epistemic_status=MoneyEpistemicStatus.NOT_COMPARABLE,
    )
    projected = public_money_projection(PublicMoneySummary("Prueba", value), {})
    assert projected["universe"]["epistemic_status"] == "NOT_COMPARABLE"
    assert projected["universe"]["display_amount"] == "$70.000.000"


def test_investigated_amount_is_not_accredited_loss_and_cutoffs_are_not_comparable() -> None:
    investigated = PublicMoneyObservation(
        MoneyMetric.INVESTIGATED_AMOUNT, 426_000_000, "CLP", "Investigación", "Fiscalía", "2023-12-18"
    )
    accredited_loss = PublicMoneyObservation(
        MoneyMetric.ACCREDITED_LOSS, None, "CLP", "Sentencia de fondo", "Tribunal", "2023-12-18", epistemic_status=MoneyEpistemicStatus.UNKNOWN
    )
    later_cutoff = PublicMoneyObservation(
        MoneyMetric.TRANSFERRED, 426_000_000, "CLP", "Universo posterior distinto", "Otra fuente", "2025-01-01", epistemic_status=MoneyEpistemicStatus.NOT_COMPARABLE
    )
    projected = public_money_projection(
        PublicMoneySummary("Prueba", investigated, snapshots=(PublicMoneySnapshot("Cortes", "2025-01-01", "Universos distintos", "Otra fuente", (accredited_loss, later_cutoff)),)),
        {},
    )
    rows = {item["metric"]: item for item in projected["snapshots"][0]["observations"]}
    assert projected["universe"]["metric"] == "INVESTIGATED_AMOUNT"
    assert rows["ACCREDITED_LOSS"]["epistemic_status"] == "UNKNOWN"
    assert rows["TRANSFERRED"]["epistemic_status"] == "NOT_COMPARABLE"
    assert "sum" not in projected["snapshots"][0]


def test_expedient_without_summary_remains_supported_by_context_contract() -> None:
    assert CitizenProjectionContext().public_money_summary is None

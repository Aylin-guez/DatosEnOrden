from pathlib import Path

ROOT = Path(__file__).parents[1]
TARGETS = [ROOT / "reflex_app" / "features" / "laboratory", ROOT / "src" / "datosenorden" / "application" / "laboratory"]


def test_laboratory_has_no_private_imports_or_secrets():
    text = "\n".join(p.read_text(encoding="utf-8-sig") for d in TARGETS for p in d.rglob("*.py"))
    lowered = text.lower()
    for forbidden in ("deo_core", "bricks", "api_key", "secret", "token =", "http://", "https://"):
        assert forbidden not in lowered
    for pending in ("Signal", "Observation", "Question", "Event", "Decision", "Implementation", "Evaluation"):
        assert f"class {pending}" not in text

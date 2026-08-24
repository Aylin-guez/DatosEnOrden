import json

import httpx

from datosenorden.adapters.legislature.leychile import acquire_norm


def test_acquire_norm_accepts_explicit_effective_current_version(tmp_path):
    payload = {
        "metadatos": {
            "id_norma": "29824",
            "fecha_version": "1985-06-14",
            "vigencia": {"inicio_vigencia": "1990-01-24", "fin_vigencia": ""},
            "vigencias": [
                {"desde": "1990-01-24", "hasta": "", "tipo_version_s": "Última Versión"},
                {"desde": "1985-06-14", "hasta": "1990-01-23", "tipo_version_s": "Texto Original"},
            ],
        },
        "html": ["<p>texto oficial</p>"],
    }
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, content=json.dumps(payload).encode("utf-8"), headers={"content-type": "application/json"})
    )

    artifact = acquire_norm(norm_id="29824", version="1990-01-24", staging_dir=tmp_path, transport=transport)

    assert artifact.norm_id == "29824"
    assert artifact.version == "1990-01-24"
    assert artifact.staging_path.exists()

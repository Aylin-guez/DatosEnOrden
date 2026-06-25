from datosenorden.maintenance.contraloria_prototype import load_contraloria_sample_payload


def test_contraloria_sample_payload_is_marked_local() -> None:
    payload = load_contraloria_sample_payload()

    assert payload["classification"] == "LOCAL_TEST_DATA"
    assert payload["official_status"] == "NOT_OFFICIAL_DATA"
    assert payload["records"]


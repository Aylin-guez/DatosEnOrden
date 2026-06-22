from __future__ import annotations

from datosenorden.datasets import DatasetDefinition
from datosenorden.datasets import register_dataset
from datosenorden.datasets._helpers import jsonify

dataset_slug = "servel"
dataset_name = "SERVEL"
dataset_description = "Dynamic registry entry for the local SERVEL elected authorities sample."
dataset_names = ("servel-authorities-sample",)
source_names = ("DatosEnOrden Servel Sample",)
aliases = ("servel-sample", "servel-authorities", "elected-authorities")
planned = False

register_dataset(
    DatasetDefinition(
        dataset_slug=dataset_slug,
        dataset_name=dataset_name,
        dataset_description=dataset_description,
        dataset_names=dataset_names,
        source_names=source_names,
        aliases=aliases,
        planned=planned,
    )
)


def load_sample_data(input_path=None):  # noqa: ANN001
    from datosenorden.maintenance.servel_prototype import load_servel_sample_payload

    return jsonify(load_servel_sample_payload(input_path))


def build_entities(payload=None):  # noqa: ANN001
    from datosenorden.maintenance.servel_prototype import build_servel_sample_batch

    batch = build_servel_sample_batch(_null_session(), payload)
    return jsonify(batch.entities)


def build_relationships(payload=None):  # noqa: ANN001
    from datosenorden.maintenance.servel_prototype import build_servel_sample_batch

    batch = build_servel_sample_batch(_null_session(), payload)
    return jsonify(batch.public_relationships)


def build_claims(payload=None):  # noqa: ANN001
    from datosenorden.maintenance.servel_prototype import build_servel_sample_batch

    batch = build_servel_sample_batch(_null_session(), payload)
    return jsonify(batch.claims)


def build_evidence(payload=None):  # noqa: ANN001
    from datosenorden.maintenance.servel_prototype import build_servel_sample_batch

    batch = build_servel_sample_batch(_null_session(), payload)
    return jsonify(batch.evidence)


def _null_session():
    class _Scalar:
        def all(self):  # noqa: ANN001
            return []

    class _NullSession:
        def get(self, *args, **kwargs):  # noqa: ANN001
            _ = (args, kwargs)
            return None

        def scalar(self, *args, **kwargs):  # noqa: ANN001
            _ = (args, kwargs)
            return None

        def scalars(self, *args, **kwargs):  # noqa: ANN001
            _ = (args, kwargs)
            return _Scalar()

    return _NullSession()

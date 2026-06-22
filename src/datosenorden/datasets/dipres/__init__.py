from __future__ import annotations

from datosenorden.datasets import DatasetDefinition
from datosenorden.datasets import register_dataset
from datosenorden.datasets._helpers import jsonify

dataset_slug = "dipres-prototype"
dataset_name = "DIPRES"
dataset_description = "Dynamic registry entry for the local DIPRES budget sample."
dataset_names = ("dipres-budget-sample",)
source_names = ("DatosEnOrden DIPRES Sample",)
aliases = ("dipres", "dipres-sample")
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
    from datosenorden.maintenance.dipres_prototype import load_dipres_sample_payload

    return jsonify(load_dipres_sample_payload(input_path))


def build_entities(payload=None):  # noqa: ANN001
    from datosenorden.maintenance.dipres_prototype import build_dipres_sample_batch

    batch = build_dipres_sample_batch(_null_session(), payload)
    return jsonify(batch.entities)


def build_relationships(payload=None):  # noqa: ANN001
    from datosenorden.maintenance.dipres_prototype import build_dipres_sample_batch

    batch = build_dipres_sample_batch(_null_session(), payload)
    return jsonify(batch.public_relationships)


def build_claims(payload=None):  # noqa: ANN001
    from datosenorden.maintenance.dipres_prototype import build_dipres_sample_batch

    batch = build_dipres_sample_batch(_null_session(), payload)
    return jsonify(batch.claims)


def build_evidence(payload=None):  # noqa: ANN001
    from datosenorden.maintenance.dipres_prototype import build_dipres_sample_batch

    batch = build_dipres_sample_batch(_null_session(), payload)
    return jsonify(batch.evidence)


def _null_session():
    return type(
        "_NullSession",
        (),
        {
            "get": staticmethod(lambda *args, **kwargs: None),
            "scalar": staticmethod(lambda *args, **kwargs: None),
            "scalars": staticmethod(lambda *args, **kwargs: type("_Scalar", (), {"all": staticmethod(lambda: [])})()),
        },
    )()

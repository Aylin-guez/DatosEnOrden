from __future__ import annotations

from datosenorden.datasets import DatasetDefinition
from datosenorden.datasets import register_dataset
from datosenorden.datasets._helpers import jsonify

dataset_slug = "municipalidades"
dataset_name = "Municipalidades"
dataset_description = "Local prototype dataset for municipal projects and spending items."
dataset_names = ("municipalidades-project-sample",)
source_names = ("DatosEnOrden Municipalidades Sample",)
aliases = ("municipalidades-sample", "municipalidades-project")
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
    from datosenorden.maintenance.municipalidades_prototype import load_municipalidades_sample_payload

    return jsonify(load_municipalidades_sample_payload(input_path))


def build_entities(payload=None):  # noqa: ANN001
    from datosenorden.maintenance.municipalidades_prototype import build_municipalidades_sample_batch

    batch = build_municipalidades_sample_batch(_null_session(), payload)
    return jsonify(batch.entities)


def build_relationships(payload=None):  # noqa: ANN001
    from datosenorden.maintenance.municipalidades_prototype import build_municipalidades_sample_batch

    batch = build_municipalidades_sample_batch(_null_session(), payload)
    return jsonify(batch.public_relationships)


def build_claims(payload=None):  # noqa: ANN001
    from datosenorden.maintenance.municipalidades_prototype import build_municipalidades_sample_batch

    batch = build_municipalidades_sample_batch(_null_session(), payload)
    return jsonify(batch.claims)


def build_evidence(payload=None):  # noqa: ANN001
    from datosenorden.maintenance.municipalidades_prototype import build_municipalidades_sample_batch

    batch = build_municipalidades_sample_batch(_null_session(), payload)
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


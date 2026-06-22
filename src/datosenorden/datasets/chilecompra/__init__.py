from __future__ import annotations

from datosenorden.datasets import DatasetDefinition
from datosenorden.datasets import register_dataset

dataset_slug = "chilecompra"
dataset_name = "ChileCompra"
dataset_description = "Dynamic registry entry for ChileCompra datasets."
dataset_names = ("chilecompra-licitaciones", "chilecompra-ordenes-compra")
source_names = ("ChileCompra API Mercado Publico",)
aliases = ("chilecompra-api", "mercado-publico")
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
    return {
        "classification": "LOCAL_TEST_DATA",
        "official_status": "NOT_OFFICIAL_DATA",
        "dataset_name": dataset_slug,
        "source_name": source_names[0],
        "records": [],
    }


def build_entities(payload=None):  # noqa: ANN001
    return []


def build_relationships(payload=None):  # noqa: ANN001
    return []


def build_claims(payload=None):  # noqa: ANN001
    return []


def build_evidence(payload=None):  # noqa: ANN001
    return []


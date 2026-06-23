from __future__ import annotations

from datosenorden.datasets import DatasetDefinition
from datosenorden.datasets import register_dataset


dataset_slug = "registro_empresas"
dataset_name = "Registro Empresas"
dataset_description = "Local prototype sample for company registry records."
dataset_names = ("registro-empresas-sample",)
source_names = ("DatosEnOrden Registro Empresas Sample",)
aliases = ("registro empresas", "registro_empresas", "registro-empresas")
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

from datosenorden.datasets import DatasetDefinition, register_dataset


dataset_names = ("congreso-votaciones-boletin",)
source_names = ("Datos Abiertos Legislativos Congreso Nacional", "Congreso Nacional de Chile")
aliases = ("datos abiertos legislativos", "congreso-votaciones-boletin", "camara-votaciones")


register_dataset(
    DatasetDefinition(
        dataset_slug="legislature",
        dataset_name="Datos Abiertos Legislativos",
        dataset_description="Votaciones oficiales de Camara asociadas a boletines legislativos cargados manualmente.",
        dataset_names=dataset_names,
        source_names=source_names,
        aliases=aliases,
    )
)

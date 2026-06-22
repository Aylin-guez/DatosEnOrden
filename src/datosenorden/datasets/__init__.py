from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from pkgutil import iter_modules
from types import ModuleType
from typing import Any


@dataclass(frozen=True)
class DatasetDefinition:
    dataset_slug: str
    dataset_name: str
    dataset_description: str
    dataset_names: tuple[str, ...] = ()
    source_names: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()
    planned: bool = False


_REGISTERED_DATASETS: dict[str, DatasetDefinition] = {}
_DISCOVERED = False


def register_dataset(definition: DatasetDefinition) -> DatasetDefinition:
    _REGISTERED_DATASETS[definition.dataset_slug] = definition
    return definition


def discover_datasets(*, force: bool = False) -> tuple[DatasetDefinition, ...]:
    global _DISCOVERED
    if force:
        _REGISTERED_DATASETS.clear()
        _DISCOVERED = False

    if not _DISCOVERED:
        for module in _iter_dataset_modules():
            _import_dataset_module(module)
        _DISCOVERED = True
    return tuple(sorted(_REGISTERED_DATASETS.values(), key=lambda item: item.dataset_name.lower()))


def dataset_definition_for_name(name: str) -> DatasetDefinition | None:
    cleaned = _clean_name(name)
    if not cleaned:
        return None
    for definition in discover_datasets():
        if _matches_definition(definition, cleaned):
            return definition
    return None


def dataset_slug_for_name(name: str) -> str | None:
    definition = dataset_definition_for_name(name)
    if definition is None:
        return None
    return definition.dataset_slug


def dataset_label_for_name(name: str) -> str:
    definition = dataset_definition_for_name(name)
    if definition is not None:
        return definition.dataset_name
    return name.replace("-", " ").replace("_", " ").title()


def dataset_dataset_names() -> tuple[str, ...]:
    names: list[str] = []
    for definition in discover_datasets():
        names.extend(definition.dataset_names)
    return tuple(names)


def dataset_catalog() -> tuple[DatasetDefinition, ...]:
    return discover_datasets()


def _iter_dataset_modules() -> tuple[str, ...]:
    package = __name__
    module = import_module(package)
    module_path = list(getattr(module, "__path__", ()))
    modules: list[str] = []
    for finder in module_path:
        for info in iter_modules([finder]):
            if info.ispkg:
                modules.append(f"{package}.{info.name}")
    return tuple(sorted(modules))


def _import_dataset_module(module_name: str) -> ModuleType:
    return import_module(module_name)


def _matches_definition(definition: DatasetDefinition, cleaned_name: str) -> bool:
    haystack = {
        _clean_name(definition.dataset_slug),
        _clean_name(definition.dataset_name),
        *(_clean_name(alias) for alias in definition.aliases),
        *(_clean_name(dataset_name) for dataset_name in definition.dataset_names),
        *(_clean_name(source_name) for source_name in definition.source_names),
    }
    return cleaned_name in haystack


def _clean_name(value: str) -> str:
    return value.strip().lower()


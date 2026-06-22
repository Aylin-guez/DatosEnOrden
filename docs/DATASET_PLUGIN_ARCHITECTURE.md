# Dataset Plugin Architecture

DatosEnOrden now uses a local dataset plugin layer so new public-information sources can be added without changing the investigation frontend.

## How it works

1. Each dataset lives under `src/datosenorden/datasets/<dataset_name>/`.
2. The module registers a `DatasetDefinition` when it is imported.
3. The maintenance layer loads the real graph data with the existing `GraphBatch` + `GraphLoader` path.
4. The registry, cross-dataset explorer, timeline explorer, and investigation view read dataset metadata from the discovered plugins.

## Required interface

Each dataset module should expose:

- `dataset_slug`
- `dataset_name`
- `dataset_description`
- `load_sample_data()`
- `build_entities()`
- `build_relationships()`
- `build_claims()`
- `build_evidence()`

For local prototype datasets, the build functions may wrap the maintenance loader and return plain list/dict structures for inspection.

## How to add a dataset

1. Create `src/datosenorden/datasets/<new_dataset>/__init__.py`.
2. Add a local sample file under `data/sample/`.
3. Implement the required interface and call `register_dataset(...)`.
4. Add a matching maintenance loader if the dataset needs to persist graph data.
5. Add tests that verify the sample loader, registry entry, and investigation integration.

## Investigation integration flow

Browser/UI -> service layer -> investigation view -> dataset catalog -> maintenance loaders -> PostgreSQL

The frontend does not need dataset-specific branches. If a new dataset is registered and loaded, it appears through the same shared service layer and explorer queries.

## Notes

- PostgreSQL remains the source of truth.
- The plugin layer is local and does not call external APIs.
- Sample data must stay clearly labeled as `LOCAL_TEST_DATA` and `NOT_OFFICIAL_DATA`.


# Automatic Timeline

La timeline automática construye una cronología inicial desde los datos ya presentes en el expediente.

## Implementado

`src/datosenorden/maintenance/investigation_timeline.py` usa la timeline derivada del grafo local y la agrupa por año y categoría.

Cada evento expone:

- fecha;
- etiqueta;
- fuente;
- categoría;
- explicación neutral;
- `origin=derived_from_expediente`;
- `source_id` / `source_record_id` cuando existe;
- `claim_id`;
- `predicate`.

## Neutralidad

La timeline describe registros y cambios observables. No afirma causalidad, irregularidad ni responsabilidad.

## Integración

- `/investigation` muestra una cronología generada cuando existe información con fecha.
- `/tracking` distingue eventos `demo_manual` de eventos derivados.

## Futuro

- Fusionar timeline manual y derivada.
- Mostrar eventos sin fecha en una sección separada.
- Permitir filtros por fuente, entidad relacionada y tipo de evidencia.

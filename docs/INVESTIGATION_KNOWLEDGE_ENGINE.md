# Investigation Knowledge Engine

## Objetivo

Investigation Knowledge Engine genera una lectura ciudadana estructurada para expedientes a partir de datos ya disponibles: fuentes, claims, evidencias, relaciones, timeline y entidades conectadas.

No usa IA externa, scraping, APIs externas ni cambios de schema.

## Entradas

El motor recibe un payload de expediente ya construido por la aplicacion. Usa campos genericos:

- `entity`
- `dataset_badges`
- `compact_metrics`
- `evidence`
- `connections`
- `timeline`
- registros operativos u otros grupos de datos disponibles

No depende de conceptos politicos, nacionales, hospitalarios ni de un cliente especifico.

## Salidas

Devuelve:

- `citizen_summary`: resumen ciudadano neutral.
- `key_points`: 3 a 6 puntos clave con `source_ids` o `evidence_ids`.
- `suggested_questions`: preguntas para orientar revision.
- `limitations`: limites del expediente y del demo.
- `neutrality_notice`: advertencia reutilizable.

## Reglas de neutralidad

El motor debe:

- explicar que informacion existe;
- indicar de donde viene;
- mostrar que permite entender;
- decir que no permite concluir;
- evitar acusaciones o inferencias de responsabilidad;
- recordar que cada afirmacion debe revisarse con evidencia original.

No debe afirmar causalidad, irregularidad ni responsabilidad.

## Integracion actual

`app_services.get_investigation()` agrega el bloque `knowledge` al payload del expediente.

La UI de `/investigation` usa ese bloque para complementar `Resumen ciudadano` con:

- puntos clave;
- preguntas sugeridas;
- limitaciones;
- advertencia neutral.

El flujo anterior sigue disponible como fallback para no romper compatibilidad.

## Evolucion futura

El motor puede crecer sin cambiar su contrato principal:

1. Mejorar reglas por tipo de fuente.
2. Incorporar plantillas configurables por audiencia.
3. Agregar validaciones de cobertura.
4. Usar IA local o externa solo como capa opcional de redaccion o sugerencia.

Si se agrega IA en el futuro:

- no debe escribir directamente datos canonicos;
- debe recibir evidencia y contexto ya estructurados;
- debe devolver afirmaciones trazables;
- debe conservar `source_ids` y `evidence_ids`;
- debe mantener advertencias de neutralidad;
- debe permitir revision humana antes de publicar.

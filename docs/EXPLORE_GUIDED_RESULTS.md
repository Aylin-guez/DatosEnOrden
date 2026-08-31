# Resultados guiados de Explore

Una pregunta guiada abre una respuesta ciudadana separada de la búsqueda manual.
La respuesta describe únicamente la información pública incorporada en
DatosEnOrden; no pretende enumerar el universo completo de personas, organismos,
proveedores o contratos.

El contrato de proyección conserva:

- `result_count`: resultados ciudadanos principales devueltos;
- `items`: entidades y expedientes relacionados disponibles;
- `result_limit`: límite actual de presentación (12);
- `offset` y `next_cursor`: reservados para paginación futura;
- `filters_available` y `sort_options`: capacidades declaradas para evolución.

La interfaz no debe renderizar un conjunto ilimitado de tarjetas. Cuando el
corpus requiera más resultados, el lector deberá implementar paginación, filtros
y orden respaldados por ese contrato, sin convertir el estado de una pregunta
guiada en una búsqueda manual.

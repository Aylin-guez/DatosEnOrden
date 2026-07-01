# Library V1

La Biblioteca es el lugar donde documentos locales de prueba u oficiales futuros se convierten en lectura ciudadana.

## Implementado

La Biblioteca usa Knowledge Engine local y rule-based para mostrar:

- listado de documentos;
- metadata visible: tipo, fecha, fuente, clasificación y estado;
- resumen ciudadano;
- preguntas importantes;
- puntos clave;
- evidencia/anclas del documento;
- relación con expediente, reporte ciudadano y seguimiento.

## Datos actuales

El caso demo usa datos locales marcados como:

- `LOCAL_TEST_DATA`;
- `NOT_OFFICIAL_DATA`.

No representa datos oficiales reales.

## PDFs y originales

Esta fase no descarga ni almacena PDFs pesados. Los documentos pueden declarar `official_url` o referencias `local://` para apuntar a la fuente original o a una referencia local liviana.

## Futuro

- Conectar documentos reales verificados.
- Guardar hashes y metadatos de origen.
- Agregar búsqueda interna por documento.
- Separar vista de catálogo y vista de documento.

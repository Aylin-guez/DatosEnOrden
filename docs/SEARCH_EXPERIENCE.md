# Search Experience

La búsqueda ciudadana debe ayudar a una persona que no conoce el nombre exacto de una entidad.

## Implementado

- Normalización de mayúsculas, acentos y espacios.
- Coincidencia por alias mediante Entity Resolution.
- Coincidencia parcial sobre entidades locales.
- Resultados de documentos, reportes y seguimiento cuando el texto coincide.
- Tipo de resultado y acción principal:
  - entidad: abrir expediente;
  - proveedor: abrir expediente;
  - documento: ver Biblioteca;
  - reporte: ver Reportes;
  - seguimiento: ver Seguimiento;
  - fuente/registro: abrir expediente relacionado cuando exista.

## Ejemplo

Buscar `arauco` debe devolver resultados relacionados con Servicio de Salud Arauco, documentos explicados, reportes ciudadanos y seguimiento demo cuando existan datos locales cargados.

## Principios

- La búsqueda no reemplaza Entity Resolution; la usa como ayuda.
- No debe abrir expedientes vacíos como si fueran completos.
- Debe favorecer acciones claras antes que detalles técnicos.

## Futuro

- Ranking por cercanía semántica local.
- Filtros por tipo de resultado.
- Vista de registro cuando un resultado no tenga expediente rico.

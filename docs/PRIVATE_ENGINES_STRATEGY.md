# Private Engines Strategy

Los motores reutilizables son propiedad estrategica de DatosEnOrden Studio. En el MVP pueden convivir en este monorepo para acelerar validacion, integracion y demostracion publica.

## Estrategia futura

A futuro, los motores deberan extraerse a repos privados independientes:

- `platform-core`
- `entity-resolution-engine`
- `reading-pipeline`
- `knowledge-engine`
- `publication-engine`
- `traceflow-engine`
- `report/thirdlife engine`

DatosEnOrden publico sera cliente de esos motores. El sitio publico debe consumir contratos y artefactos publicados, no contener toda la logica estrategica de Studio para siempre.

## Reglas actuales

- No mover codigo ahora.
- No romper imports existentes.
- No publicar configuraciones de clientes.
- No subir datos reales sensibles.
- No mezclar datos demo con contenido publico real.
- Mantener `src/datosenorden/studio` versionado mientras el MVP lo necesite.

## Zona privada futura

Las carpetas locales para motores privados, configuraciones de clientes y datos reales deben permanecer fuera de Git mediante `.gitignore`. Si se necesita probar integraciones privadas, deben vivir en carpetas ignoradas y documentarse sin exponer material sensible.

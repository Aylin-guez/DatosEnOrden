# Repository Strategy

## Objetivo

DatosEnOrden debe poder mostrarse publicamente como proyecto ciudadano sin exponer de forma innecesaria la propiedad estrategica de DatosEnOrden Studio.

## Principio

El proyecto ciudadano puede tener partes publicas: aplicacion de demostracion, documentacion publica, datos demo, guias de uso y materiales de transparencia sobre el estado del MVP.

Los motores reutilizables son propiedad estrategica de DatosEnOrden Studio. Su valor esta en ordenar, conectar, seguir y transformar informacion para distintos dominios. No deben presentarse como codigo abierto por defecto ni mezclarse con configuraciones comerciales o de clientes.

## Separacion futura recomendada

Repo publico:

- app ciudadana DatosEnOrden
- documentacion publica
- datos demo claramente marcados
- scripts de demostracion seguros
- guias de despliegue del MVP ciudadano

Repos privados:

- motores core reutilizables
- adaptadores comerciales
- configuraciones de clientes
- plantillas comerciales
- integraciones privadas
- datos o fixtures de clientes

## Reglas actuales

- No mover archivos ahora.
- No romper imports actuales.
- No cambiar schema por esta separacion.
- No publicar datos reales ni configuraciones de clientes.
- Mantener los datos demo marcados como `LOCAL_TEST_DATA` y `NOT_OFFICIAL_DATA` cuando corresponda.

## Criterio para publicar

Antes de hacer publico cualquier archivo, revisar si contiene:

- nombres de clientes reales
- datos sensibles
- claves, tokens o rutas privadas
- configuraciones comerciales
- logica que convenga mantener como ventaja estrategica
- promesas de producto que todavia no existen

Si hay duda, mantener privado hasta separar responsabilidades con mas cuidado.

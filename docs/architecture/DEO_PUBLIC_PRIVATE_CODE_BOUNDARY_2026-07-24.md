# DEO Public/Private Code Boundary

Fecha: 2026-07-24

## Ownership

| Superficie | Responsabilidad |
| --- | --- |
| Producto publico | UI ciudadana, State de producto, coordinacion especifica, contratos publicos y clientes sin secretos. |
| Core privado | Capacidades reutilizables de busqueda, ingestion documental, ranking y normalizacion transversal. |
| Integraciones comerciales privadas | Empaquetado, autenticacion, metering, marketplaces y adaptadores comerciales. |

## Clasificacion

- PUBLIC_PRODUCT_UI: paginas, componentes y State propios de DEO Ciudadano.
- PUBLIC_PRODUCT_APPLICATION: coordinacion especifica, view-models y adaptacion UI.
- PUBLIC_CONTRACT: puertos y protocolos para consumir capacidades externas sin revelar implementacion.
- CORE_PRIVATE: engines y algoritmos reutilizables.
- BRICK_PRIVATE: integraciones comerciales, autenticacion, metering y adaptadores cerrados.
- PRODUCT_SPECIFIC: logica valida solo para la experiencia ciudadana.
- DUPLICATED_PRIVATE_LOGIC: codigo publico que replica una capacidad privada y requiere una decision de migracion.
- UNCLEAR_REQUIRES_DECISION: ownership aun no determinado.

## Regla De Frontera

El producto publico puede contener UI, feature state, orquestacion especifica, puertos publicos y clientes configurables sin secretos. No debe contener engines reutilizables, OCR, ranking, extraccion documental, graph analysis, evidence analysis, metering comercial, implementaciones privadas ni configuracion interna.

## Auditoria De Search

Se revisaron la capa de aplicacion de Search y sus consumidores Reflex frente a contratos privados de referencia, sin copiar rutas, nombres de paquetes ni detalles de integracion.

Resultado:

1. La capa de Search coordina el producto y forma view-models ciudadanos.
2. No implementa busqueda documental, ranking, extraccion PDF, OCR ni normalizacion reusable.
3. No expone detalles de implementacion privada.
4. No importa codigo privado.
5. Debe conservarse como PUBLIC_PRODUCT_APPLICATION.
6. WorkspaceSearchPort es una frontera publica permitida para un backend o gateway futuro.
7. Las etiquetas ciudadanas, hrefs publicados, badges y textos de discovery son PRODUCT_SPECIFIC.

## Contratos Publicos Permitidos

- puertos Protocol;
- payloads publicos del producto;
- URLs configurables y sin secretos;
- clientes de feature que no implementen engines.

No deben incluir nombres de paquetes privados, puertos internos, claves, tokens, detalles comerciales ni implementaciones de engine.

## Decisiones

- Search publico se mantiene como capa de orquestacion de producto.
- El producto no se conecta directamente a Core ni a integraciones comerciales privadas.
- Document Reading consume contratos publicos; no revela implementacion privada.
- Public Record no se modifica en esta fase.
- Laboratory no se implementa.

## Reglas Para Futuras Features

- Toda feature nueva nace bajo reflex_app/features/<feature>/.
- Si requiere una capacidad privada, define un puerto publico y espera un cliente o gateway.
- No importar paquetes privados en src, reflex_app ni tests publicos de producto.
- No copiar funciones privadas para desacoplar rapido.
- No publicar configuracion interna, API keys, tokens ni URLs privadas.

## Checklist previo a cualquier push publico

- Buscar imports de paquetes privados.
- Revisar codigo copiado por contratos y comportamiento, no solo por nombre.
- Revisar capacidades reutilizables: ranking, OCR, extraction, graph analysis y evidence analysis.
- Revisar secretos, tokens, API keys, headers comerciales y URLs internas.
- Revisar docs que revelen arquitectura privada no destinada al repo publico.
- Revisar wheels, dist, paquetes privados y caches.
- Ejecutar git diff --check, py_compile, tests de fronteras, characterization, core contracts, Reflex compile y suite completa.

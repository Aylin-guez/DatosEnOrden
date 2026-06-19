# DatosEnOrden - Arquitectura

> El codigo construye el sistema. La documentacion conserva la memoria.

DatosEnOrden debe comenzar pequeno, pero no como demo desechable. La arquitectura actual esta disenada para permitir cargas iniciales controladas y evolucionar hacia APIs publicas, grafos interactivos, asistentes de IA, auditoria e historico sin reescribir todo desde cero.

## Principio central

La base de verdad no es el grafo publico. La base de verdad es la cadena:

```text
source -> dataset -> import_job -> source_record -> claim -> evidence -> relationship_public
```

El grafo publico es una proyeccion navegable derivada de claims validados.

## Capas

### 1. Fuente

`source` representa el sistema u organismo origen: ChileCompra, DIPRES, SERVEL, Consejo para la Transparencia u otro.

### 2. Dataset

`dataset` representa un recurso versionado o una ventana de carga concreta. Permite saber que se consulto, cuando, desde que URL y con que hash.

### 3. Importacion

`import_job` registra ejecuciones operativas: inicio, termino, estado, registros procesados y errores.

### 4. Registro fuente

`source_record` guarda el registro extraido antes de convertirlo en grafo. Es la pieza que evita perder trazabilidad cuando cambia el mapeo.

### 5. Entidad canonica

`entity` representa objetos reutilizables del mundo real: organismo, empresa, contrato, licitacion, persona, indicador u otros.

### 6. Claim

`claim` es una afirmacion atomica verificable.

Ejemplos:

- Organismo X emitio orden de compra Y.
- Proveedor Z recibio orden de compra Y.
- Orden de compra Y tiene monto N.

Un claim puede apuntar a otra entidad o a un valor estructurado.

### 7. Evidencia

`evidence` respalda claims y conserva vinculo a fuente, dataset y source_record. La evidencia no debe contener opiniones.

### 8. Relacion publica

`relationship_public` es la proyeccion navegable para APIs, grafos e interfaces. No es fuente de verdad.

## Estados de workflow

Estados minimos:

- `ingested`
- `normalized`
- `validated`
- `published`
- `rejected`
- `disputed`
- `withdrawn`

Estos estados permiten separar datos extraidos, datos validados y datos publicables.

## Lo que no se implementa todavia

Por pragmatismo, Fase 2.5 no agrega:

- MinIO/S3.
- Redis.
- OpenSearch.
- Neo4j.
- Blockchain.
- IA ciudadana.
- Microservicios.
- Kubernetes.

La arquitectura deja espacio para esas piezas, pero no las introduce antes de tener datos y contratos estables.

## Regla de publicacion

Un dato publico debe poder responder:

- De que fuente viene.
- Cual fue el registro original.
- Que claim se genero.
- Que evidencia lo respalda.
- Si esta validado o publicado.
- Que relacion publica derivo de ese claim.

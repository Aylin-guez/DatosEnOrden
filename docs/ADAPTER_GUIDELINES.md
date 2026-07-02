# Adapter Guidelines

## Que es un Adapter

Un Adapter es una capa tecnica pequena que conecta una fuente oficial externa con contratos internos de DatosEnOrden.

Responsabilidades:

- hablar con una fuente oficial;
- validar una entrada manual y acotada;
- parsear formatos externos;
- normalizar identificadores;
- mapear a contratos internos existentes;
- conservar trazabilidad de URL, fecha de recuperacion, formato y fuente.

Un Adapter debe ser reemplazable, testeable con fixtures pequenos y no debe modificar motores ni schema.

## Que NO debe hacer un Adapter

- No crear motores.
- No cambiar Platform Core.
- No cambiar schema.
- No llamar Reading Pipeline.
- No llamar Knowledge Engine.
- No llamar Publication Engine.
- No llamar Actualidad Engine.
- No hacer scraping.
- No recorrer historicos completos.
- No sincronizar automaticamente.
- No publicar.
- No generar interpretaciones, rankings, alertas ni inferencias.
- No resolver entidades de forma global.
- No escribir en base de datos salvo que una fase posterior lo autorice explicitamente.

## Adapter vs Engine

Un Adapter traduce una fuente externa a contratos internos.

Un Engine procesa contratos internos para producir una capacidad de producto o conocimiento.

```text
Adapter: ChileCompra XML/JSON -> contratos DEO
Engine: Knowledge Engine -> preguntas, claims, evidencia organizada
```

Regla: un Adapter no debe contener logica de negocio profunda. Si empieza a decidir significado, prioridad, narrativa o publicacion, ya esta invadiendo un Engine.

## Adapter vs Product

Un Product es una experiencia visible o empaquetada para usuarios.

Un Adapter no sabe de pantallas, rutas, reportes, SEO, biblioteca, navegacion ni acciones de usuario.

```text
Adapter: InfoLobby -> audiencias estructuradas
Product: Expediente ciudadano que muestra actividad institucional
```

Regla: un Adapter no debe construir UI ni texto ciudadano final.

## Adapter vs Platform Core

Platform Core contiene contratos, modelos compartidos, schema, persistencia y reglas transversales.

Un Adapter puede usar contratos publicados por Platform Core, pero no debe modificarlos para acomodar una fuente puntual.

Si una fuente requiere nuevos tipos o relaciones:

1. documentar la necesidad;
2. demostrar que no cabe en contratos existentes;
3. proponer cambio de Core en una fase separada;
4. no mezclar ese cambio con el Adapter.

## Arquitectura obligatoria de adapters oficiales

Todo adapter oficial futuro debe seguir esta forma:

```text
src/datosenorden/adapters/<source>/
  __init__.py
  adapter.py
  client.py
  parser.py
  mapper.py
  models.py
  README.md
```

Responsabilidades:

- `client.py`: fuente oficial, HTTP/SOAP/API/descarga puntual. No conoce DEO.
- `parser.py`: formato externo a objetos Python propios del adapter.
- `mapper.py`: objetos del adapter a contratos internos.
- `adapter.py`: orquestacion minima.
- `models.py`: dataclasses propias del adapter.
- `README.md`: alcance, limites y ejemplo minimo.

## Patron de pruebas

Cada adapter debe tener pruebas unitarias con fixtures pequenos:

- no consumir APIs masivamente;
- no depender de red para pruebas normales;
- probar normalizacion de identificadores;
- probar parseo del formato oficial;
- probar mapeo a contratos internos;
- probar limites o errores esperados.

## Futuros adapters

### ChileCompra

```text
adapters/chilecompra/
  client.py   # API Mercado Publico con ticket
  parser.py   # JSON/XML oficial a objetos ChileCompra
  mapper.py   # licitaciones/OC/proveedores a contratos DEO
```

Comenzar por codigo o fecha manual; no sincronizar Mercado Publico completo; no mezclar analisis de probidad ni evaluaciones.

### Diario Oficial

```text
adapters/diario_oficial/
  client.py   # consulta puntual por CVE/URL/fecha autorizada
  parser.py   # HTML/PDF metadata/EPUB si corresponde
  mapper.py   # publicacion oficial a documento/evidencia
```

Comenzar por CVE o URL exacta; no recorrer ediciones historicas; no extraer PDFs masivamente.

### LeyChile

```text
adapters/leychile/
  client.py   # web service LeyChile
  parser.py   # XML de norma/metadatos
  mapper.py   # norma a documento normativo y evidencia
```

Comenzar por identificador de norma; conservar version/fecha; no mezclar con Diario Oficial hasta tener contrato claro.

### DIPRES

```text
adapters/dipres/
  client.py   # dataset puntual o recurso datos.gob.cl
  parser.py   # CSV/XLS/JSON segun recurso
  mapper.py   # presupuesto/ejecucion a contratos DEO
```

Comenzar por un dataset mensual especifico; exigir diccionario de campos; no mezclar presupuesto aprobado y ejecutado sin modelo explicito.

### Contraloria

```text
adapters/contraloria/
  client.py   # consulta puntual autorizada
  parser.py   # dictamen/informe/acto
  mapper.py   # control administrativo a evidencia/claims
```

Comenzar por numero de dictamen, informe o URL exacta; no scraping de buscadores; no generar conclusiones sobre responsabilidades.

### InfoLobby

```text
adapters/infolobby/
  client.py   # catalogo CSV/XML/JSON o SPARQL puntual
  parser.py   # audiencia/viaje/donativo
  mapper.py   # actividad de lobby a contratos DEO
```

Preferir catalogo descargable puntual antes que SPARQL amplio; no construir inferencias de influencia; mantener lenguaje descriptivo.

### Portal Transparencia

```text
adapters/portal_transparencia/
  client.py   # dataset CPLT/Portal puntual
  parser.py   # CSV/XML de casos/solicitudes
  mapper.py   # solicitud/caso/organismo a contratos DEO
```

Comenzar por dataset abierto CPLT; no automatizar solicitudes ciudadanas; separar transparencia activa de casos/reclamos.

## Regla final

Un Adapter oficial debe responder una pregunta tecnica simple:

```text
Para este identificador manual, que datos oficiales existen y como se representan en contratos DEO?
```

Todo lo demas pertenece a otro componente o a una fase posterior.

# Legislative Integration Plan

Fase: Legislative Adapter Discovery / Sprint 0.

Este documento describe una integracion futura. No implementa adapter, loader, ETL, scraping, IA ni consumo API.

## Objetivo futuro

Conectar Datos Abiertos Legislativos como primera fuente documental real, preservando las fronteras actuales:

- No modificar Platform Core.
- No modificar Reading Pipeline.
- No modificar Knowledge Engine.
- No modificar Publication Engine.
- No hacer scraping.
- No descargar datos masivos.

La integracion futura deberia comenzar por un adapter documental liviano que transforme XML oficial en contratos internos ya existentes o en un contrato intermedio revisable.

## Forma esperada del flujo

```text
LegislativeAdapter
  -> Boletin / LegislativeBill
  -> Documento legislativo
  -> Tramitacion
  -> Votaciones
  -> Reading Pipeline
  -> Publication
```

Para la primera version, el adapter no deberia escribir en base de datos ni activar Knowledge Engine directamente. Debe producir una representacion estructurada, auditable y pequena.

## Adapter futuro propuesto

Nombre conceptual:

```text
LegislativeAdapter
```

Responsabilidad:

- Recibir un boletin canonico o un identificador de sesion/votacion.
- Consultar endpoints oficiales permitidos.
- Parsear XML.
- Normalizar identificadores.
- Producir objetos documentales estructurados.
- No interpretar politicamente.
- No concluir causalidad ni relevancia.

No responsabilidad:

- No Entity Resolution.
- No GraphLoader.
- No resumen automatico por IA.
- No crawling de proyectos.
- No descarga historica completa.
- No publicacion automatica.

## Entrada minima recomendada

La primera entrada futura deberia ser manual y acotada:

```text
boletin: 8575-05
source: congreso-opendata
retrieval_mode: manual_single_bill
```

El adapter deberia aceptar un boletin completo y validar:

- formato no vacio;
- numero correlativo presente;
- sufijo opcional preservado;
- normalizacion estable;
- fuente oficial declarada.

## Identificador canonico

Entidad principal:

```text
LegislativeBill
```

Identificador DEO:

```text
cl-congreso-boletin-<boletin_completo_normalizado>
```

Ejemplo:

```text
cl-congreso-boletin-8575-05
```

Aliases:

```text
8575-05
8575
```

Regla:

- `8575-05` es preferible a `8575`.
- La forma corta se guarda solo como alias si el servicio la acepta.
- El adapter no debe inventar sufijos faltantes.

## Contrato intermedio sugerido

El adapter futuro podria producir un objeto de este tipo conceptual:

```text
LegislativeSourceBundle
  source: congreso-opendata
  retrieval_date: YYYY-MM-DD
  bill:
    canonical_id
    display_id
    aliases
    title
    status
    origin
  documents:
    - document_id
      type
      source_url
      source_format
      retrieved_as
      title
      date
      related_session_id
  procedure_events:
    - event_id
      date
      chamber
      stage
      description
      source_endpoint
  votes:
    - vote_id
      date
      result
      quorum
      session_id
      article
      totals
      detail_available
  sessions:
    - session_id
      legislature_id
      number
      date
      type
      status
```

Este contrato debe quedar antes del Reading Pipeline. El Reading Pipeline deberia recibir solo documentos estructurados ya seleccionados, no ejecutar consultas a la fuente.

## Secuencia de consumo futura

### Paso 1: resolver boletin

Entrada:

```text
8575-05
```

Salida:

```text
canonical_id = cl-congreso-boletin-8575-05
```

### Paso 2: consultar votaciones Camara por boletin

Endpoint:

```text
GET /wscamaradiputados.asmx/getVotaciones_Boletin?prmBoletin=8575-05
```

Salida esperada:

- lista de votaciones;
- `Votacion.ID`;
- fecha;
- resultado;
- sesion;
- totales;
- tramite/informe/articulo.

### Paso 3: consultar detalle de votaciones seleccionadas

Endpoint:

```text
GET /wscamaradiputados.asmx/getVotacion_Detalle?prmVotacionID=<id>
```

Salida esperada:

- votos individuales;
- opcion de voto;
- diputados por `DIPID`;
- pareos.

Regla:

- Solo consultar detalle cuando el usuario o proceso manual seleccione una votacion.
- No consultar todos los detalles historicos en lote.

### Paso 4: consultar sesiones relacionadas

Si la votacion incluye `Sesion.ID`, usar:

```text
GET /wscamaradiputados.asmx/getSesionDetalle?prmSesionID=<id>
GET /wscamaradiputados.asmx/getSesionBoletinXML?prmSesionID=<id>
```

Salida esperada:

- detalle de sesion;
- boletin de sesion XML como documento legislativo.

### Paso 5: documentos para Reading Pipeline

Solo documentos seleccionados manualmente deberian pasar al Reading Pipeline.

Ejemplo conceptual:

```text
LegislativeDocument
  -> OfficialDocument
  -> Parser estructurado
  -> Fragmentos
  -> Knowledge Engine
  -> Lectura Documentada
  -> Publication
```

Regla:

- El adapter no debe llamar Reading Pipeline.
- El adapter solo prepara metadata y contenido estructurado.
- La decision de lectura/publicacion queda en el flujo documental existente.

## Mapeo a Official Document Workflow

El documento legislativo futuro deberia poder convertirse a metadata compatible:

```json
{
  "id": "cl-congreso-boletin-8575-05-session-3162",
  "title": "Boletin de sesion asociado al boletin 8575-05",
  "organization": "Camara de Diputadas y Diputados",
  "source_url": "https://opendata.camara.cl/wscamaradiputados.asmx/getSesionBoletinXML?prmSesionID=3162",
  "publication_date": "YYYY-MM-DD",
  "retrieval_date": "YYYY-MM-DD",
  "status": "incoming",
  "document_type": "legislative_session_bulletin",
  "language": "es",
  "version": 1
}
```

Este JSON es ilustrativo. No debe crearse ahora como archivo real.

## Relacion con Reading Pipeline

El Reading Pipeline existente trabaja con documentos estructurados locales. Para no modificarlo, la integracion futura debe entregar un documento ya normalizado:

```text
source XML
  -> LegislativeAdapter parsea XML
  -> OfficialDocument-compatible structure
  -> Reading Pipeline existente
```

No se debe pedir al Reading Pipeline que:

- consulte `opendata.camara.cl`;
- conozca SOAP;
- resuelva boletines;
- descargue documentos;
- interprete votaciones.

## Relacion con Publication Engine

Publication deberia recibir el resultado de Reading Pipeline, no XML crudo.

```text
LegislativeDocument selected
  -> DocumentExperience
  -> Publication
```

La publicacion debe mostrar:

- fuente oficial;
- URL consultada;
- fecha de recuperacion;
- identificador del boletin;
- identificador de sesion/votacion si aplica;
- formato original;
- limitaciones de cobertura.

## Campos minimos por tipo

### LegislativeBill

- `canonical_id`
- `display_boletin`
- `aliases`
- `source`
- `source_project_url`
- `title` si el endpoint Senado lo confirma
- `status` si el endpoint Senado lo confirma

### LegislativeVote

- `source_vote_id`
- `bill_canonical_id`
- `session_id`
- `date`
- `result`
- `quorum`
- `article`
- `procedure_stage`
- `report`
- `totals`

### LegislativeSession

- `source_session_id`
- `legislature_id`
- `number`
- `date`
- `end_date`
- `type`
- `status`

### LegislativeDocument

- `document_id`
- `bill_canonical_id`
- `session_id`
- `document_type`
- `source_url`
- `source_format`
- `retrieval_date`
- `publication_date`
- `content_hash`

## Politica de consumo

Para evitar descarga masiva:

- permitir solo boletines explicitamente solicitados;
- consultar votaciones por boletin como primer nivel;
- consultar detalles de votacion solo por seleccion;
- consultar boletin de sesion solo por sesion seleccionada;
- registrar fecha y URL de cada consulta;
- cachear manualmente solo fixtures pequenos cuando la fase tecnica lo autorice;
- no iterar legislaturas completas;
- no recorrer todos los boletines.

## Manejo de Senado

El componente Senado debe quedar como sub-adapter separado:

```text
LegislativeAdapter
  CamaraClient
  SenadoClient
```

Razon:

- Camara usa ASMX en `opendata.camara.cl`.
- Senado usa enlaces `tramitacion.senado.cl/wspublico/`.
- En esta auditoria, Senado devolvio 403 desde el navegador de investigacion.

Antes de implementarlo, una fase tecnica debe confirmar:

- metodo real de invocacion;
- parametros;
- estructura de respuesta;
- limites;
- si devuelve documentos del proyecto.

## Recomendacion de primera integracion real

Primera integracion futura recomendada:

```text
Input manual: boletin completo
  -> getVotaciones_Boletin
  -> seleccionar una votacion
  -> getVotacion_Detalle
  -> seleccionar sesion
  -> getSesionBoletinXML
  -> convertir a documento estructurado local
  -> revision manual
  -> Reading Pipeline
```

Motivo:

- usa endpoints Camara confirmados;
- evita crawl historico;
- conserva trazabilidad por boletin, votacion y sesion;
- produce un documento real para lectura documental;
- no requiere modificar Platform Core.

## No hacer en la primera integracion

- No recorrer `getLegislaturas` para descargar todas las sesiones.
- No consultar todos los detalles de todas las votaciones.
- No usar la forma corta del boletin como canonica.
- No mezclar LeyChile en la misma primera pasada.
- No publicar automaticamente.
- No generar interpretaciones politicas.
- No convertir votos en puntuaciones, riesgo o evaluaciones.

## Validacion esperada en fase tecnica futura

Cuando se autorice codigo, validar con:

- una prueba de normalizacion de boletin;
- una prueba de parseo XML pequeno;
- una prueba de mapeo a contrato intermedio;
- una prueba de conversion a `OfficialDocument` compatible;
- una prueba sin red usando fixture pequeno;
- una prueba manual opcional contra un boletin real.

## Decision final de Sprint 0

Datos Abiertos Legislativos es viable como primera fuente documental real si se trata como fuente XML oficial, no como API JSON/CSV. El identificador canonico de DEO debe ser el boletin completo normalizado. La primera integracion debe ser manual, acotada a un boletin y orientada a documentos seleccionados, no a ingestion historica.
## Adapter V1 implementado

La primera version real queda aislada en:

```text
src/datosenorden/adapters/legislature/
  __init__.py
  adapter.py
  client.py
  parser.py
  mapper.py
  models.py
  README.md
```

Responsabilidades:

- `client.py`: habla con la fuente oficial ASMX/HTTP XML. No conoce DEO.
- `parser.py`: transforma XML oficial en objetos Python propios del adapter.
- `mapper.py`: transforma objetos legislativos en contratos ETL del Platform Core.
- `adapter.py`: orquesta `load_bill(bulletin_id)`.
- `models.py`: contiene modelos propios del adapter.

La funcionalidad V1 es:

```text
LegislativeAdapter().load_bill("8575-05")
```

La salida es un `GraphBatch` del Platform Core, sin escribir en base de datos, sin publicar, sin llamar Reading Pipeline y sin llamar engines.

## Conexion posterior con Reading Pipeline

El adapter no debe llamar al Reading Pipeline. La conexion futura debe ocurrir despues de una seleccion manual de documento legislativo:

```text
LegislativeAdapter.load_bill("8575-05")
  -> GraphBatch con bill/votes/evidence
  -> seleccion manual de documento o sesion
  -> conversion controlada a OfficialDocument
  -> Reading Pipeline
```

Reglas:

- El Reading Pipeline recibe documentos estructurados, no XML crudo.
- El Reading Pipeline no conoce SOAP, ASMX, boletines ni endpoints.
- El adapter puede preparar metadata oficial y contenido estructurado.
- La decision de leer un documento debe ser explicita y acotada.

## Conexion posterior con Knowledge Engine

El Knowledge Engine no debe ser llamado por el adapter. Su entrada futura debe venir desde el Reading Pipeline o desde un contrato documental ya validado:

```text
OfficialDocument estructurado
  -> Reading Pipeline
  -> Knowledge Engine
  -> preguntas, puntos, claims y evidencia documental
```

Reglas:

- El adapter no resume.
- El adapter no interpreta intenciones legislativas.
- El adapter no genera inferencias politicas.
- El adapter conserva hechos oficiales: boletin, votacion, sesion, fecha, resultado y fuente.

## Conexion posterior con Publication Engine

El Publication Engine debe operar solo despues de una lectura documentada validada:

```text
DocumentExperience
  -> Publication Engine
  -> salida ciudadana
```

La publicacion futura debe mostrar:

- boletin canonico;
- URL oficial consultada;
- fecha de recuperacion;
- endpoint usado;
- formato original XML;
- limitaciones de cobertura;
- aviso de que no se recorrio el Congreso completo.

## Limite vigente de V1

V1 solo consulta votaciones de Camara por boletin:

```text
GET /wscamaradiputados.asmx/getVotaciones_Boletin?prmBoletin=<boletin>
```

No consulta Senado, no baja boletines de sesion, no trae detalle de cada voto y no carga datos en persistencia. Es una base minima para validar el patron oficial de adapters.
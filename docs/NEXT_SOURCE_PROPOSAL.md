# RFC: proxima fuente oficial para integrar

## Estado

Propuesta tecnica previa a implementacion. No autoriza codigo todavia.

Fuente recomendada: **InfoLobby / Lobby**.

Esta propuesta sigue `SOURCE_FACTORY.md`, `SOURCE_INTEGRATION_WORKFLOW.md`, `DEO_CONSTITUTION.md` y `TRUST_POLICY.md`. No crea motores nuevos, no agrega IA, no cambia PostgreSQL, no cambia schema y no modifica GraphLoader, Reading Pipeline, Knowledge Engine ni Publication Engine.

## 1. Por que elegir esta fuente

InfoLobby es la siguiente fuente recomendada porque combina alto valor ciudadano con bajo riesgo arquitectonico.

Razones:

- esta planificada oficialmente como fuente prioritaria;
- tiene formatos estructurados declarados en la documentacion del proyecto: CSV, XML, JSON, RDF y SPARQL;
- ya existe prototipo local `lobby` en el repo;
- ya existen conceptos, relaciones, vista de expediente, timeline y source plugin para reuniones de lobby;
- permite conectar actividad institucional recurrente sin cambiar motores;
- puede avanzar desde catalogos descargables acotados antes de usar SPARQL;
- su lenguaje ya esta tratado de forma neutral en el producto: reunion registrada, contraparte, organismo, materia y evidencia.

No se propone ChileCompra porque ya es la fuente activa principal. No se propone Diario Oficial como primera fuente nueva porque el catalogo interno lo marca como parcial y sin API confirmada. No se propone DIPRES todavia porque requiere fijar granularidad y diccionario presupuestario. No se propone Contraloria o SERVEL porque requieren auditorias tecnicas mas especificas y tienen mayor riesgo de interpretacion.

## 2. Que aporta al ciudadano

InfoLobby permite responder preguntas ciudadanas simples y verificables:

- que reuniones de lobby registra un organismo;
- con que contraparte se registro una reunion;
- sobre que materia se registro;
- en que fecha ocurrio;
- que evidencia oficial respalda el registro;
- que otras fuentes del expediente se conectan con el mismo organismo.

El aporte no es sugerir influencia ni evaluar conducta. El aporte es mostrar actividad oficial registrada y permitir revisar la fuente.

## 3. Que entidades nuevas aparecen

El prototipo actual ya modela las entidades principales:

- `PUBLIC_ORGANIZATION`: organismo publico.
- `PERSON`: persona participante cuando corresponda.
- `COMPANY`: empresa u organizacion contraparte cuando corresponda.
- `LOBBY_MEETING`: reunion registrada.

En una integracion real podrian aparecer tambien, sin cambiar schema:

- sujeto pasivo como persona o cargo asociado a organismo;
- sujeto activo como persona, empresa, asociacion u organizacion;
- materia o asunto de reunion como valor documental;
- registro oficial de audiencia, viaje o donativo si se decide ampliar despues.

La primera version debe limitarse a audiencias o reuniones. Viajes y donativos deben quedar fuera hasta una fase separada.

## 4. Que eventos del Estado puede generar

Eventos candidatos, usando tipos existentes:

- `NEW_DOCUMENT`: nuevo registro oficial de audiencia disponible como evidencia.
- `DOCUMENT_UPDATED`: registro oficial actualizado o reemplazado.
- `STATUS_CHANGED`: cambio de estado si la fuente entrega estado verificable.
- `OTHER`: evento tecnico o registro incompleto que no debe entrar al Pulso.

No se debe crear un tipo nuevo de evento. Para la primera version, "nueva reunion registrada" puede representarse como `NEW_DOCUMENT` porque el registro oficial es la evidencia primaria.

## 5. Que Topics alimentaria automaticamente

Con la configuracion actual, haria falta agregar reglas minimas a `config/topics/topics.json` en la fase de implementacion, sin cambiar el clasificador.

Topics candidatos:

- `actividad-institucional`: reuniones y actividad registrada de organismos.
- `transparencia-publica`: registros publicados bajo obligaciones de transparencia.
- `compras-publicas`: solo cuando un expediente ya conecte el mismo organismo con ChileCompra; no por inferencia automatica.
- `presupuesto-publico`: solo si el expediente combina organismo y fuentes DIPRES/ChileCompra existentes; no por el registro de lobby aislado.

La clasificacion debe basarse en `source_id`, palabras como "lobby", "audiencia", "reunion", "sujeto pasivo", "sujeto activo" y prefijos de identificador estables.

## 6. Que Lecturas podrian actualizarse

Lecturas candidatas:

- lectura de expediente institucional: agregar seccion "Reuniones registradas" cuando exista evidencia;
- lectura de seguimiento de un organismo: sumar eventos de actividad registrada a la cronologia;
- lectura ciudadana sobre transparencia institucional: explicar que registros existen y que limitaciones tienen;
- lectura de caso de demostracion Arauco u organismos similares si el registro real coincide con entidades ya persistidas.

La integracion de fuente no debe crear lecturas automaticamente. Solo debe dejar eventos y evidencia listos para que el Reading Pipeline reutilice documentos o registros seleccionados.

## 7. Que nuevos expedientes podrian enriquecerse

Expedientes enriquecibles:

- organismos publicos ya presentes por ChileCompra;
- organismos presentes en Transparencia Activa;
- autoridades o cargos presentes por SERVEL o Transparencia Activa;
- empresas ya vinculadas como proveedores si aparecen tambien como contrapartes en registros de lobby;
- expedientes institucionales que hoy tienen contratos, evidencia y timeline, pero no actividad registrada de reuniones.

El enriquecimiento debe ser descriptivo: "se registro una reunion", "se registro una contraparte", "se registro una materia". No debe afirmar influencia, conflicto, riesgo o causalidad.

## 8. Que informacion reutilizaria de la arquitectura existente

Reutiliza:

- Source Factory como puerta de entrada;
- plantilla de integracion de fuente;
- Adapter Guidelines para estructura `client.py`, `parser.py`, `mapper.py`, `adapter.py`, `models.py`;
- `GraphBatch`, `SourceRecordPayload`, `ClaimRecord`, `EvidenceRecord` y `PublicRelationshipRecord`;
- `GraphLoader` existente, sin cambios;
- Dataset Registry y source plugins;
- Investigation View, que ya tiene `lobby_items`;
- Timeline Explorer, que ya reconoce predicates de lobby;
- Source Watcher como patron de candidatos;
- State Events para convertir cambios en eventos;
- Topic Classifier y Topic Update para asociar eventos a temas;
- Daily Brief / Pulso del Estado para mostrar cambios recientes;
- Reading Pipeline, Knowledge Engine y Publication Engine solo como consumidores posteriores de evidencia ya validada.

## 9. Que adapters ya existen que podamos reutilizar

No existe un adapter oficial `src/datosenorden/adapters/infolobby/`.

Si existe material reutilizable:

- `src/datosenorden/maintenance/lobby_prototype.py`: construye `GraphBatch`, claims, evidencia y relaciones desde payload local.
- `src/datosenorden/datasets/lobby/__init__.py`: registra el dataset `lobby`.
- `docs/sources/lobby.md`: documenta estado prototipo.
- `docs/sources/README.md`: registra conceptos y comandos operativos.
- `src/datosenorden/maintenance/source_plugins.py`: define plugin `lobby`, conceptos, relaciones, evidencia y compatibilidades.
- `src/datosenorden/maintenance/investigation_view.py`: muestra `lobby_items` en expedientes.
- `src/datosenorden/maintenance/timeline_explorer.py`: ya tiene etiquetas para relaciones de lobby.

La implementacion futura deberia extraer el conocimiento del prototipo hacia un adapter real, no duplicarlo ni crear un motor nuevo.

## 10. Cambios minimos necesarios

Cambios minimos para una fase posterior:

1. Crear `src/datosenorden/adapters/infolobby/` con estructura estandar.
2. Definir modelos propios del adapter para audiencia/reunion.
3. Implementar cliente acotado para archivo descargable o recurso oficial puntual.
4. Implementar parser para CSV/XML/JSON oficial, empezando por un formato.
5. Implementar mapper hacia contratos existentes.
6. Reutilizar predicates actuales:
   - `ORGANIZATION_HELD_LOBBY_MEETING`
   - `COUNTERPARTY_PARTICIPATED_IN_LOBBY`
   - `LOBBY_MEETING_ABOUT_SUBJECT`
7. Reemplazar marcadores `LOCAL_TEST_DATA` / `NOT_OFFICIAL_DATA` por metadatos oficiales cuando se use fuente real.
8. Agregar fixtures pequenos de fuente real permitida o fixture sanitizado marcado con origen.
9. Agregar tests del adapter.
10. Agregar watcher acotado para detectar registros nuevos o actualizados desde un catalogo seleccionado.
11. Agregar reglas minimas de topic/evento en configuracion, sin cambiar motores.
12. Actualizar documentacion de fuente y estado de registry cuando la integracion pase validacion.

No se requiere cambiar schema, GraphLoader, Knowledge Engine, Publication Engine ni Reading Pipeline.

## 11. Riesgos

### Riesgo de inferencia

Los registros de lobby pueden ser malinterpretados como influencia, conflicto o irregularidad. DEO debe evitar ese lenguaje. La fuente solo permite decir que una reunion fue registrada con determinados participantes, fecha y materia.

### Riesgo de datos personales

Puede haber personas naturales. La integracion debe limitarse a datos oficialmente publicados y evitar enriquecer perfiles personales fuera del contexto documental.

### Riesgo de identificadores

La estabilidad de IDs debe confirmarse por catalogo. Si no hay ID estable, debe construirse una clave documentada desde organismo, fecha, contraparte y registro oficial, conservando URL y hash.

### Riesgo de volumen

No se debe descargar todo el historico. La primera version debe usar una muestra acotada, un periodo corto o un archivo oficial seleccionado.

### Riesgo de cambios de formato

InfoLobby ofrece varios formatos. La primera integracion debe elegir uno y documentar limites. No debe intentar soportar CSV, XML, JSON, RDF y SPARQL al mismo tiempo.

### Riesgo de mezcla de dominios

No se debe cruzar Lobby con ChileCompra, DIPRES o Contraloria para sugerir causalidad. Los cruces solo pueden aparecer como coexistencia documental en un expediente.

## 12. Flujo completo propuesto

```text
InfoLobby
-> Adapter infolobby
-> Watcher acotado de registros seleccionados
-> ChangeCandidate
-> State Event
-> Topic
-> Topic Update
-> Reading Pipeline solo si hay lectura seleccionada
-> Knowledge Engine como consumidor de evidencia ya estructurada
-> Publication Engine solo para lectura validada
-> Home
-> Pulso del Estado
-> Ciudadano
```

## Detalle del flujo

### Fuente

Fuente oficial: InfoLobby.

Entrada inicial recomendada: catalogo descargable oficial de audiencias/reuniones, no SPARQL amplio y no crawling historico.

### Adapter

El adapter recibe archivo o respuesta oficial acotada, parsea registros y produce contratos internos. No publica, no clasifica politicamente y no decide relevancia.

### Watcher

El watcher compara registros observados con source records existentes. Produce candidatos nuevos, actualizados o ignorados.

### State Event

Cada registro nuevo o actualizado se convierte en evento descriptivo con evidencia disponible.

### Topic

El Topic Classifier asocia el evento a actividad institucional o transparencia publica usando reglas locales.

### Reading

Solo se activa cuando una persona decide crear o actualizar una Lectura Documentada sobre un organismo, tema o expediente.

### Knowledge

Knowledge Engine puede organizar preguntas y evidencia desde claims ya estructurados. No debe consultar InfoLobby ni decidir interpretaciones.

### Publication

Publication Engine publica solo lecturas validadas con evidencia y limitaciones.

### Home

Home puede mostrar cambios recientes si Daily Brief recibe eventos de calidad suficiente.

### Pulso del Estado

El Pulso puede mostrar: "Se registro una nueva reunion de lobby asociada a un organismo", con enlace a evidencia. No debe mostrar titulares interpretativos.

## Decision recomendada

La siguiente fuente oficial debe ser **InfoLobby / Lobby**.

Es la mejor candidata para demostrar que Source Factory funciona porque:

- ya esta planificada;
- tiene formatos estructurados;
- reutiliza la arquitectura existente;
- ya tiene prototipo y superficie de producto;
- aporta valor ciudadano directo;
- permite una implementacion acotada sin motores nuevos;
- obliga a practicar neutralidad, evidencia cercana y limitaciones visibles.

## Condicion antes de implementar

Antes de programar, completar una ficha de fuente basada en `docs/templates/SOURCE_INTEGRATION_TEMPLATE.md` con:

- URL oficial exacta del catalogo elegido;
- formato inicial elegido;
- licencia o condiciones de reutilizacion;
- identificador estable;
- campos minimos;
- limites de privacidad;
- ejemplo pequeno;
- criterio de watcher;
- criterios de exclusion del Pulso.

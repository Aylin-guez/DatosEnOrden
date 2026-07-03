# State Domain Model

Este documento propone el modelo conceptual de **Dominio del Estado** para que DatosEnOrden pueda crecer durante anos sin reorganizar temas cada vez que se integre una nueva fuente oficial.

No define codigo. No modifica Source Watcher, Topic Classifier, State Events, GraphLoader, Reading Pipeline, Knowledge Engine, Publication Engine, PostgreSQL ni schema.

## Decision central

DatosEnOrden debe introducir una capa conceptual permanente entre Estado y Tema:

```text
Estado
-> Dominio del Estado
-> Tema
-> Evento
-> Documento Fuente
-> Evidencia
-> Lectura Documentada
-> Ciudadano
```

El Dominio no reemplaza al Tema. Lo gobierna.

El problema actual no es que existan temas. El problema es que, sin una capa superior estable, los temas pueden empezar a crecer como una lista reactiva a fuentes nuevas. Si cada fuente crea sus propios temas sin una taxonomia permanente, DEO terminara organizando la memoria del Estado por origen tecnico, no por comprension ciudadana.

## 1. Que es un Dominio del Estado

Un Dominio del Estado es una gran area permanente de accion publica.

Representa una zona estable donde el Estado legisla, administra, compra, fiscaliza, presupuestan recursos, publica documentos, registra actividad o toma decisiones.

Un Dominio debe cumplir estas condiciones:

- existe aunque no haya eventos recientes;
- puede recibir informacion desde muchas fuentes oficiales;
- contiene muchos temas de largo plazo;
- permite agrupar eventos sin convertirlos en una lista desordenada;
- usa lenguaje ciudadano y estable;
- no depende de un organismo especifico;
- no depende de un formato de fuente;
- no depende de una coyuntura.

Ejemplos razonables de Dominio pueden ser:

- Actividad Legislativa
- Presupuesto Publico
- Compras Publicas
- Transparencia
- Justicia y Control
- Seguridad
- Salud
- Educacion
- Economia
- Vivienda
- Medio Ambiente
- Relaciones Internacionales
- Infraestructura
- Ciencia e Innovacion
- Gobierno Local
- Procesos Electorales

Esta lista no debe considerarse definitiva. El criterio no es cubrir ministerios, sino ordenar la memoria publica de forma comprensible y durable.

## 2. Diferencia entre Dominio y Tema

Un Dominio es una categoria permanente de memoria estatal.

Un Tema es una historia publica concreta dentro de uno o mas dominios.

Ejemplo:

```text
Dominio: Presupuesto Publico
Tema: Financiamiento hospitalario en la Region del Biobio
Evento: DIPRES publica ejecucion presupuestaria mensual
Documento Fuente: archivo oficial de ejecucion presupuestaria
Evidencia: fila, campo, fecha, URL y periodo
Lectura: explicacion ciudadana del cambio presupuestario
```

Otro ejemplo:

```text
Dominio: Transparencia
Tema: Actividad registrada de lobby en organismos de salud
Evento: InfoLobby publica una audiencia registrada
Documento Fuente: registro oficial de audiencia
Evidencia: ID, fecha, organismo, contraparte, materia y URL
Lectura: explicacion de que registros existen y como verificarlos
```

La diferencia practica:

- Dominio responde: "En que gran area del Estado ocurre esto?"
- Tema responde: "Que historia publica estamos siguiendo?"
- Evento responde: "Que cambio oficial ocurrio?"
- Documento Fuente responde: "Donde esta publicado?"
- Evidencia responde: "Que respalda esta afirmacion?"
- Lectura responde: "Como lo entiende una persona?"

## 3. Cuando nace un Tema

Un Tema nace cuando existe una historia publica verificable que probablemente acumulara eventos en el tiempo.

No basta con que exista una fuente nueva. No basta con que exista un documento aislado. No basta con que haya una noticia externa.

Un Tema puede nacer cuando:

- hay un asunto publico con continuidad probable;
- existe al menos una fuente oficial verificable;
- hay un documento, registro o evento inicial con evidencia;
- el asunto puede explicarse sin opinion ni inferencia;
- el ciudadano puede entender por que conviene seguirlo;
- se puede ubicar dentro de uno o mas dominios;
- hay criterios para actualizarlo con eventos futuros.

Un Tema no debe nacer solo para acomodar una fuente tecnica. Por ejemplo, "Registros XML de fuente X" no es un Tema. "Tramitacion de una reforma legal" o "actividad registrada de un organismo" si puede serlo.

## 4. Cuando un evento actualiza un Tema existente

Un evento actualiza un Tema existente cuando agrega continuidad a una historia ya abierta.

Criterios:

- comparte el mismo asunto publico;
- pertenece al mismo ciclo documental o administrativo;
- afecta el mismo expediente, organismo, norma, programa, proceso o territorio;
- usa identificadores que conectan con eventos anteriores;
- proviene de una fuente oficial compatible con el Tema;
- no cambia el significado central del Tema;
- puede agregarse a la cronologia sin crear confusion.

Ejemplo:

- una nueva votacion actualiza un Tema legislativo existente;
- una nueva ejecucion mensual actualiza un Tema presupuestario existente;
- una nueva audiencia registrada actualiza un Tema de actividad institucional;
- una publicacion del Diario Oficial actualiza un Tema normativo ya seguido.

La pregunta de control es:

```text
Si agrego este evento a la cronologia del Tema, la historia se entiende mejor?
```

Si la respuesta es si, el evento actualiza el Tema.

## 5. Cuando debe crearse un Tema nuevo

Debe crearse un Tema nuevo cuando el evento documenta una historia distinta, aunque comparta fuente, dominio u organismo.

Criterios para crear Tema:

- el evento abre un asunto publico con continuidad propia;
- mezclarlo con un Tema existente volveria confusa la cronologia;
- tiene actores, documentos o proceso principal distinto;
- requiere preguntas ciudadanas propias;
- tiene criterios de actualizacion distintos;
- podria recibir eventos futuros desde varias fuentes;
- necesita una Lectura Documentada distinta.

No debe crearse un Tema nuevo cuando:

- solo cambia el formato de la fuente;
- solo aparece un nuevo documento de respaldo para el mismo asunto;
- solo cambia una fecha o estado dentro de un proceso ya seguido;
- solo hay un evento aislado sin continuidad probable;
- la diferencia es editorial, no documental.

## 6. Puede un Tema pertenecer a mas de un Dominio

Si. Un Tema puede pertenecer a mas de un Dominio.

Pero debe tener:

- un Dominio principal;
- dominios secundarios opcionales;
- una razon documentada para cada dominio secundario.

El Dominio principal define donde vive la lectura publica principal. Los dominios secundarios permiten descubrir el Tema desde otras areas.

Ejemplo:

```text
Tema: Construccion de un hospital publico
Dominio principal: Salud
Dominios secundarios: Presupuesto Publico, Compras Publicas, Infraestructura
```

Esto evita duplicar el mismo Tema como cuatro temas separados. La historia es una; las puertas de entrada son varias.

## 7. Puede un Evento alimentar varios Temas

Si, pero debe ser excepcional y trazable.

Un Evento puede alimentar varios Temas cuando el mismo cambio oficial tiene relevancia documental directa para historias distintas.

Ejemplo:

- una ley publicada puede actualizar el Tema "tramitacion de la ley" y tambien un Tema sectorial afectado por esa ley;
- una orden de compra puede actualizar el Tema de un organismo y tambien el Tema de un programa publico especifico;
- una audiencia registrada puede actualizar actividad institucional y un expediente de un organismo.

Reglas:

- el Evento debe conservar un identificador unico;
- cada asociacion a Tema debe explicar por que corresponde;
- no se debe duplicar la evidencia;
- no se debe transformar una relacion indirecta en conclusion;
- si la relacion es debil, el evento debe alimentar solo el Tema principal.

## 8. Como una fuente oficial decide que Dominios alimenta

Una fuente oficial no "decide" por si sola. DEO debe declarar, antes de implementar, que dominios puede alimentar esa fuente.

La ficha Source Factory de cada fuente debe indicar:

- dominio principal;
- dominios secundarios posibles;
- tipos de eventos que puede generar;
- tipos de documentos fuente;
- entidades principales;
- limites de interpretacion;
- criterios de exclusion del Pulso;
- temas que puede actualizar automaticamente;
- temas que solo puede sugerir para revision humana.

Ejemplos:

| Fuente | Dominio principal | Dominios secundarios posibles |
| --- | --- | --- |
| ChileCompra | Compras Publicas | Salud, Educacion, Infraestructura, Gobierno Local |
| Diario Oficial | Actividad Normativa | Justicia y Control, Economia, Salud, Educacion, Medio Ambiente |
| DIPRES | Presupuesto Publico | Salud, Educacion, Infraestructura, Vivienda |
| InfoLobby | Transparencia | Actividad Institucional, Salud, Economia, Gobierno Local |
| SERVEL | Procesos Electorales | Gobierno Local, Actividad Politica Institucional |
| Contraloria | Justicia y Control | Gobierno Local, Compras Publicas, Presupuesto Publico |
| Transparencia | Transparencia | Gobierno Local, Salud, Educacion, Compras Publicas |
| BCN | Actividad Legislativa | Actividad Normativa, Justicia y Control |
| Municipalidades | Gobierno Local | Compras Publicas, Presupuesto Publico, Infraestructura |

La fuente no debe crear dominios nuevos durante la ingestion. Si una fuente parece no caber en ningun Dominio, eso es una decision de arquitectura, no una excepcion tecnica.

## 9. Convivencia con Source Factory

Source Factory debe incorporar Dominio como decision previa a Tema.

El flujo conceptual quedaria:

```text
Fuente Oficial
-> Adapter
-> Watcher
-> State Event
-> Dominio
-> Tema
-> Documento Fuente
-> Evidencia
-> Pulso del Estado
-> Lectura Documentada
-> Ciudadano
```

En Source Factory, cada nueva fuente debe responder:

- que dominios puede alimentar;
- que dominios no debe alimentar;
- que temas existentes puede actualizar;
- que eventos podrian sugerir temas nuevos;
- que limites impiden clasificacion automatica.

Esto evita que una fuente nueva llegue directamente a "crear topics". Primero se declara su papel dentro de la memoria del Estado.

## 10. Convivencia con State Events

State Events siguen siendo la unidad de cambio.

El Dominio no reemplaza el evento ni cambia su funcion. Agrega contexto estable:

```text
Evento = que cambio
Tema = que historia actualiza
Dominio = en que area permanente del Estado vive esa historia
```

Un State Event deberia poder responder:

- source_id;
- external_id;
- event_type;
- document_available;
- evidence_available;
- topic_id;
- domain_id o dominios asociados.

No es necesario crear tipos de evento nuevos por Dominio. Los tipos existentes pueden seguir funcionando. Un `NEW_DOCUMENT` puede ocurrir en Transparencia, Presupuesto, Salud o Justicia. El tipo describe la forma del cambio; el Dominio describe el area de memoria.

## 11. Convivencia con Topic Update

Topic Update seguiria actualizando el estado operativo del Tema.

Con Dominio, el update deberia ubicarse dentro de una jerarquia:

```text
domain_id
topic_id
latest_event
status
timeline_event
```

La regla importante: Topic Update no debe inventar Dominios. Debe usar dominios declarados en la configuracion de temas o en la ficha de fuente.

Si un evento no puede clasificarse con confianza:

- puede quedar asociado solo a la fuente y evento;
- puede ir a revision;
- puede usar un Dominio "por determinar" solo como estado interno temporal;
- no debe aparecer como Lectura Documentada principal.

## 12. Como cambia la experiencia publica

La experiencia publica gana una capa de orientacion.

Hoy una persona puede ver:

```text
Pulso -> Evento -> Lectura
```

Con Dominio, la persona podria entender:

```text
Pulso -> Dominio -> Tema -> Lectura
```

Esto no significa agregar pantallas tecnicas. Publicamente, Dominio puede funcionar como:

- filtro de Pulso;
- agrupador en Home;
- seccion en Mas lecturas;
- contexto dentro de una Lectura;
- puerta de entrada desde Fuentes oficiales.

La persona no necesita saber de adapters, engines ni datasets. Si ve "Presupuesto Publico" o "Transparencia", entiende el tipo de asunto antes de abrir la lectura.

## 13. Como cambia Pulso del Estado

Pulso del Estado debe dejar de ser solo una lista cronologica.

Con Dominio, Pulso puede responder:

- que cambio recientemente;
- en que Dominio ocurrio;
- que Tema actualiza;
- que fuente oficial lo respalda;
- si hay documento fuente;
- si existe lectura disponible;
- si el evento esta pendiente de lectura.

Ejemplo conceptual:

```text
Dominio: Transparencia
Tema: Actividad registrada de organismos de salud
Evento: Se registro una nueva audiencia en InfoLobby
Fuente: InfoLobby
Accion: Entender contexto
```

Pulso no debe convertirse en dashboard. Dominio ayuda a escanear sin perder la ruta hacia la lectura.

## 14. Como cambia Daily Brief

Daily Brief debe agrupar eventos recientes por Dominio y luego por Tema.

Orden recomendado:

```text
Dominio
-> Temas con cambios
-> Eventos recientes
-> Fuente y evidencia
-> Ruta a lectura o cronologia
```

Esto evita que un dia con 200 eventos de 10 fuentes parezca una lista plana.

Daily Brief debe conservar una regla:

- un evento sin evidencia suficiente no debe entrar;
- un evento sin Tema claro puede aparecer solo como pendiente interno;
- un Dominio con demasiados eventos debe resumirse por Tema, no por fuente.

## 15. Como cambia una Lectura Documentada

Una Lectura Documentada debe declarar su ubicacion:

```text
Dominio principal
Tema
Eventos recientes
Documento Fuente
Evidencia
Cronologia
Expediente relacionado
```

La Lectura no debe explicar "la arquitectura". Debe usar el Dominio para orientar:

- "Esta lectura pertenece a Presupuesto Publico";
- "Tambien se relaciona con Salud";
- "Los cambios recientes vienen de DIPRES y Diario Oficial";
- "La evidencia esta en estos documentos fuente".

Cuando cambian eventos relevantes, la Lectura puede requerir:

- aviso de actualizacion;
- nueva seccion de cronologia;
- revision de limitaciones;
- republicacion o regeneracion controlada.

La Lectura no cambia por cada evento menor. Cambia cuando el evento altera el estado comprensible del Tema.

## 16. Como cambia el seguimiento historico

El seguimiento historico debe pasar de:

```text
Tema -> lista de eventos
```

a:

```text
Dominio -> Tema -> Cronologia de eventos -> Documentos -> Evidencia
```

Esto permite:

- comparar temas dentro del mismo Dominio;
- revisar continuidad por fuente;
- detectar temas dormidos pero no muertos;
- separar eventos tecnicos de eventos publicables;
- preservar historia aunque una fuente cambie;
- evitar que documentos antiguos queden aislados.

Un Tema puede estar inactivo durante meses o anos, pero no muere. El Dominio sigue siendo su ubicacion estable.

## 17. Impacto con muchas fuentes integradas

Cuando existan ChileCompra, Diario Oficial, DIPRES, Lobby, SERVEL, Contraloria, Transparencia, BCN y Municipalidades al mismo tiempo, Dominio evita que la organizacion dependa de la fuente.

### ChileCompra

Dominio principal: Compras Publicas.

Puede alimentar temas sobre adquisiciones, proveedores, licitaciones, contratos y organismos compradores. Tambien puede conectar con Salud, Educacion o Infraestructura cuando el expediente lo justifique.

### Diario Oficial

Dominio principal: Actividad Normativa o Documentos Oficiales del Estado.

Puede actualizar temas legislativos, normativos, nombramientos, decretos, resoluciones y publicaciones sectoriales. Debe operar por CVE o documento acotado, no por barrido masivo.

### DIPRES

Dominio principal: Presupuesto Publico.

Puede alimentar temas sobre ejecucion presupuestaria, programas, partidas y organismos. Requiere diccionario cerrado para no mezclar presupuesto aprobado, ejecutado y transferido.

### Lobby

Dominio principal: Transparencia.

Puede alimentar actividad institucional registrada. Debe evitar cualquier lenguaje que sugiera influencia, conflicto o causalidad.

### SERVEL

Dominio principal: Procesos Electorales.

Puede alimentar resultados historicos, autoridades electas, periodos y documentos electorales. Debe excluir datos personales no necesarios y priorizar agregados o registros oficiales publicables.

### Contraloria

Dominio principal: Justicia y Control.

Puede alimentar dictamenes, informes, toma de razon y observaciones. Debe tratar cada documento como evidencia oficial sin convertir observaciones en conclusiones propias.

### Transparencia

Dominio principal: Transparencia.

Puede alimentar solicitudes, casos, transparencia activa, cargos, organigramas y registros institucionales. Debe distinguir transparencia activa, solicitudes y decisiones.

### BCN

Dominio principal: Actividad Legislativa.

Puede alimentar normas, historia legislativa, informes y recursos parlamentarios. Debe separarse LeyChile, datos legislativos y documentos contextuales.

### Municipalidades

Dominio principal: Gobierno Local.

Puede alimentar temas territoriales, gasto municipal, proyectos, ordenanzas, compras y documentos locales. Debe evitar mezclar municipios como si fueran una fuente uniforme; cada municipio puede tener calidad documental distinta.

## Modelo conceptual propuesto

### Estado

El conjunto de instituciones, documentos, registros y decisiones oficiales que DEO observa.

Proposito: mantener la memoria viva del Estado como totalidad, sin depender de una fuente aislada.

### Dominio del Estado

Gran area permanente de accion estatal.

Proposito: dar estabilidad a la organizacion, agrupar temas por sentido publico y evitar que nuevas fuentes creen desorden.

### Tema

Historia publica persistente dentro de uno o mas dominios.

Proposito: acumular eventos, documentos y evidencia en torno a un asunto comprensible.

### Evento

Cambio oficial observado desde una fuente.

Proposito: registrar que algo ocurrio, cuando, desde que fuente y con que evidencia.

### Documento Fuente

Documento, registro, expediente, publicacion o recurso oficial que respalda el evento.

Proposito: conservar prioridad documental y permitir verificacion directa.

### Evidencia

Referencia verificable que conecta una afirmacion con el documento o registro.

Proposito: sostener afirmaciones concretas sin reemplazar el documento.

### Lectura Documentada

Explicacion ciudadana basada en documentos y evidencia.

Proposito: permitir comprension sin perder trazabilidad.

### Ciudadano

Persona que necesita entender que cambio, por que contexto documental importa y donde puede comprobarlo.

Proposito: orientar la experiencia hacia comprension verificable, no hacia navegacion tecnica.

## Reglas permanentes

### Reglas de Dominio

- Un Dominio debe ser estable durante anos.
- Un Dominio no debe nacer por una sola fuente.
- Un Dominio no debe depender de un ministerio especifico.
- Un Dominio debe tener nombre ciudadano, no tecnico.
- Un Dominio puede recibir eventos desde muchas fuentes.
- Un Dominio puede contener temas activos, inactivos y emergentes.
- Un Dominio no publica afirmaciones; solo organiza memoria.
- Cambiar la lista de Dominios debe ser una decision de arquitectura, no una consecuencia de ingestion.

### Reglas de Tema

- Un Tema vive mientras exista historia documental posible.
- Un Tema debe tener un Dominio principal.
- Un Tema puede tener dominios secundarios si hay relacion documental clara.
- Un Tema debe tener criterios de actualizacion.
- Un Tema no debe duplicarse por fuente.
- Un Tema no debe crearse para cada evento aislado.
- Un Tema debe poder explicarse a una persona sin nombrar pipelines ni datasets.
- Un Tema puede dormir, pero no debe borrarse solo por falta de novedades.

### Reglas de Evento

- Un Evento representa un cambio oficial.
- Un Evento debe tener fuente, fecha, identificador y evidencia o limitacion explicita.
- Un Evento puede actualizar un Tema existente o sugerir uno nuevo.
- Un Evento no debe crear Tema automaticamente si la continuidad no esta clara.
- Un Evento puede alimentar mas de un Tema solo con razon documentada.
- Un Evento tecnico o ambiguo puede quedar fuera del Pulso.
- Un Evento no debe contener opinion ni inferencia.

### Reglas de Documento Fuente

- El Documento Fuente tiene prioridad sobre cualquier explicacion.
- Un Documento Fuente puede respaldar muchos eventos.
- Un Documento Fuente puede pertenecer a varios temas, pero no debe duplicarse sin razon.
- Si el documento cambia, DEO debe preservar historial cuando sea posible.
- Un resumen nunca reemplaza al Documento Fuente.

### Reglas de Evidencia

- La Evidencia debe estar cerca de la afirmacion que sostiene.
- La Evidencia debe permitir llegar al documento, registro o campo original.
- La Evidencia no reemplaza al Documento Fuente.
- Si la evidencia es insuficiente, la afirmacion se reduce o no se publica.
- La evidencia contradictoria debe mostrarse como condicion documental, no resolverse por opinion.

### Reglas de Lectura

- Una Lectura Documentada pertenece a un Tema.
- Una Lectura debe mostrar Dominio principal y relacion con dominios secundarios cuando ayude.
- Una Lectura se actualiza cuando eventos nuevos cambian la comprension documentada del Tema.
- Una Lectura no debe actualizarse por eventos menores que no cambian la lectura ciudadana.
- Una Lectura debe conservar fuente, evidencia, limitaciones y cronologia.
- Una Lectura no debe esconder incertidumbre.

### Reglas de Pulso y Daily Brief

- Pulso muestra cambios recientes agrupables por Dominio y Tema.
- Daily Brief debe evitar listas planas cuando el volumen crezca.
- Un evento entra al Pulso solo si tiene suficiente evidencia y ruta de contexto.
- El Pulso no debe ser una pagina de eventos tecnicos.
- Daily Brief debe resumir sin convertir eventos en conclusiones.

### Reglas de Fuente

- Una fuente debe declarar dominios antes de generar temas.
- Una fuente puede alimentar varios dominios, pero debe tener uso principal.
- Una fuente no debe crear Dominios nuevos durante procesamiento.
- Una fuente no debe mezclar dominios sin trazabilidad.
- Una fuente nueva debe integrarse por Source Factory, no por excepcion.

## Correccion a la propuesta inicial

La propuesta "Estado -> Dominio -> Tema -> Evento" es correcta, pero necesita dos precisiones:

1. Dominio no debe ser una lista fija cerrada desde el inicio.
2. Dominio no debe sustituir `category_id` tecnicamente hasta que exista una fase de migracion.

En el corto plazo, Dominio puede vivir como modelo conceptual y luego mapearse a configuracion. En el largo plazo, `category_id` podria evolucionar hacia `domain_id`, pero eso debe decidirse en una fase tecnica separada.

## Respuesta fundamental

Si se aplica con disciplina, este modelo si puede permitir que DEO crezca hasta cientos de miles de documentos oficiales sin perder orden.

La razon es que separa tres cosas que hoy podrian confundirse:

- Dominio: area permanente del Estado.
- Tema: historia publica de largo plazo.
- Evento: cambio oficial puntual.

Esa separacion evita que:

- cada fuente cree su propia taxonomia;
- cada evento cree un tema;
- cada documento quede aislado;
- cada lectura tenga que reorganizarse por volumen;
- el Pulso se vuelva una lista inmanejable;
- los temas se dupliquen por dominio tecnico.

Pero el modelo solo funcionara si DEO respeta estas condiciones:

- pocos Dominios, estables y bien nombrados;
- Temas con criterios de nacimiento y actualizacion;
- Eventos deduplicados y trazables;
- fuentes declarando dominios antes de implementarse;
- documentos y evidencia preservados cerca de la explicacion;
- lecturas que cambian por significado documental, no por ruido.

El riesgo principal es convertir Dominio en una lista demasiado grande o demasiado parecida a ministerios. Si eso ocurre, DEO solo habra reemplazado el desorden de temas por desorden de dominios. Por eso la regla debe ser estricta: un Dominio existe para ordenar memoria publica durante anos, no para acomodar una fuente o una coyuntura.

## Decision recomendada

Adoptar State Domain como capa conceptual permanente.

Primera version sugerida:

- definir dominios en documentacion antes de codigo;
- exigir dominio principal en cada ficha Source Factory futura;
- exigir dominio principal en cada Tema nuevo;
- permitir dominios secundarios solo con justificacion;
- agrupar Pulso y Daily Brief por Dominio cuando la fase tecnica lo permita;
- no cambiar motores ni schema hasta que el modelo sea revisado.

La arquitectura futura deberia proteger esta jerarquia:

```text
Estado
-> Dominio estable
-> Tema vivo
-> Evento verificable
-> Documento Fuente prioritario
-> Evidencia cercana
-> Lectura Documentada
-> Ciudadano orientado
```

Ese es el camino mas solido para que DatosEnOrden siga siendo una memoria viva del Estado y no una coleccion creciente de datasets.

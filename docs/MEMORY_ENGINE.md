# Memory Engine V1

Memory Engine es el modelo conceptual que explica como crece la memoria del Estado en DatosEnOrden cuando llegan nuevos eventos oficiales.

No define codigo. No crea adapters. No crea pipelines. No modifica PostgreSQL. No crea schema. No reemplaza Source Watcher, State Events, Topic Update, Daily Brief, Reading Pipeline, Knowledge Engine ni Publication Engine.

## Decision central

El centro de DatosEnOrden ya no son los temas.

El centro son los **Eventos del Estado**.

Un tema sigue siendo necesario para organizar historias publicas de largo plazo, pero ya no debe tratarse como la unidad primaria del sistema. Un tema es una vista persistente construida desde eventos, documentos y evidencia. Una Lectura Documentada tambien es una vista construida sobre esa memoria.

La memoria crece cuando el Estado produce cambios observables desde fuentes oficiales.

```text
Fuente Oficial
-> Watcher
-> State Event
-> Memory Engine
-> Dominio
-> Tema
-> Cronologia
-> Lectura Documentada
-> Pulso del Estado
-> Ciudadano
```

## Que es la Memoria del Estado

La Memoria del Estado no es una base de datos.

No es un buscador.

No es una IA.

Es el historial verificable de todo lo que ha ocurrido y ha sido observado por DatosEnOrden mediante documentos, registros y fuentes oficiales.

La memoria existe para conservar continuidad documental:

- que ocurrio;
- cuando fue observado;
- que fuente oficial lo publico;
- que documento o registro lo respalda;
- que entidades participan;
- que temas o dominios se ven afectados;
- que cronologias deben actualizarse;
- que lecturas pueden necesitar revision;
- que puede verificar una persona.

La memoria no intenta producir una conclusion. Conserva hechos oficiales observados y sus relaciones verificables.

## Unidad minima

La unidad minima de memoria es el **State Event**.

Un State Event representa un cambio oficial observado desde una fuente oficial. Puede tener documento fuente completo, registro estructurado, fragmento, identificador, URL o evidencia parcial marcada con limitaciones.

Ejemplos de State Event:

- nuevo proyecto ingresado;
- nueva votacion;
- nuevo decreto;
- nuevo oficio;
- nueva compra publica;
- nuevo informe de Contraloria;
- nuevo nombramiento;
- nueva renuncia;
- nueva declaracion;
- nuevo presupuesto;
- nueva resolucion;
- nuevo dictamen;
- nuevo registro de lobby;
- nueva publicacion en Diario Oficial;
- nueva actualizacion de estado;
- nuevo documento asociado a un expediente.

Un tema puede recibir muchos eventos. Un documento puede respaldar varios eventos. Una entidad puede participar en miles de eventos. Pero el hecho minimo que hace crecer la memoria es el evento.

## Que hace el Memory Engine

Memory Engine actua despues de que existe un State Event.

Su trabajo no es interpretar el evento. Su trabajo es conectarlo con la memoria existente.

Cuando aparece un evento, Memory Engine debe:

1. Registrar el evento como hecho observado.
2. Relacionarlo con entidades conocidas.
3. Relacionarlo con documentos fuente o registros oficiales.
4. Relacionarlo con fuentes oficiales.
5. Actualizar cronologias afectadas.
6. Actualizar temas afectados.
7. Actualizar dominios del Estado cuando corresponda.
8. Actualizar el Pulso del Estado si el evento cumple criterios de evidencia y relevancia publica.
9. Marcar lecturas relacionadas que pueden requerir actualizacion.
10. Preservar trazabilidad entre evento, fuente, documento, evidencia, entidad, tema y lectura.

Todo esto ocurre sin IA.

Todo ocurre mediante relaciones declaradas, identificadores, reglas, configuracion y evidencia oficial.

## Que NO hace

Memory Engine nunca debe:

- resumir documentos;
- interpretar intenciones;
- redactar lecturas;
- generar conclusiones;
- clasificar politicamente;
- asignar culpa, merito, riesgo o sospecha;
- publicar automaticamente;
- reemplazar la fuente oficial;
- reemplazar el documento fuente;
- decidir por si solo que una lectura esta lista para publicarse;
- borrar eventos anteriores;
- reescribir la historia para que parezca mas simple;
- resolver contradicciones oficiales por opinion.

Memory Engine organiza memoria. No produce relato editorial.

## Que consume

Memory Engine consume **State Events**.

Un State Event debe aportar, cuando exista:

- identificador del evento;
- tipo de evento;
- fuente oficial;
- identificador externo;
- fecha del hecho, publicacion, actualizacion u observacion;
- titulo o descripcion neutral;
- URL oficial o punto de consulta;
- documento fuente asociado;
- evidencia disponible;
- entidades detectadas o referenciadas;
- dominio o tema sugerido por reglas existentes;
- limitaciones conocidas.

Si un evento no tiene evidencia suficiente, Memory Engine puede conservarlo como evento observado limitado, pero no debe promoverlo automaticamente a Pulso, Lectura o publicacion.

## Que produce

Memory Engine produce memoria enriquecida.

Su salida conceptual incluye:

- eventos preservados;
- relaciones entre eventos;
- relaciones entre eventos y entidades;
- relaciones entre eventos y documentos fuente;
- relaciones entre eventos y fuentes oficiales;
- cronologias actualizadas;
- temas actualizados;
- dominios alimentados;
- Pulso del Estado actualizado;
- lecturas relacionadas marcadas como vigentes, pendientes o afectadas;
- rutas de verificacion para ciudadanos;
- limitaciones y contradicciones documentales preservadas.

La salida no es una publicacion automatica. Es una memoria mas conectada y mas verificable.

## Relacion con otros motores

Memory Engine vive despues de State Events y antes de las vistas publicas o productos de lectura.

```text
Fuente Oficial
-> Adapter
-> Source Watcher
-> State Event
-> Memory Engine
-> Topic Update
-> Daily Brief
-> Reading Pipeline
-> Knowledge Engine
-> Publication Engine
-> Ciudadano
```

La version conceptual para el ciudadano es mas simple:

```text
Source
-> Watcher
-> State Event
-> Memory Engine
-> Topic
-> Reading
-> Citizen
```

La relacion correcta es:

- Source Factory define como una fuente puede entrar.
- Source Watcher observa cambios.
- State Events convierte cambios en hechos oficiales observados.
- Memory Engine conecta esos hechos con la memoria existente.
- Topic Update refleja cambios en temas afectados.
- Daily Brief y Pulso muestran novedades recientes verificables.
- Reading Pipeline produce lecturas cuando corresponde.
- Knowledge Engine estructura conocimiento desde documentos.
- Publication Engine prepara salidas publicables.

Memory Engine no sustituye ninguno de esos componentes. Los conecta conceptualmente alrededor de eventos.

## Relacion con Source Factory

Source Factory responde como entra una fuente oficial.

Memory Engine responde que ocurre despues de que esa fuente produce eventos.

Cada ficha Source Factory deberia ayudar a Memory Engine a saber:

- que tipos de eventos puede generar la fuente;
- que entidades suelen aparecer;
- que documentos fuente existen;
- que identificadores permiten deduplicar;
- que dominios puede alimentar;
- que temas existentes puede actualizar;
- que limitaciones deben conservarse;
- que eventos no deben publicarse sin revision.

Una fuente no debe crear memoria por excepcion. Debe entrar al sistema generando eventos verificables que Memory Engine pueda relacionar.

## Relacion con State Events

State Events son la unidad minima y la entrada principal.

Memory Engine no cambia el evento. Lo integra.

Un evento debe mantenerse estable:

```text
Evento = que ocurrio
Fuente = donde se observo
Documento = que lo respalda
Evidencia = como se verifica
Relaciones = con que memoria existente se conecta
```

Si despues aparece nueva informacion, no se edita el evento original para fingir que siempre se supo. Se agrega un nuevo evento, una nueva relacion o una nueva limitacion.

## Relacion con Topic Update

Topic Update sigue siendo util, pero deja de ser el centro.

El orden conceptual debe ser:

```text
State Event
-> Memory Engine
-> Tema afectado
-> Topic Update
```

Un tema no se actualiza porque el sistema quiere mostrar novedades. Se actualiza porque un evento oficial afecta su historia documentada.

Un evento puede:

- actualizar un tema existente;
- sugerir un tema nuevo;
- alimentar varios temas con justificacion;
- quedar solo en memoria si no hay contexto suficiente;
- quedar fuera de Pulso si no hay evidencia publicable.

## Relacion con Daily Brief y Pulso del Estado

Daily Brief y Pulso del Estado no deben ser listas planas de fuentes.

Deben construirse desde memoria enriquecida:

```text
Evento reciente
-> Dominio
-> Tema afectado
-> Documento o registro
-> Evidencia
-> Ruta a lectura o cronologia
```

Pulso responde: que se movio en el Estado y como se verifica.

Daily Brief responde: que cambios recientes merecen atencion y donde se entiende su contexto.

Ni Pulso ni Daily Brief deben convertir un evento en conclusion.

## Relacion con Lecturas Documentadas

Una Lectura Documentada es una vista sobre la memoria.

No es la memoria.

La lectura toma eventos, documentos, evidencia, cronologia y entidades para explicar un asunto publico en lenguaje ciudadano. Cuando Memory Engine agrega eventos relevantes, una lectura puede:

- mantenerse vigente;
- mostrar aviso de nuevo evento;
- requerir actualizacion;
- requerir nueva evidencia;
- requerir nueva seccion de cronologia;
- quedar limitada si la fuente cambio o se contradice.

No toda novedad debe regenerar una lectura. Una lectura cambia cuando el evento afecta la comprension documentada del tema.

## Relacion con Knowledge Engine

Knowledge Engine transforma documentos o registros en conocimiento estructurado reutilizable: resumen ciudadano, puntos importantes, preguntas, claims verificables y evidencia asociada.

Memory Engine hace otra cosa.

Memory Engine no procesa texto para explicar. Conecta eventos oficiales con memoria historica.

La diferencia central:

```text
Knowledge Engine: documento -> conocimiento estructurado
Memory Engine: evento -> memoria relacionada
```

Knowledge Engine puede ayudar a una lectura. Memory Engine mantiene la continuidad de lo que el Estado ha hecho en el tiempo.

## Principios permanentes

### Principios de evento

- La memoria crece desde eventos oficiales observados.
- Un evento no se elimina.
- Un evento no se reescribe para cambiar su sentido historico.
- Un evento puede recibir nuevas relaciones.
- Un evento puede recibir nuevas limitaciones.
- Un evento puede quedar fuera de publicacion sin salir de la memoria.
- Un evento debe conservar fuente, fecha, identificador y trazabilidad.

### Principios de memoria

- La memoria nunca elimina eventos.
- La memoria solo agrega.
- La memoria no reescribe la historia.
- La memoria puede corregirse agregando correcciones visibles.
- Las relaciones pueden crecer con el tiempo.
- Las entidades pueden acumular historia.
- Los temas pueden dormir, pero no mueren.
- Las fuentes pueden cambiar, pero el historial observado debe preservarse cuando sea posible.

### Principios de evidencia

- Todo debe poder verificarse.
- El documento fuente tiene prioridad.
- La evidencia debe estar cerca de la explicacion.
- La evidencia no reemplaza al documento.
- Si no hay evidencia suficiente, no hay publicacion completa.
- Si dos fuentes oficiales se contradicen, la contradiccion se conserva como condicion documental.

### Principios de neutralidad

- Memory Engine observa, no opina.
- No clasifica politicamente.
- No infiere causalidad.
- No asigna intencion.
- No convierte proximidad temporal en relacion causal.
- No produce lenguaje acusatorio.

### Principios de crecimiento

- Un nuevo evento debe poder conectarse sin reorganizar toda la memoria.
- Una nueva fuente debe alimentar eventos, no crear una taxonomia paralela.
- Un nuevo tema debe nacer desde continuidad documental, no desde una fuente aislada.
- Una lectura debe ser regenerable desde memoria, no depender de una pagina manual.
- El ciudadano nunca debe perder la ruta hacia el documento fuente.

## Modelo conceptual

```text
Estado
-> Fuente Oficial
-> Documento o Registro
-> State Event
-> Memory Engine
-> Entidades
-> Dominio
-> Tema
-> Cronologia
-> Evidencia
-> Lectura Documentada
-> Pulso del Estado
-> Ciudadano
```

### Estado

Conjunto de instituciones, decisiones, documentos, registros y cambios oficiales que DEO observa.

### Fuente Oficial

Origen institucional verificable desde donde se observa un evento.

### Documento o Registro

Soporte oficial especifico que respalda el evento cuando existe.

### State Event

Unidad minima de memoria. Dice que algo ocurrio, desde que fuente, cuando fue observado y con que evidencia.

### Memory Engine

Capa conceptual que relaciona eventos con entidades, fuentes, documentos, dominios, temas, cronologias, lecturas y Pulso.

### Entidad

Organismo, persona publica, proveedor, institucion, norma, expediente, programa, territorio u otro sujeto identificable que aparece en eventos oficiales.

### Dominio

Area permanente del Estado donde vive una parte de la memoria.

### Tema

Historia publica persistente que acumula eventos y documentos en el tiempo.

### Cronologia

Secuencia verificable de eventos relacionados.

### Evidencia

Referencia que permite verificar una afirmacion, relacion o evento.

### Lectura Documentada

Vista ciudadana construida desde memoria, documentos y evidencia.

### Pulso del Estado

Vista reciente de eventos oficiales relevantes, agrupados y verificables.

### Ciudadano

Persona que necesita entender que cambio, por que importa documentalmente y donde puede comprobarlo.

## Ejemplo 1: Congreso publica nueva votacion

```text
Congreso publica nueva votacion
-> Watcher legislativo detecta el registro
-> State Event: NEW_VOTE
-> Memory Engine relaciona la votacion con boletin, camara, fecha, parlamentarios, documento o registro oficial
-> Tema Presupuesto Publico se actualiza si la votacion pertenece al boletin presupuestario
-> Cronologia del tema agrega el hito
-> Lectura Presupuesto queda marcada como relacionada con evento nuevo
-> Pulso del Estado puede mostrar la novedad si hay evidencia suficiente
-> Ciudadano abre la lectura y puede verificar la votacion en la fuente
```

Memory Engine no dice si la votacion fue buena, mala, importante politicamente o esperada. Solo preserva el hecho oficial y sus relaciones.

## Ejemplo 2: ChileCompra publica una nueva orden de compra

```text
ChileCompra publica nueva orden de compra
-> Watcher observa cambio o nuevo registro
-> State Event: NEW_PUBLIC_PURCHASE
-> Memory Engine relaciona evento con organismo comprador, proveedor, monto, fecha, codigo de compra y URL oficial
-> Dominio Compras Publicas recibe el evento
-> Tema del organismo o programa se actualiza si existe continuidad documental
-> Cronologia agrega el hito de compra
-> Pulso del Estado puede mostrar la compra como cambio verificable
-> Lectura relacionada puede incorporar el evento si afecta la historia documentada
-> Ciudadano revisa documento, registro o ficha oficial
```

Memory Engine no concluye que la compra sea irregular, relevante por si misma o causalmente conectada con otro evento. Solo crea memoria verificable.

## Ejemplo 3: Contraloria publica un informe

```text
Contraloria publica nuevo informe
-> Watcher detecta documento oficial
-> State Event: NEW_REPORT
-> Memory Engine relaciona informe con organismo fiscalizado, periodo, materia, documento fuente y URL
-> Dominio Justicia y Control recibe el evento
-> Tema de control institucional se actualiza si el informe pertenece a una historia seguida
-> Cronologia agrega publicacion del informe
-> Lectura Documentada puede requerir nueva seccion de evidencia
-> Pulso del Estado muestra el informe solo con lenguaje descriptivo
-> Ciudadano puede abrir el documento fuente
```

Memory Engine no transforma observaciones de Contraloria en conclusiones propias de DEO. Conserva el documento, el evento y sus relaciones.

## Manejo de cambios posteriores

Si una fuente oficial actualiza, rectifica o reemplaza un documento, DEO debe registrar un nuevo evento.

```text
Documento actualizado
-> State Event: DOCUMENT_UPDATED
-> Memory Engine relaciona el nuevo evento con el documento anterior
-> Cronologia conserva ambas observaciones
-> Tema muestra que hubo cambio
-> Lectura marca limitacion o actualizacion si corresponde
```

La version nueva no borra la version anterior. La memoria conserva la historia de observacion.

## Manejo de contradicciones

Si dos fuentes oficiales entregan informacion distinta, Memory Engine debe relacionar ambas fuentes y marcar la contradiccion como condicion documental.

No debe decidir por opinion cual fuente "gana".

Debe conservar:

- fuente A;
- fuente B;
- fechas;
- documentos o registros;
- identificadores;
- descripcion neutral de la diferencia;
- tema o lectura afectada;
- estado de revision.

La contradiccion puede actualizar una lectura, pero no autoriza una conclusion no documentada.

## Decisiones futuras

Estos modulos pueden existir en fases futuras como extensiones del Memory Engine. No forman parte obligatoria de V1 y no deben implementarse solo por estar nombrados aqui.

### Relationship Builder

Extension futura para construir relaciones entre eventos, entidades, documentos y temas usando reglas verificables.

### Timeline Builder

Extension futura para producir cronologias desde eventos relacionados, preservando orden, fuente y evidencia.

### Entity Memory

Extension futura para mostrar la historia documentada de una entidad: organismo, proveedor, autoridad, norma, territorio o programa.

### Institution Memory

Extension futura especializada en organismos publicos, sus eventos, documentos, compras, informes, autoridades y cronologias.

### Citizen Feed

Extension futura para presentar eventos recientes de forma comprensible, agrupados por dominio, tema y relevancia documental.

### Alert Engine

Extension futura para avisar cambios relevantes. No debe publicar conclusiones ni notificaciones sin evidencia y reglas claras.

## Riesgos de diseno

### Riesgo: convertir Memory Engine en Knowledge Engine

Si Memory Engine empieza a resumir, redactar o interpretar, duplicara Knowledge Engine y debilitara la arquitectura.

Correccion: Memory Engine solo relaciona eventos.

### Riesgo: convertir eventos en publicaciones automaticas

Un evento observado no equivale a una lectura lista.

Correccion: Pulso puede mostrar eventos verificables, pero una Lectura Documentada requiere evidencia, contexto y reglas de publicacion.

### Riesgo: crear temas por cada evento

Si cada evento crea un tema, DEO perdera orden.

Correccion: un evento actualiza temas existentes cuando hay continuidad; solo sugiere tema nuevo cuando abre una historia publica persistente.

### Riesgo: borrar historia al actualizar fuentes

Si DEO reemplaza eventos antiguos por datos nuevos, deja de ser memoria.

Correccion: las actualizaciones oficiales son nuevos eventos, no ediciones silenciosas.

## Regla final

Memory Engine existe para que DatosEnOrden pueda crecer sin perder memoria.

Cada nuevo evento oficial debe poder responder:

```text
Que ocurrio?
Donde fue observado?
Que documento o registro lo respalda?
Que entidades toca?
Que dominio alimenta?
Que tema actualiza?
Que cronologia cambia?
Que lectura queda relacionada?
Como puede verificarlo un ciudadano?
```

Si esas preguntas no pueden responderse, el evento puede conservarse como observacion limitada, pero no debe convertirse en publicacion plena.

## Conclusion

Memory Engine es el nucleo conceptual de DatosEnOrden porque desplaza el centro desde paginas, temas o documentos aislados hacia el historial vivo de eventos oficiales.

Los temas organizan.

Las lecturas explican.

El Pulso muestra novedades.

Pero la memoria crece con eventos.

Esa separacion permite que DEO incorpore nuevas fuentes, miles de documentos y anos de cambios oficiales sin perder orden, trazabilidad ni neutralidad.

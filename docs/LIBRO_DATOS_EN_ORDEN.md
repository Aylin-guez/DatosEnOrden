# Libro de Datos en Orden

> Primer borrador. Documento vivo para ordenar como piensa, opera y evoluciona el ecosistema Datos en Orden.

Este libro no reemplaza la documentacion tecnica existente. Su funcion es reunir en una base comun la identidad, filosofia, arquitectura, metodologia, operacion y preguntas abiertas del proyecto.

## Prologo

Datos en Orden existe porque la informacion publica suele estar disponible, pero no necesariamente es comprensible.

El Estado publica leyes, presupuestos, compras, informes, actas, auditorias, contratos, declaraciones, votaciones y registros. El problema no es solo acceder a esos materiales. El problema es reconstruir que ocurrio, donde esta la evidencia, que cambio en el tiempo y que falta por revisar.

La documentacion del proyecto define a DatosEnOrden como una infraestructura para transformar informacion publica dispersa en conocimiento verificable, trazable y reutilizable. Su principio mas importante es reducir la distancia entre una persona y la evidencia oficial.

La relacion central es:

```text
Informacion oficial
-> evidencia verificable
-> memoria ordenada
-> comprension ciudadana
-> mejores decisiones
```

Datos en Orden no existe para decirle a una persona que pensar. Existe para que pueda comprobar por si misma.

## 1. Origen

Datos en Orden nace de una necesidad concreta: ordenar informacion publica y ciudadana que aparece dispersa entre portales, documentos, bases de datos y registros institucionales.

El manifiesto del proyecto lo resume asi: mientras mas informacion publica existe, mas dificil puede ser comprender que esta ocurriendo realmente. Las personas terminan dependiendo de interpretaciones de terceros porque los documentos oficiales suelen ser extensos, tecnicos y fragmentados.

La motivacion inicial combina:

- transparencia;
- evidencia;
- trazabilidad;
- comprension ciudadana;
- mejores decisiones;
- separacion entre hechos verificables, interpretacion y opinion.

El origen tecnico tambien es gradual. La documentacion muestra una evolucion desde una base PostgreSQL trazable, ETLs y claims verificables hacia una plataforma ciudadana con expedientes, seguimiento, reportes, documento fuente, lectura documentada, fuentes oficiales y memoria de eventos.

## 2. Filosofia

La filosofia de Datos en Orden no es vender tecnologia por tecnologia.

La tecnologia solo tiene sentido si ayuda a transformar informacion en comprension verificable.

Principios documentados:

- Evidencia primero.
- Sin fuente no existe.
- Neutralidad de los datos.
- Opiniones separadas de los datos.
- Codigo y metodologia publicos cuando no expongan informacion sensible.
- Arquitectura preparada para crecer.
- El documento fuente tiene prioridad.
- La explicacion nunca reemplaza al documento.
- DEO observa, no opina.
- La evidencia debe estar cerca de la explicacion.

Automatizar no significa reemplazar criterio humano. En la arquitectura actual, los motores ordenan, conectan, preparan, transforman y publican artefactos verificables, pero no deben inventar conclusiones ni convertir eventos en interpretaciones automaticas.

La automatizacion debe liberar tiempo para lo que aporta mas valor:

- revisar evidencia;
- mejorar claridad;
- detectar limitaciones;
- mantener trazabilidad;
- decidir que merece publicarse;
- mejorar el Core para futuros proyectos.

## 3. Mision y vision

### Mision actual

Construir una base de conocimiento publica, verificable y reutilizable sobre informacion publica de Chile.

En la formulacion mas reciente de identidad, DatosEnOrden es una memoria viva del Estado basada en documentos oficiales.

### Vision de largo plazo

Datos en Orden debe poder alimentar:

- portales ciudadanos;
- lecturas documentadas;
- expedientes;
- cronologias;
- reportes ciudadanos;
- investigaciones academicas;
- periodismo de datos;
- organizaciones civiles;
- APIs abiertas;
- aplicaciones de terceros;
- sistemas de analisis historico.

La vision no es reemplazar portales oficiales. Es organizar fuentes, documentos, eventos y evidencia para que las personas puedan seguir historias publicas sin perder el origen verificable.

### Que significa Datos en Orden Studio

DatosEnOrden Studio es la capa reutilizable de motores, flujos y componentes que permite producir experiencias de lectura, publicacion y trazabilidad documental.

El sitio publico es la experiencia ciudadana. Studio es la base de motores configurables.

La documentacion define Studio como el espacio donde se desarrollan motores de informacion configurables para transformar documentos, registros, eventos y evidencia en conocimiento, seguimiento y reportes.

Studio no debe convertirse en una coleccion de proyectos aislados. Cada proyecto nuevo debe fortalecer motores comunes o ampliar configuraciones reutilizables.

## 4. Principios

### Principios tecnicos

- La base de verdad no es el grafo publico; es la cadena de trazabilidad desde fuente, dataset, importacion, source record, claim, evidencia y relacion publica.
- Cada fuente debe transformarse a contratos internos antes de contaminar el Core.
- Los adapters son pequenos, reemplazables y testeables.
- Un adapter no decide significado publico, no publica y no cambia schema.
- Los motores deben conocer abstracciones estables, no vocabulario de cliente.
- Las configuraciones de dominio deben contener vocabulario, workflows, audiencias, templates y branding.
- No introducir infraestructura pesada antes de validar contratos.
- No duplicar motores por industria o cliente.
- Cada cambio relevante debe conservar fuente, fecha, identificador y evidencia.

### Principios eticos

- No scoring personal ni empresarial.
- No acusaciones.
- No inferencias ocultas.
- No presentar anomalias como delito.
- Separar fuente oficial, dato derivado, inferencia y opinion.
- Mantener atribucion clara de fuentes.
- Minimizar datos personales.
- No publicar datos personales innecesarios.
- No mezclar datos con propaganda.
- Si no hay evidencia suficiente, reducir o no publicar la afirmacion.

### Principios comerciales

Lo documentado hasta ahora indica:

- DatosEnOrden publico puede ser una aplicacion ciudadana demostrativa.
- DatosEnOrden Studio concentra capacidades reutilizables para clientes, organizaciones y productos derivados.
- Cada cliente debe dejar una mejora reusable: configuracion, adapter, plantilla, validacion o mejora de motor.
- Los motores reutilizables son propiedad estrategica de Studio y podrian separarse en repos privados futuros.
- El proyecto ciudadano puede ser publico sin exponer configuraciones comerciales, datos sensibles o logica estrategica de clientes.

Pendiente de definir:

- pricing;
- paquetes comerciales;
- estructura formal de licencias;
- terminos de soporte;
- estrategia de ventas;
- criterios para aceptar clientes;
- separacion legal y contractual entre producto publico y Studio.

### Principios de la fundadora

Pendiente de definir.

El repositorio documenta principios de producto, etica, arquitectura, repositorio y crecimiento, pero no contiene todavia una declaracion explicita de principios personales de la fundadora ni reglas sobre ritmo de vida, limites operativos o tipo de empresa deseada.

## 5. Ecosistema

Datos en Orden se entiende como un ecosistema de motores, contratos, fuentes y productos.

### Platform Core

Contiene reglas comunes, contratos internos, servicios compartidos, validadores, modelos abstractos y helpers que permiten que los motores funcionen en distintos dominios.

El Core debe preguntar:

- que entidades existen;
- que relaciones se permiten;
- que estados tiene este workflow;
- que audiencias existen;
- que templates puede producir el motor.

La configuracion responde esas preguntas.

### Knowledge Engine

Transforma documentos o registros en conocimiento estructurado:

- resumen ciudadano;
- puntos importantes;
- preguntas sugeridas;
- claims verificables;
- evidencia;
- digest reutilizable.

No debe conocer leyes, paises, industrias, clientes ni vocabulario especifico. Es un motor general que opera sobre documentos y contratos estructurados.

### Memory Engine

El Memory Engine define como crece la memoria del Estado cuando llegan nuevos eventos oficiales.

Su centro no son los temas, sino los State Events.

```text
State Event
-> Memory Engine
-> entidades
-> documentos
-> dominios
-> temas
-> cronologias
-> lecturas relacionadas
-> Pulso del Estado
```

No resume, no interpreta, no redacta y no publica automaticamente. Conecta eventos con memoria historica.

### TraceFlow / Tracking Engine

TraceFlow es la capacidad de seguir eventos, estados, documentos y cambios en el tiempo.

En la experiencia publica se presenta como cronologia o seguimiento. Internamente modela historias documentales: propuestas, hitos, estados, documentos, evidencia y entidades relacionadas.

Su valor es mostrar continuidad sin inferir causalidad.

### Reading Pipeline

Transforma documentos estructurados en una experiencia de lectura con paginas, fragmentos, anclas y referencias.

No debe extraer PDFs ni hacer OCR en V1. Recibe documentos ya estructurados y entrega contratos listos para UI o publicacion futura.

### Publication Engine

Prepara salidas publicables y decide que superficies deben actualizarse cuando cambia una fuente documental.

Debe operar sobre contratos y evidencia. No debe reemplazar revision ni convertir novedades en publicaciones sin trazabilidad.

### ThirdLifeEngine / Report Engine

La documentacion lo describe como motor conceptual o reutilizable para convertir conocimiento estructurado en reportes, HTML, PDF, publicaciones y materiales para audiencias.

En el repo actual existe una capa local de reportes ciudadanos HTML. PDF y publicaciones avanzadas estan documentadas como posibilidades futuras, no como promesas completas.

### Source Factory y Source Plugins

Source Factory es el estandar para integrar nuevas fuentes oficiales.

Una fuente nueva debe entrar mediante ficha, revision legal/documental, adapter, watcher cuando corresponda, State Event, documento fuente, evidencia, Pulso y lectura.

Source Plugins centralizan metadata de fuentes y permiten que Ecosistema, Descubre, Expediente, CLI docs y readiness checks lean una misma descripcion.

### Plataforma ciudadana

La plataforma publica usa los motores para presentar:

- Pulso del Estado;
- Lectura Documentada;
- Documento Fuente;
- Evidencia;
- Cronologia;
- Expediente;
- Mas lecturas;
- Informes ciudadanos;
- Fuentes oficiales;
- Proyecto.

La experiencia publica no debe hablar de pipelines, engines, imports, adapters, schema ni datasets. Debe responder preguntas humanas.

## 6. Metodologia Datos en Orden

La metodologia comercial completa no esta formalizada como proceso unico en el repositorio. Sin embargo, la documentacion permite derivar una base de trabajo.

### 1. Diagnostico

Identificar que informacion existe, donde vive, que fuentes la sostienen, que decisiones dependen de ella y que tan verificable es.

Pendiente de definir:

- formato del diagnostico comercial;
- duracion;
- entregables;
- precio;
- criterios para pasar a implementacion.

### 2. Jornada de inmersion

Pendiente de definir.

No hay en el repositorio una metodologia documentada para entrevistas, talleres o sesiones de inmersion con cliente.

### 3. Observacion de procesos

Base documentada:

- no partir por tecnologia;
- entender fuentes, documentos, registros, eventos, entidades y flujos;
- separar fuente oficial, dato derivado, inferencia y opinion;
- evitar hardcodear negocio en motores.

Pendiente de definir:

- guia de observacion;
- checklist de procesos;
- formato de notas;
- criterios para detectar fricciones.

### 4. Deteccion del problema real

El problema real no debe asumirse desde la fuente o desde la herramienta. Debe identificarse desde la trazabilidad:

- que se necesita entender;
- que evidencia existe;
- que se repite manualmente;
- que decisiones dependen de informacion dispersa;
- que riesgos aparecen por falta de historial o contexto;
- que parte puede automatizarse sin perder control.

### 5. Diseno de alternativas

Las alternativas deben distinguir:

- configuracion;
- adapter;
- mejora de motor;
- producto visible;
- reporte;
- cronologia;
- expediente;
- lectura documentada;
- exportacion.

La regla de Studio es no crear software aislado cuando una mejora reusable puede resolver el problema.

### 6. Recomendacion fundamentada

Una recomendacion debe explicar:

- problema observado;
- fuentes disponibles;
- evidencia;
- limites;
- alternativa recomendada;
- alternativa descartada;
- impacto sobre Core;
- esfuerzo esperado;
- riesgos.

### 7. Decision final del cliente

Pendiente de definir.

El repositorio no documenta todavia el flujo formal de decision, aprobacion, contrato, firma, pagos o responsabilidad del cliente.

## 7. Productos y servicios

Esta seccion distingue lo documentado de lo pendiente.

### Diagnostico Datos en Orden

Pendiente de definir como producto formal.

Base conceptual: diagnosticar fuentes, evidencia, procesos y necesidad real antes de implementar.

### Adaptacion de motores

Documentado como principio de Studio.

Cada proyecto puede aportar:

- configuracion de dominio;
- adapter de fuente;
- plantilla reusable;
- mejora del motor;
- validacion general.

No debe aportar:

- fork completo del motor;
- reglas de cliente incrustadas en Core;
- duplicacion de modelos existentes.

### Implementacion

Documentada tecnicamente como adaptacion de Platform Core, Source Plugins, adapters, loaders, servicios JSON-safe, UI Reflex, reportes y validaciones.

Pendiente de definir:

- alcance comercial por tipo de implementacion;
- tiempos;
- responsabilidades del cliente;
- criterios de aceptacion.

### Licencias

Pendiente de definir.

La documentacion habla de motores reutilizables como propiedad estrategica de Studio y de posible separacion a repos privados futuros, pero no define licencias comerciales.

### Soporte

Pendiente de definir.

Existen documentos de troubleshooting, desarrollo y deployment, pero no un servicio comercial de soporte.

### Mantenimiento

Pendiente de definir comercialmente.

Base tecnica documentada:

- backups;
- logs;
- monitoreo;
- prelaunch checks;
- verificacion de demo;
- readiness checks por fuente;
- validacion de plugins;
- mantener datos sensibles fuera del repo.

### Evolucion

Documentada como principio:

- cada proyecto debe mejorar Core o configuracion;
- no duplicar motores;
- no mezclar reglas de cliente con Core;
- separar repo publico y motores privados cuando corresponda.

## 8. Modelo de negocio

### Plataforma ciudadana gratuita

La documentacion describe DatosEnOrden publico como aplicacion ciudadana demostrativa y futura superficie publica estable.

Pendiente de definir:

- alcance gratuito;
- costos cubiertos;
- limites de uso;
- politica de datos reales;
- gobernanza editorial.

### Donaciones

Pendiente de definir.

`LAUNCH_CHECKLIST.md` indica que pagos, donaciones o suscripciones no estan listos todavia.

### Clientes empresa

Documentado conceptualmente.

Studio puede adaptar motores configurables para clientes, organizaciones y productos derivados. El repo recomienda no exponer configuraciones comerciales ni datos de clientes.

Pendiente de definir:

- segmentos prioritarios;
- oferta comercial;
- proceso de ventas;
- contratos;
- SLA;
- soporte.

### Licencias

Pendiente de definir.

### Soporte recurrente

Pendiente de definir.

### Servicios personalizados

Documentado como posibilidad mediante adaptacion de motores, configuraciones de dominio, adapters, plantillas y mejoras reutilizables.

Pendiente de definir:

- tipos de servicio;
- precios;
- limites;
- criterios de reutilizacion.

### Relacion entre proyectos y mejora del Core

Principio documentado:

Cada proyecto de cliente debe mejorar el Core o ampliar configuracion, no crear un software aislado.

Un proyecto nuevo puede aportar:

- nuevo Source Plugin;
- nueva configuracion de dominio;
- nueva plantilla reusable;
- mejora del motor aplicable a otros dominios;
- bugfix;
- validacion general.

## 9. Operacion

El flujo operativo comercial esta pendiente de formalizar. Se propone como base de trabajo:

### Primer contacto

Pendiente de definir:

- canal;
- formulario;
- criterios de entrada;
- informacion minima solicitada.

### Agenda

Pendiente de definir:

- formato de reunion;
- duracion;
- preparacion previa;
- participantes.

### Diagnostico

Base documentada:

- revisar fuentes;
- revisar evidencia;
- separar datos, inferencias y opinion;
- detectar si el problema requiere configuracion, adapter, motor, reporte o producto visible;
- no prometer integraciones no construidas.

### Propuesta

Pendiente de definir.

Debe evitar prometer login, pagos, APIs productivas, scraping, automatizacion completa con LLM o publicacion con datos reales sin revision legal y operacional.

### Contrato

Pendiente de definir.

No hay decisiones legales o tributarias documentadas.

### Desarrollo

Base documentada:

- trabajar local-first cuando corresponda;
- usar datos demo marcados como `LOCAL_TEST_DATA` y `NOT_OFFICIAL_DATA`;
- no llamar APIs externas salvo alcance explicito;
- mantener tests y validaciones;
- no cambiar schema sin migracion y decision;
- proteger configuraciones privadas.

### Entrega

Base documentada:

- validar demo;
- compilar Reflex;
- revisar rutas principales;
- mantener avisos de demo/no oficial cuando aplique;
- entregar reportes HTML o salidas verificables cuando esten dentro de alcance.

### Seguimiento

Pendiente de definir comercialmente.

Base tecnica:

- cronologias;
- readiness checks;
- logs;
- monitoreo;
- revisiones de fuentes;
- correcciones visibles si hay errores.

## 10. Aprendizaje

### Cada proyecto debe dejar un activo

Principio documentado:

Cada cliente o proyecto debe dejar una mejora reusable:

- adapter;
- configuracion;
- plantilla;
- validacion;
- mejora de motor;
- bugfix;
- documentacion;
- fixture o test seguro.

### Revision posterior al proyecto

Pendiente de definir.

Propuesta para formalizar:

- que se aprendio;
- que se puede reutilizar;
- que no debe entrar al Core;
- que debe quedar como configuracion;
- que debe mantenerse privado;
- que deuda tecnica queda.

### Como se mejora el Core

Algo entra al Core si:

- aplica a mas de un dominio;
- describe una abstraccion estable;
- mejora validacion o interoperabilidad;
- reduce duplicacion real;
- puede probarse sin datos de cliente;
- no necesita vocabulario de negocio especifico.

### Como se documentan aprendizajes

Base documentada:

- la documentacion conserva memoria;
- las decisiones tecnicas deben quedar en docs o ADRs;
- material sensible debe vivir fuera del repo publico;
- si un documento mezcla categorias, debe separarse.

Pendiente de definir:

- plantilla post-proyecto;
- ritual de revision;
- ubicacion para aprendizajes internos no publicos.

## 11. Cultura

### Crecimiento sostenible

Documentado parcialmente.

La arquitectura insiste en crecer por contratos y carpetas estables, no por excepciones. El principio comercial dice que cada cliente debe fortalecer el Core o configuracion, no crear sistemas cerrados.

Pendiente de definir:

- ritmo de crecimiento;
- limites de carga operativa;
- criterios para decir que no;
- politicas de descanso o foco.

### Empresa diseñada para proteger la vida de la fundadora

Pendiente de definir.

No hay documento en el repositorio que establezca este principio de forma explicita. Si este sera un valor central, debe documentarse en una futura version del libro o en un documento de cultura.

### No crecer a costa de perder la esencia

Base documentada:

- no mezclar datos con propaganda;
- no sacrificar verificabilidad por velocidad;
- no convertir tecnologia en fin;
- no duplicar motores por cliente;
- no ocultar evidencia;
- no exponer estrategia sensible por publicar demasiado pronto.

### Automatizar Datos en Orden primero

Documentado indirectamente.

El proyecto ya incorpora scripts de verificacion, readiness checks, loaders, exportadores, validaciones de demo, source factory y documentacion operativa.

Pendiente de definir:

- que procesos internos de Studio deben automatizarse primero;
- como medir ahorro de tiempo;
- que tareas deben seguir siendo humanas.

## 12. Roadmap

### Etapa actual

Segun `PROJECT_PHASES.md`, la fase actual es:

```text
Fase 2 - Primeras fuentes y documentos reales
```

Objetivo:

- publicar la primera Lectura Documentada real;
- usar un documento oficial pequeno, verificable y trazable;
- mantener separacion clara entre demo local y contenido publico real.

### Pendientes tecnicos

Documentados:

- fuentes reales verificadas;
- proceso productivo de refresh de fuentes;
- validacion legal y operacional por fuente;
- browser-level tests;
- paginas de registro especifico;
- despliegue estable;
- backups;
- monitoreo;
- acceso controlado;
- estrategia para datos reales;
- separacion futura de motores privados;
- API publica futura;
- versionado historico avanzado.

### Pendientes legales

Documentados como no resueltos:

- revision legal profesional;
- estrategia legal completa para publicar datos no demo;
- condiciones/licencias por fuente;
- mecanismo futuro de correccion, rectificacion o retiro.

### SpA

Pendiente de definir.

No se encontro decision documentada sobre crear SpA, tipo societario, fecha, responsabilidades ni estructura legal.

### SII

Pendiente de definir.

No se encontro decision tributaria documentada.

### Dominio

Documentado como pendiente/proxima fase:

- comprar o conectar dominio;
- activar HTTPS;
- probar rutas principales en desktop y mobile;
- preparar `datosenorden.cl` como superficie publica estable.

### Registro de Proveedores ChileCompra

Pendiente de definir.

El repositorio documenta ChileCompra como fuente de datos, no como proceso comercial de registro de Datos en Orden como proveedor.

### Ventas al Estado

Pendiente de definir.

No hay estrategia documentada para vender al Estado, participar en licitaciones, convenios marco, trato directo u otros mecanismos.

## Fuentes internas revisadas

Este borrador se basa en documentos existentes del repositorio, especialmente:

- `README.md`
- `MANIFESTO.md`
- `PLATFORM.md`
- `PROJECT_PHASES.md`
- `PROJECT_STATUS.md`
- `NEXT_STEPS.md`
- `docs/VISION.md`
- `docs/DEO_CONSTITUTION.md`
- `docs/TRUST_POLICY.md`
- `docs/LEGAL_ETHICS.md`
- `docs/ARCHITECTURE.md`
- `docs/TECHNICAL_ROADMAP.md`
- `docs/ROADMAP.md`
- `docs/PUBLIC_PRODUCT_IDENTITY.md`
- `docs/CITIZEN_JOURNEY.md`
- `docs/PLATFORM_CORE_VISION.md`
- `docs/STUDIO_ARCHITECTURE.md`
- `docs/PRIVATE_ENGINES_STRATEGY.md`
- `docs/REPOSITORY_STRATEGY.md`
- `docs/SOURCE_FACTORY.md`
- `docs/MEMORY_ENGINE.md`
- `docs/STATE_EVENTS_MODEL.md`
- `docs/STATE_DOMAIN_MODEL.md`
- `docs/PROJECT_GROWTH_PLAN.md`
- `docs/CONTENT_STRATEGY.md`
- `docs/NEXT_PUBLIC_PHASE.md`
- `docs/LAUNCH_CHECKLIST.md`
- `docs/INFORMATION_POLICY.md`
- `docs/DATA_SOURCE_STRATEGY.md`

## Preguntas abiertas

1. Cual es la definicion formal de Datos en Orden Studio como empresa: producto, consultora, laboratorio de motores o combinacion?
2. Que principios personales de la fundadora deben convertirse en reglas de cultura?
3. Que tipo de crecimiento se considera sano y que tipo de crecimiento debe rechazarse?
4. Cual sera el primer producto comercial vendible?
5. Como se empaquetara el Diagnostico Datos en Orden?
6. Que parte de Studio sera publica y que parte sera privada?
7. Cual sera la politica de licencias de los motores?
8. Habra plataforma ciudadana gratuita permanente? Con que limites?
9. Se aceptaran donaciones? En que etapa?
10. Que proceso legal y tributario se necesita antes de vender?
11. Se creara SpA? Cuando y con que alcance?
12. Que pasos exige SII para operar formalmente?
13. Tiene sentido registrarse como proveedor ChileCompra? En que momento?
14. Cual sera la estrategia de ventas al Estado?
15. Que fuentes reales se integraran primero y bajo que criterios de riesgo?
16. Cual sera el flujo formal de correccion, rectificacion o retiro?
17. Que procesos internos deben automatizarse antes de crecer comercialmente?
18. Como se medira si cada proyecto mejora realmente el Core?
19. Que documentacion debe permanecer publica y que debe moverse a privado?
20. Que version del libro debe compartirse fuera del equipo y que version debe quedar interna?

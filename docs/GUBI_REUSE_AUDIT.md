# Gubi / Sistema Vivo Reuse Audit + DEO UI Next

## Alcance

Este informe revisa el proyecto Gubi como referencia conceptual y visual para la siguiente etapa publica de DatosEnOrden. No propone copiar codigo, mover archivos ni integrar componentes todavia.

Rutas revisadas:

- `E:\Gubi`
- `I:\Gubi`
- `E:\Gubi\PROJECT_VISION.md`
- `E:\Gubi\Codex\SISTEMA_VIVO_CORE_V1.md`
- `E:\Gubi\docs\system_language\SYSTEM_LANGUAGE_README.md`
- `E:\Gubi\docs\system_language\SYSTEM_GOVERNANCE.md`
- `E:\Gubi\docs\JOURNEY_SIDEBAR_V2.md`
- `E:\Gubi\docs\FLOW_CLARITY_V1.md`
- `E:\Gubi\docs\UI_POLISH_V1.md`
- `E:\Gubi\ui\SCREEN_BEHAVIOR.md`
- `E:\Gubi\ui\MVP_NAVIGATION_RULES.md`
- `E:\Gubi\mvp\MVP_SCREENS.md`
- `E:\Gubi\sistema-vivo-mvp`
- `E:\Gubi\sistema-vivo-studio`
- `reflex_app/reflex_app.py`, especialmente `home`, `topic`, `topic_source_panel` y `topic_reading_flow`.

## Hallazgos principales

Sistema Vivo no debe entenderse como una fuente de componentes listos para copiar. Su valor principal para DatosEnOrden esta en sus reglas de producto: mantener una historia unica, preservar contexto, mostrar estado actual, explicar el siguiente paso y evitar que el usuario se pierda en rutas laterales.

El patron mas reutilizable es la interfaz de observabilidad: una situacion, evento o documento se entiende mejor cuando la pantalla mantiene visible:

- que se sabe;
- de donde viene;
- que cambio;
- que sigue;
- que falta;
- que historia lo sostiene.

Esto calza directamente con la evolucion de DatosEnOrden hacia un lector interactivo de documentos oficiales. DEO no necesita un nuevo motor para adoptar este enfoque. Necesita ordenar la experiencia publica alrededor del documento fuente, los State Events y la memoria verificable.

## 1. Que es Sistema Vivo conceptualmente

Sistema Vivo es un marco de observabilidad y coordinacion. Su unidad central no es una persona, un ticket, una tarea ni una base de datos, sino una situacion observable.

Conceptualmente, Sistema Vivo convierte trazas parciales en una historia comprensible sin convertirlas automaticamente en sentencia, perfil, decision o conclusion. Su ciclo base es:

```text
Realidad observada
    |
Datos, declaraciones o hechos observados
    |
Eventos trazables
    |
Senales explicables
    |
Revision humana y estado epistemologico
    |
Situacion observable
    |
Responsabilidad, accion, seguimiento y resultado
    |
Aprendizaje
```

Para DatosEnOrden, la parte relevante no es la coordinacion social ni la intervencion institucional. La parte relevante es la idea de que una realidad compleja se vuelve comprensible cuando se organiza como historia verificable, con contexto persistente y limites visibles.

## 2. Que partes NO deben mezclarse con DatosEnOrden

No deben mezclarse con DEO:

- Modulos de intervencion social, derivacion, transferencia o responsabilidad sobre personas.
- Lenguaje de necesidades, barreras, riesgo social, vulnerabilidad o seguimiento individual.
- Cualquier logica que parezca vigilancia, scoring, priorizacion automatica o decision institucional.
- Alertas operativas que impliquen recomendar accion publica.
- Conceptos de responsable principal sobre una situacion ciudadana, salvo como metadato oficial documentado.
- Formularios de captura manual propios de Sistema Vivo Studio.
- Esquemas YAML o modelos de datos de Gubi.
- UI Streamlit como implementacion tecnica.
- Vistas de productividad, cumplimiento, tareas o gestion de casos.

DatosEnOrden observa documentos oficiales. No coordina intervenciones. No decide. No clasifica politicamente. No perfila personas. No reemplaza a instituciones.

## 3. Que partes SI pueden convertirse en motor reutilizable

Las partes reutilizables son patrones conceptuales, no codigo inmediato:

- Observabilidad basada en eventos.
- Historia acumulativa y no destructiva.
- Separacion entre observacion, interpretacion, decision y accion.
- Estado epistemologico visible: observado, documentado, limitado, pendiente, corregido.
- Contexto persistente: nunca perder que se esta leyendo y cual es la fuente.
- Mapa lateral no invasivo para orientar sin fragmentar la experiencia.
- Siguiente paso como orientacion, no como recomendacion politica.
- Correccion localizada junto al contenido original.
- Incertidumbre visible sin bloquear la comprension.
- Distinciones textuales breves: registrar no es interpretar, observar no prueba causalidad, explicar no reemplaza al documento.

En DEO, esto puede expresarse como una capa reusable de presentacion y memoria llamada provisionalmente `Sistema Vivo Engine`, pero no deberia implementarse todavia como motor tecnico independiente.

## 4. Componentes visuales de Gubi reutilizables

Conviene reutilizar como patrones:

- **Mapa lateral de recorrido:** una guia persistente que muestra donde esta el usuario dentro de una historia. En DEO podria mostrar Documento, Resumen, Cambios, Cronologia, Evidencia y Expediente.
- **Estado actual compacto:** una franja o bloque que indique fuente, documento activo, evento vigente, fecha y limite conocido.
- **Historia acumulativa:** una cronologia que no separa documentos, eventos y cambios en paginas distintas.
- **Panel de "lo que sabemos":** resumen breve de hechos documentados y limitaciones.
- **Siguiente paso no invasivo:** en DEO no debe decir que hacer politicamente; puede orientar a "revisar evidencia", "ver cronologia" o "abrir fuente oficial".
- **Estados nombrados:** evitar depender solo de colores. Usar etiquetas como "documentado", "limitado", "actualizado", "corregido", "pendiente de fuente".
- **Recordatorios conceptuales breves:** por ejemplo, "La explicacion no reemplaza al documento" o "Una fuente nueva actualiza la historia".

No conviene copiar componentes tecnicos de Streamlit. DEO ya esta en Reflex y debe mantener su propia arquitectura.

## 5. Patrones de navegacion que conviene traer a DEO

Gubi tiene una regla fuerte: preservar una sola historia. Esa regla es especialmente util para `/topic`.

Patrones recomendados:

- Reducir rutas laterales durante la lectura principal.
- Mantener una sola pantalla funcional para Documento + Lectura.
- Usar vistas avanzadas solo como salida secundaria.
- No abrir otra pagina para ver evidencia.
- No usar tabs cuando el contenido debe leerse como secuencia.
- Mantener contexto visible durante todo el recorrido.
- Mostrar historial por tiempo, no por modulo.
- Permitir revisar pasos anteriores sin perder el punto actual.
- Hacer que cada click de evidencia acerque al documento, no que aleje al usuario de el.

## 6. Propuesta de Sistema Vivo Engine reutilizable

El nombre `Sistema Vivo Engine` podria reservarse para una capa futura de observabilidad reusable entre productos. No seria una IA, ni un pipeline, ni una base de datos nueva.

Su contrato conceptual seria:

```text
Eventos verificables
    |
Relaciones con documentos, entidades y tiempo
    |
Estado actual de una historia
    |
Recorrido visible
    |
Limitaciones e incertidumbres
    |
Vista publica orientada
```

En DEO, ese engine no deberia consumir datos crudos ni crear eventos. Deberia operar sobre la memoria ya formada por State Events y documentos oficiales.

Entradas posibles:

- State Events existentes.
- Documentos fuente.
- Evidencias.
- Entidades.
- Topics.
- Cronologias.
- Limitaciones editoriales.

Salidas posibles:

- Estado actual de un tema.
- Recorrido historico.
- Bloques de orientacion publica.
- Indicadores de que cambio y que falta.
- Navegacion contextual para Lectura Documentada.

Este engine seria reutilizable porque no conoceria ChileCompra, Congreso, DIPRES o Contraloria como casos especiales. Solo sabria presentar historias vivas construidas sobre eventos verificables.

## 7. Relacion con la arquitectura actual de DEO

```text
Fuente Oficial
    |
Source Watcher
    |
State Event
    |
Memory Engine
    |
Sistema Vivo Engine
    |
Topic Update
    |
Daily Brief / Pulso del Estado
    |
Lectura Documentada
    |
Ciudadano
```

La relacion recomendada es:

- **Source Watcher:** sigue observando fuentes oficiales. No cambia.
- **State Events:** siguen siendo la unidad minima. El engine no crea eventos por fuera del modelo existente.
- **Memory Engine:** mantiene la historia verificable. Sistema Vivo Engine solo organiza como se muestra esa memoria.
- **Topic Update:** recibe eventos y mantiene temas vivos. Sistema Vivo Engine puede aportar estructura de recorrido y estado actual.
- **Daily Brief / Pulso del Estado:** puede usar el enfoque de "que cambio, que sigue, que falta" para volverse menos dashboard y mas pulso vivo.
- **Lectura Documentada:** se convierte en la vista principal donde el documento, la explicacion y la evidencia permanecen conectados.

## 8. Cambios concretos para la UI actual de `/topic`

La direccion correcta es convertir `/topic` en una sola experiencia de lectura verificable:

```text
Documento completo visible
    |
Evidencia accionable
    |
Lectura ciudadana continua
```

Cambios propuestos:

- El panel izquierdo debe mostrar el documento completo una sola vez.
- El fragmento activo no debe duplicar el documento; debe funcionar como ubicacion o resaltado dentro del documento.
- El scroll del documento debe ser interno y estable, con altura cercana a `80vh`.
- La proporcion visual debe acercarse a 48% documento y 52% lectura.
- Cada evidencia debe apuntar a un fragmento con identificador estable.
- Al hacer click en evidencia, la app debe actualizar el fragmento activo, hacer scroll interno y resaltar temporalmente.
- El boton principal externo debe ser solo "Documento original" y debe apuntar a la fuente oficial.
- Eliminar duplicados como "Abrir documento", "Ver documento", "Abrir lectura" o "Ver lectura" cuando llevan al mismo flujo.
- Reducir enlaces a `/official-document` y otras vistas avanzadas dentro de la lectura principal.
- Reemplazar pestañas por lectura continua con secciones en orden: Resumen, Que propone, Que cambia, Que NO cambia, Cronologia, Evidencia, Expediente.
- Usar acordeones solo para metadatos tecnicos, evidencia adicional o expediente extendido.
- Mantener una mini navegacion interna de secciones, pero no como navbar dominante.
- Mantener el documento visible mientras la columna derecha avanza.

La pregunta de diseno debe ser: si el usuario hace click, queda mas cerca del documento oficial o mas lejos. Si queda mas lejos, esa accion debe salir del flujo principal.

## 9. Cambios para Home como Pulso del Estado

Home debe sentirse menos como portada de sitio y mas como tablero de observacion publica. No un dashboard de metricas, sino un pulso documentado.

Propuesta:

- Abrir con "Pulso del Estado" como estado actual, no como seccion secundaria.
- Mostrar eventos recientes agrupados por dominio o tema.
- Para cada evento, mostrar fuente oficial, documento, fecha y que lectura afecta.
- Incluir bloques de "Que cambio hoy", "Temas que se actualizaron", "Documentos nuevos" y "Lecturas afectadas".
- Evitar cards promocionales o explicativas largas.
- Mantener enlaces principales hacia `/topic` como lectura central.
- Usar estados nombrados: nuevo, actualizado, corregido, pendiente, limitado.
- Mostrar limitaciones cuando una fuente oficial no entrega suficiente informacion.

La Home deberia contestar rapidamente: que observo DEO, que documento lo sostiene y donde puedo leerlo con evidencia.

## 10. Navbar: mantener, compactar o preparar sidebar

Recomendacion: mantener por ahora, compactar visualmente y preparar migracion a sidebar.

No conviene eliminar el navbar en esta fase porque todavia existen rutas avanzadas utiles. Pero si conviene reducir su protagonismo dentro de `/topic`.

Evolucion propuesta:

1. Navbar compacto para rutas principales.
2. En `/topic`, una navegacion contextual lateral o rail interno.
3. En fase siguiente, sidebar persistente con secciones de producto:
   - Pulso
   - Lectura
   - Documento
   - Evidencia
   - Cronologia
   - Expediente
4. Las vistas avanzadas quedan accesibles, pero no compiten con la lectura.

El sidebar no debe ser un menu de modulos. Debe ser un mapa de contexto.

## 11. Que NO implementar todavia

No implementar todavia:

- Un motor tecnico nuevo llamado Sistema Vivo Engine.
- Nuevos schemas.
- Nuevas tablas.
- PostgreSQL adicional.
- Adapters nuevos.
- Pipelines nuevos.
- IA para clasificar o resumir.
- Copia de codigo Streamlit desde Gubi.
- Alertas, scores, rankings o predicciones.
- Reorganizacion completa de rutas.
- Eliminacion de rutas avanzadas existentes.
- Sidebar definitivo sin validar primero la lectura documento-primero.
- Cambios en GraphLoader, Knowledge Engine, Reading Pipeline o Publication Engine.

Primero debe consolidarse la experiencia publica sobre la arquitectura existente.

## Plan de implementacion por fases

### Fase 1: Ajuste de `/topic` sin arquitectura nueva

- Documento completo visible una sola vez.
- Scroll interno del documento.
- Evidencia con click hacia fragmento.
- Resaltado temporal de fragmento activo.
- Lectura continua sin tabs.
- Reduccion de botones duplicados.

### Fase 2: Home como Pulso del Estado

- Reordenar Home alrededor de eventos oficiales recientes.
- Conectar cada evento con fuente, documento, tema y lectura.
- Mostrar limitaciones y correcciones de forma visible.

### Fase 3: Navegacion contextual

- Compactar navbar.
- Agregar rail o sidebar contextual en `/topic`.
- Mantener vistas avanzadas como secundarias.

### Fase 4: Especificacion del Sistema Vivo Engine

- Documentar contrato conceptual.
- Definir entradas y salidas sobre eventos existentes.
- Validar que no duplique Memory Engine ni Topic Update.

### Fase 5: Reutilizacion multi-producto

- Solo despues de validar DEO, evaluar si el patron sirve tambien para otros productos del ecosistema.
- Mantener separadas las semanticas civicas de DEO y las semanticas sociales de Gubi.

## Riesgos

- **Mezcla semantica:** importar conceptos sociales de Gubi podria hacer que DEO parezca evaluar personas o instituciones. Mitigacion: usar solo lenguaje documental y verificable.
- **Nuevo motor prematuro:** crear Sistema Vivo Engine ahora podria duplicar Memory Engine. Mitigacion: primero usarlo como patron de UI y contrato conceptual.
- **Sidebar como menu de modulos:** si se transforma en navegacion lateral tradicional, se pierde la historia unica. Mitigacion: que sea mapa de contexto, no menu.
- **Documento duplicado:** mostrar fragmento activo y documento completo como bloques separados puede repetir informacion. Mitigacion: un solo documento, muchos anclajes.
- **Evidencia decorativa:** si la evidencia no mueve el documento, vuelve a ser una cita aislada. Mitigacion: click, scroll y resaltado obligatorio.
- **Home como dashboard:** demasiadas metricas pueden alejar a DEO de su identidad documental. Mitigacion: cada indicador debe tener fuente y documento cercano.
- **Rutas avanzadas compitiendo:** si cada tarjeta invita a salir de `/topic`, la lectura se fragmenta. Mitigacion: un solo flujo principal.

## Conclusion

Sistema Vivo aporta a DatosEnOrden una disciplina de producto: mantener una historia viva, mostrar contexto persistente, distinguir observacion de interpretacion y guiar sin fragmentar. Lo reutilizable no es la implementacion, sino el patron de observabilidad.

Para DEO, la traduccion correcta es:

```text
Documento oficial visible
    |
Evento verificable
    |
Memoria historica
    |
Lectura documentada
    |
Pulso del Estado
```

La proxima mejora no deberia ser un motor nuevo. Deberia ser una UI que haga cumplir la identidad del proyecto: una memoria viva del Estado basada en documentos oficiales.

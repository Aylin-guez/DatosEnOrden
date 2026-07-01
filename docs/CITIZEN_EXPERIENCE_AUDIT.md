# Citizen Experience Audit

Auditoria de experiencia para una persona que entra por primera vez a DatosEnOrden.

## Diagnostico General

La aplicacion ya tiene piezas fuertes: expediente, seguimiento, reportes, biblioteca/documentos, ecosistema y demo. El principal riesgo de UX era que algunas secciones sonaban internas o tecnicas, y que varias paginas terminaban sin sugerir un siguiente paso claro.

Objetivo de esta fase: que el MVP se sienta como una plataforma terminada, aunque los datos sigan siendo locales de prueba.

## Que Entiende Un Usuario Nuevo

- DatosEnOrden sirve para leer informacion publica con evidencia.
- Existe un caso demo principal.
- Hay reportes, seguimiento, expediente y fuentes.
- El producto usa datos locales de prueba y no representa datos oficiales reales.

## Que No Entendia Antes

- "Knowledge Engine" sonaba a motor interno, no a biblioteca ciudadana.
- "Exportar HTML" parecia una accion tecnica.
- "Suscribirse a cambios" estaba deshabilitado y generaba dudas.
- Algunas paginas terminaban en detalles tecnicos o listas sin proximo paso.
- El footer no mostraba todas las rutas ciudadanas importantes.

## Paginas Con Riesgo De Sentirse Vacias

- `/investigation` sin `id`: necesitaba explicar mejor como empezar.
- `/knowledge`: estaba orientada al motor, no al documento.
- `/reports`: parecia un conjunto de tarjetas, no una lectura tipo articulo.
- `/ecosystem`: podia parecer catalogo tecnico si no se conectaba con expediente/reporte.

## Propuestas Priorizadas

### Prioridad 1

- Convertir la entrada de documentos en "Biblioteca Oficial".
- Agregar una pagina `/project` para explicar MVP, datos demo, roadmap y feedback.
- Asegurar que Home tenga una promesa clara y tres accesos principales.
- Eliminar o rebajar acciones futuras no disponibles como suscripciones.
- Agregar siguientes pasos al final de cada modulo.

### Prioridad 2

- Hacer Reportes mas parecido a un articulo: resumen, que cambio, por que importa, fuentes y conexiones.
- Agregar ayudas contextuales visibles: expediente, fuente, evidencia, seguimiento, reporte ciudadano.
- Conectar expediente -> reporte -> biblioteca -> seguimiento -> fuentes.

### Prioridad 3

- Mejorar microcopy de botones tecnicos.
- Revisar futuras rutas con slugs publicos.
- Agregar pagina de contacto real cuando exista canal definido.

## Cambios Aplicados

- Home explica que puede hacer una persona y muestra novedades demo.
- Footer incluye DatosEnOrden, Studio, Reportes, Biblioteca, Seguimiento, Fuentes, Estado del proyecto y Contacto.
- Nueva ruta `/library` como Biblioteca Oficial visible.
- Nueva ruta `/project` como estado del MVP.
- Reportes se reorganiza como lectura ciudadana.
- Seguimiento reemplaza suscripcion deshabilitada por siguientes pasos.
- Expediente agrega bloque final de siguientes pasos.
- Ecosistema y Descubre conectan hacia otras rutas.

## Recomendaciones Siguientes

- Definir canal real de contacto antes del dominio publico.
- Agregar feedback simple por formulario cuando exista backend adecuado.
- Crear una primera pieza editorial real cuando existan fuentes verificadas.
- Revisar contraste y copy en mobile con capturas antes del lanzamiento.

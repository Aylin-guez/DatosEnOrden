# Workflow de integracion de fuentes

Este documento explica el proceso para integrar una fuente oficial desde cero en DatosEnOrden.

No contiene codigo. No autoriza crear motores nuevos ni modificar pipelines existentes.

## Principio operativo

Toda integracion empieza con una pregunta:

```text
Que informacion oficial puede verificar un ciudadano y como conserva DEO esa evidencia?
```

Si la respuesta no es clara, la fuente queda en investigacion.

## Paso 1: abrir ficha de fuente

Crear una ficha usando `docs/templates/SOURCE_INTEGRATION_TEMPLATE.md`.

Completar al menos:

- nombre;
- descripcion;
- organismo;
- URL oficial;
- tipo de acceso;
- documentacion oficial;
- licencia o condiciones de uso;
- eventos posibles;
- evidencia esperada;
- limitaciones conocidas.

## Paso 2: revisar permiso y alcance

Antes de escribir codigo, revisar si la fuente permite consulta y reutilizacion.

La decision debe dejar claro:

- que se puede consultar;
- que no se debe consultar;
- si hay limites de uso;
- si requiere credenciales;
- si el acceso debe ser manual, puntual o automatizado;
- si hay riesgos de publicar datos personales o sensibles.

Si el alcance no es claro, la fuente no avanza.

## Paso 3: identificar el formato real

Confirmar el formato observado:

- API;
- XML;
- JSON;
- CSV;
- XLS/XLSX;
- PDF;
- HTML oficial;
- descarga manual;
- otro.

Guardar ejemplos pequenos cuando sea posible. Los ejemplos deben servir para pruebas sin depender de red ni de descargas masivas.

## Paso 4: definir eventos

Listar que cambios oficiales puede producir la fuente.

Ejemplos:

- nuevo documento;
- documento actualizado;
- nuevo estado;
- nueva votacion;
- nuevo informe;
- nueva norma;
- rectificacion;
- publicacion de anexo;
- registro retirado o reemplazado.

Cada evento debe poder describirse sin opinion y con evidencia.

## Paso 5: definir documentos fuente y evidencia

Identificar que documento, registro o pagina oficial sostiene cada evento.

Para cada evidencia, definir:

- identificador;
- URL;
- fecha;
- organismo;
- campo o fragmento relevante;
- forma de verificacion ciudadana.

Si la evidencia no puede localizarse, no se publica afirmacion.

## Paso 6: disenar el adapter

El adapter debe seguir `docs/ADAPTER_GUIDELINES.md`.

Debe tener responsabilidad limitada:

- obtener o recibir datos de la fuente;
- parsear formato externo;
- normalizar identificadores;
- mapear a contratos internos existentes;
- conservar trazabilidad.

El adapter no debe publicar, interpretar, puntuar, clasificar politicamente, llamar motores ni cambiar schema.

## Paso 7: preparar pruebas

Antes de conectarlo a otros componentes, preparar pruebas con fixtures pequenos.

Las pruebas deben cubrir:

- parseo del formato oficial;
- normalizacion de identificadores;
- fechas y URLs;
- errores esperados;
- mapeo a contratos internos;
- preservacion de metadatos de fuente.

## Paso 8: conectar al Watcher si corresponde

Si la fuente tiene cambios observables, conectar el patron con Source Watcher.

El Watcher debe producir candidatos o cambios acotados. No debe publicar automaticamente ni ejecutar Reading Pipeline, Knowledge Engine, Publication Engine, GraphLoader o cargas masivas.

Si no corresponde watcher, documentar la razon: fuente manual, fuente historica, acceso puntual, baja frecuencia o falta de fecha confiable.

## Paso 9: mapear a State Event

Definir como los cambios se convierten en eventos.

Cada evento debe incluir:

- fuente;
- identificador externo;
- titulo descriptivo;
- URL o documento fuente;
- fecha de deteccion u observacion;
- tipo de cambio;
- razon;
- prioridad si aplica;
- evidencia disponible.

## Paso 10: asociar a temas

Definir reglas de asociacion a temas existentes o proponer un tema nuevo.

La clasificacion debe ser revisable y no inferencial. Un tema acumula eventos; no se recrea cada vez que una fuente publica una novedad.

## Paso 11: revisar Pulso del Estado

Un evento puede entrar al Pulso del Estado solo si tiene evidencia suficiente y su significado publico es claro.

Si el evento es tecnico, ambiguo o incompleto, puede quedar fuera del Pulso y permanecer como registro interno o pendiente.

## Paso 12: preparar Lectura Documentada si aplica

Una Lectura Documentada requiere revision adicional:

- documento fuente disponible;
- evidencia cercana;
- limitaciones visibles;
- lenguaje neutral;
- explicacion ciudadana que no reemplace el documento.

La integracion de fuente no obliga a crear lectura. Solo deja el camino preparado.

## Paso 13: validar

Antes de cerrar la integracion, ejecutar validaciones del proyecto y pruebas especificas de la fuente.

Validacion base:

```powershell
python scripts/content_readiness.py
python scripts/run_demo_check.py
python -m pytest -q --basetemp .pytest-tmp-source-name
python -m reflex compile --dry --no-rich
```

## Paso 14: documentar estado final

Actualizar la ficha de fuente con:

- estado;
- limites;
- pruebas disponibles;
- eventos soportados;
- documentos fuente soportados;
- evidencia validada;
- decisiones pendientes.

## Regla de cierre

Una fuente no esta integrada porque existe codigo. Esta integrada cuando existe un camino verificable desde la fuente oficial hasta el ciudadano.
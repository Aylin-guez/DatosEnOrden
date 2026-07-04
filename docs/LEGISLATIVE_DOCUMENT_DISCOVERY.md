# Legislative Document Discovery

Fase: Legislative Document Experience V1.

Este documento es solo investigacion. No implementa adapters, no conecta fuentes nuevas, no modifica Platform Core, Reading Pipeline, Knowledge Engine ni Publication Engine.

Punto de partida del expediente actual:

```text
cl-congreso-boletin-8575-05
```

## Pregunta principal

El expediente legislativo ya puede identificar un boletin y asociarlo con votaciones de Camara. La siguiente pieza documental es resolver si el boletin puede llegar automaticamente a un documento oficial legible por el flujo documental existente.

Respuesta corta:

```text
Si, es posible obtener automaticamente documentos oficiales asociados a un boletin.
La fuente primaria para proyecto/tramitacion/documentos asociados es Senado.
La fuente Camara sirve para votaciones y boletines de sesion, pero no entrega el texto oficial inicial del proyecto por boletin.
LeyChile/BCN sirven como fuentes posteriores o complementarias cuando el proyecto ya es norma publicada o cuando exista historia de la ley.
```

## Fuentes oficiales evaluadas

### Camara de Diputadas y Diputados

Fuente oficial:

```text
https://opendata.camara.cl/wscamaradiputados.asmx
```

Endpoints confirmados:

```text
GET https://opendata.camara.cl/wscamaradiputados.asmx/getVotaciones_Boletin?prmBoletin=<boletin>
GET https://opendata.camara.cl/wscamaradiputados.asmx/getVotacion_Detalle?prmVotacionID=<id>
GET https://opendata.camara.cl/wscamaradiputados.asmx/getSesionDetalle?prmSesionID=<id>
GET https://opendata.camara.cl/wscamaradiputados.asmx/getSesionBoletinXML?prmSesionID=<id>
```

Formato:

```text
XML via ASMX, SOAP, HTTP GET o HTTP POST.
```

Hallazgo:

- `getVotaciones_Boletin` permite partir desde el boletin y obtener votaciones asociadas.
- Las votaciones pueden incluir `Sesion.ID`.
- Con `Sesion.ID`, `getSesionBoletinXML` permite obtener un boletin de sesion en XML.
- Esto es un documento legislativo oficial, pero no necesariamente el texto inicial del proyecto.
- No se encontro en la API de Camara un endpoint directo que, dado `8575-05`, entregue el mensaje/mocion, informes, comparados u oficios del proyecto.

Uso recomendado:

```text
Camara = evidencia parlamentaria y documentos de sesion.
No usar Camara como fuente primaria del texto oficial del proyecto.
```

### Senado

Fuente oficial:

```text
https://tramitacion.senado.cl/wspublico/tramitacion.php?boletin=<correlativo>
```

Ejemplo verificado para el expediente actual:

```text
GET https://tramitacion.senado.cl/wspublico/tramitacion.php?boletin=8575
```

Respuesta:

```text
200 OK
XML
```

El endpoint devuelve un bloque `<proyectos>` con:

- `<boletin>8575-05</boletin>`
- `<titulo>Ley de Presupuestos del sector publico para el ano 2013.</titulo>`
- fecha de ingreso
- iniciativa
- camara de origen
- etapa
- numero de ley cuando aplica
- fecha de Diario Oficial cuando aplica
- estado
- tramitacion
- votaciones Senado
- urgencias
- informes
- comparados
- oficios
- materias
- links documentales `getDocto`

Documento inicial del proyecto:

```xml
<link_mensaje_mocion>
  http://www.senado.cl/appsenado/index.php?mo=tramitacion&ac=getDocto&iddocto=9000&tipodoc=mensaje_mocion
</link_mensaje_mocion>
```

Documentos asociados:

```text
LINK_INFORME   -> tipodoc=info
LINK_COMPARADO -> tipodoc=compa
LINK_OFICIO    -> tipodoc=ofic
```

Endpoint documental:

```text
https://www.senado.cl/appsenado/index.php?mo=tramitacion&ac=getDocto&iddocto=<iddocto>&tipodoc=<tipo>
```

Formato observado para `iddocto=9000&tipodoc=mensaje_mocion`:

```text
Content-Type: application/msword
Content-Disposition: attachment; filename=archivo.doc
```

Hallazgo importante:

```text
tramitacion.php?boletin=8575-05 devolvio "No existe el numero de boletin".
tramitacion.php?boletin=8575 devolvio el proyecto correcto y conserva <boletin>8575-05</boletin>.
```

Interpretacion:

- El identificador canonico interno debe seguir siendo `cl-congreso-boletin-8575-05`.
- Para Senado, la consulta puede requerir el correlativo corto antes del guion.
- La respuesta oficial debe validar que `<boletin>` coincida con el boletin completo esperado.
- No se debe reemplazar el canonico completo por la forma corta.

Uso recomendado:

```text
Senado = fuente primaria para resolver proyecto, tramitacion y documentos asociados por boletin.
```

### BCN Historia de la Ley

Fuente oficial:

```text
https://www.bcn.cl/historiadelaley/
```

Formato esperado:

```text
HTML y PDF, con identificadores propios de Historia de la Ley.
```

Hallazgo:

- Es una fuente oficial correcta para historia legislativa consolidada.
- No debe ser la primera ruta automatica V1 para boletines en tramitacion.
- No se confirmo en esta investigacion un endpoint simple por `boletin=8575-05`.
- La vista expandida exige un parametro interno `Id`.

Uso recomendado:

```text
BCN Historia de la Ley = enriquecimiento posterior cuando exista historia consolidada y se resuelva su identificador propio.
```

### LeyChile

Fuente oficial:

```text
https://www.bcn.cl/leychile/
```

Uso:

- Texto vigente o versiones de una norma ya publicada.
- XML/HTML normativo por identificador de norma.
- Relacion posterior cuando el proyecto llega a ley.

Limitacion:

```text
LeyChile no es la fuente primaria del texto de un proyecto en tramitacion.
Requiere que el proyecto ya tenga norma publicada o que pueda resolverse el identificador LeyChile.
```

Uso recomendado:

```text
LeyChile = texto normativo final/publicado, no documento inicial del proyecto.
```

## Como un boletin llegara a tener documento oficial

Flujo conceptual para cualquier proyecto:

```text
1. Entrada DEO
   cl-congreso-boletin-<boletin_completo>

2. Normalizacion
   display_boletin = <boletin_completo>
   senate_query_boletin = parte antes del guion cuando Senado lo requiera

3. Consulta oficial de proyecto
   tramitacion.senado.cl/wspublico/tramitacion.php?boletin=<senate_query_boletin>

4. Validacion
   XML debe contener <boletin> igual al boletin completo esperado.

5. Resolucion documental
   link_mensaje_mocion -> documento inicial del proyecto.
   informes -> documentos de comision.
   comparados -> textos comparados.
   oficios -> documentos de comunicacion legislativa.

6. Descarga acotada
   getDocto?iddocto=<id>&tipodoc=<tipo>

7. Registro documental
   Guardar metadata: organismo, URL, iddoc, tipodoc, boletin, fecha de recuperacion, content type, hash.

8. Paso a flujo documental existente
   Solo despues de seleccionar documento y convertirlo a una unidad compatible con Official Document Workflow.
```

## Identificadores recomendados

Entidad canonica:

```text
cl-congreso-boletin-<boletin_completo_normalizado>
```

Ejemplo:

```text
cl-congreso-boletin-8575-05
```

Identificador de consulta Senado:

```text
8575
```

Regla:

```text
Usar la forma corta solo como parametro tecnico de Senado.
Validar siempre contra el <boletin> completo devuelto.
```

Identificador documental Senado:

```text
senado-docto-<iddocto>-<tipodoc>
```

Ejemplos:

```text
senado-docto-9000-mensaje_mocion
senado-docto-15431-info
senado-docto-1107-compa
senado-docto-17543-ofic
```

## Formatos disponibles

| Organismo | Recurso | Formato |
| --- | --- | --- |
| Camara | Votaciones por boletin | XML |
| Camara | Detalle de votacion | XML |
| Camara | Boletin de sesion | XML |
| Senado | Proyecto/tramitacion/documentos asociados | XML |
| Senado | Documento `getDocto` | DOC observado; puede variar segun documento |
| BCN Historia de la Ley | Historia consolidada | HTML/PDF |
| LeyChile | Norma publicada | HTML/XML |

## Problemas detectados

- Senado puede requerir correlativo corto aunque el boletin oficial tenga sufijo.
- `getDocto` no entrega siempre texto plano; puede descargar binarios como DOC.
- El nombre de descarga observado es generico (`archivo.doc`), por lo que el nombre local debe derivarse de metadata propia.
- No todos los proyectos tendran los mismos tipos documentales.
- Proyectos refundidos o fusionados pueden traer mas de un boletin relacionado.
- El texto de un proyecto en tramitacion y el texto final publicado en LeyChile no son el mismo documento.
- BCN Historia de la Ley usa identificadores propios; no asumir que el boletin basta.
- Camara tiene documentos de sesion, pero no reemplaza el mensaje/mocion o documentos del expediente Senado.

## Recomendacion para la siguiente implementacion

Implementar una fase minima, acotada y sin modificar engines:

```text
Input manual: cl-congreso-boletin-<boletin_completo>
  -> resolver parametro Senado
  -> consultar tramitacion.php
  -> validar <boletin>
  -> extraer lista de documentos asociados
  -> NO descargar todos por defecto
  -> seleccionar un documento
  -> descargar getDocto
  -> registrar metadata y hash
  -> entregar archivo/metadata al Official Document Workflow existente
```

Prioridad documental:

```text
1. link_mensaje_mocion
2. informes principales
3. comparados
4. oficios relevantes
5. boletines de sesion Camara solo cuando la lectura necesite contexto de sesion
6. LeyChile/BCN solo cuando se busque norma final o historia consolidada
```

La implementacion no debe hacer crawling historico ni descargar todos los documentos asociados. Debe operar por boletin explicito y documento seleccionado.

## Respuestas solicitadas

### Es posible obtener automaticamente el documento?

Si. Para este boletin, Senado entrega enlaces oficiales `getDocto` desde el XML de tramitacion.

### Desde que organismo?

Principalmente Senado, mediante `tramitacion.senado.cl` y `www.senado.cl/appsenado`.

Camara queda como fuente complementaria para votaciones y boletines de sesion. LeyChile y BCN quedan como fuentes posteriores para norma publicada e historia consolidada.

### Que formato?

Proyecto/tramitacion en XML. Documento oficial observado en DOC (`application/msword`). Camara entrega XML. LeyChile/BCN pueden entregar HTML, XML o PDF segun recurso.

### Que identificador usar?

Internamente:

```text
cl-congreso-boletin-8575-05
```

Para consultar Senado en este caso:

```text
8575
```

Para documentos:

```text
iddocto + tipodoc
```

### Que problemas existen?

La forma completa del boletin no siempre sirve como parametro Senado; los documentos pueden ser binarios DOC; hay tipos documentales heterogeneos; BCN/LeyChile usan identificadores distintos; y no todos los proyectos tienen la misma cobertura documental.

### Que se recomienda?

Hacer primero un resolver documental Senado por boletin explicito que liste documentos y permita seleccionar uno. No implementar ingestion masiva ni conectar el Reading Pipeline directamente a la fuente.

## Fuentes consultadas

```text
https://opendata.camara.cl/wscamaradiputados.asmx
https://opendata.camara.cl/wscamaradiputados.asmx?op=getVotaciones_Boletin
https://opendata.camara.cl/wscamaradiputados.asmx?op=getSesionBoletinXML
https://tramitacion.senado.cl/wspublico/tramitacion.php?boletin=8575
https://tramitacion.senado.cl/wspublico/tramitacion.php?boletin=8575-05
https://www.senado.cl/appsenado/index.php?mo=tramitacion&ac=getDocto&iddocto=9000&tipodoc=mensaje_mocion
https://www.bcn.cl/historiadelaley/historia-de-la-ley/vista-expandida/
```

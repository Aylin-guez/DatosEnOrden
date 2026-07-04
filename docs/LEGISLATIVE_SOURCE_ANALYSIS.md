# Legislative Source Analysis

Fase: Legislative Adapter Discovery / Sprint 0.

Fuente unica investigada: Datos Abiertos Legislativos Congreso Nacional.

URL oficial: `https://opendata.camara.cl/`

Este documento no implementa adapter, loader, ETL, scraping ni consumo masivo. Su objetivo es describir como se deberia consumir la fuente cuando exista una fase tecnica autorizada.

## Hallazgo principal

Datos Abiertos Legislativos no se presenta como una API JSON/CSV moderna. El portal oficial funciona como indice de servicios web legislativos. La parte de Camara de Diputadas y Diputados expone un servicio ASP.NET ASMX:

- Base: `https://opendata.camara.cl/wscamaradiputados.asmx`
- WSDL: `https://opendata.camara.cl/wscamaradiputados.asmx?WSDL`
- Namespace documentado: `http://tempuri.org/`
- Protocolos documentados por operacion: SOAP 1.1, SOAP 1.2, HTTP GET y HTTP POST.
- Formato de respuesta: XML.

El portal tambien enlaza servicios del Senado en `https://tramitacion.senado.cl/wspublico/`. En esta auditoria, los enlaces de documentacion del Senado respondieron `403 Forbidden` desde el navegador de investigacion, por lo que quedan como endpoints oficiales enlazados pero pendientes de prueba desde otro cliente/red.

## Datasets encontrados

El portal agrupa los datasets en cuatro dominios.

### 1. Tramite Legislativo

Fuente producida por Senado y Camara.

Datasets/enlaces:

- Proyectos de Ley.
- Listado de proyectos que han tenido movimiento a partir de una fecha.
- Votaciones por Boletin - Senado.
- Votaciones por Boletin - Camara de Diputados.
- Votacion Detalle - Camara de Diputadas y Diputados.
- Periodo Legislativo Actual.
- Periodos Legislativos.
- Legislaturas.
- Legislatura Actual.

### 2. Informacion Parlamentarios

Datasets/enlaces:

- Senadores Vigentes.
- Diputadas y Diputados Vigentes.
- Diputadas y Diputados por Periodo Legislativo.

### 3. Senado

Datasets/enlaces:

- Sesiones de Sala.
- Diario de Sesion.
- Comisiones Vigentes.

Estos enlaces apuntan a `tramitacion.senado.cl/wspublico/` y requieren verificacion adicional porque devolvieron `403 Forbidden` durante esta investigacion.

### 4. Camara de Diputadas y Diputados

Datasets/enlaces:

- Sesiones de Sala.
- Sesion de Sala - Detalle.
- Boletin de Sesion.
- Comisiones Vigentes.

### 5. Biblioteca del Congreso Nacional

El portal tambien apunta al web service de LeyChile para:

- Leyes mas solicitadas.
- Metadatos de una norma y texto del encabezado.
- XML completo de la version actualizada de una norma.

Estos recursos son relevantes para una integracion legislativa posterior, pero no son el foco de esta auditoria porque el alcance solicitado es `opendata.camara.cl`.

## Formatos encontrados

| Formato | Estado | Evidencia |
| --- | --- | --- |
| XML | Confirmado | Servicio ASMX Camara, SOAP y HTTP GET/POST devuelven `text/xml`. |
| SOAP XML | Confirmado | Operaciones documentan SOAP 1.1 y SOAP 1.2. |
| HTTP GET XML | Confirmado | Operaciones documentan rutas `wscamaradiputados.asmx/<operacion>?param=...`. |
| HTTP POST form | Confirmado | Operaciones documentan `application/x-www-form-urlencoded`. |
| JSON | No encontrado | No aparece como formato documentado en el portal ni en ASMX Camara. |
| CSV | No encontrado | No aparece como formato documentado para Datos Abiertos Legislativos. |
| Descarga masiva | No encontrada | El portal expone servicios por endpoint/parametro, no paquetes descargables. |
| API REST | Parcial/no estricta | Existen endpoints HTTP GET, pero son metodos ASMX XML, no REST JSON. |

## Operaciones Camara encontradas

Servicio base: `https://opendata.camara.cl/wscamaradiputados.asmx`

| Operacion | Parametros | Respuesta | Uso |
| --- | --- | --- | --- |
| `getComisiones_Vigentes` | ninguno | XML | Lista de comisiones vigentes de la Camara. |
| `getDiputados` | no auditado en detalle | XML | Diputados, probablemente consulta general. |
| `getDiputados_Periodo` | `prmPeriodoID` | XML | Diputados de un periodo legislativo. |
| `getDiputados_Vigentes` | ninguno | XML | Diputadas y diputados vigentes. |
| `getLegislaturaActual` | ninguno | XML | Legislatura actual. |
| `getLegislaturas` | ninguno | XML | Lista de legislaturas. |
| `getPeriodoLegislativoActual` | ninguno | XML | Periodo legislativo actual. |
| `getPeriodosLegislativos` | ninguno | XML | Lista de periodos legislativos. |
| `getSesionBoletinXML` | `prmSesionID` | XML | Boletin de una sesion. |
| `getSesionDetalle` | `prmSesionID` | XML | Detalle de una sesion. |
| `getSesiones` | `prmLegislaturaID` | XML | Sesiones de sala por legislatura. |
| `getVotacion_Detalle` | `prmVotacionID` | XML | Votacion con detalle de votos y pareos. |
| `getVotaciones_Boletin` | `prmBoletin` | XML | Votaciones asociadas a un boletin. |

## Endpoints HTTP GET documentados

Los endpoints HTTP GET son equivalentes practicos para un futuro adapter simple, aunque pertenecen al servicio ASMX.

```text
GET https://opendata.camara.cl/wscamaradiputados.asmx/getVotaciones_Boletin?prmBoletin=<boletin>
GET https://opendata.camara.cl/wscamaradiputados.asmx/getVotacion_Detalle?prmVotacionID=<id>
GET https://opendata.camara.cl/wscamaradiputados.asmx/getSesiones?prmLegislaturaID=<id>
GET https://opendata.camara.cl/wscamaradiputados.asmx/getSesionDetalle?prmSesionID=<id>
GET https://opendata.camara.cl/wscamaradiputados.asmx/getSesionBoletinXML?prmSesionID=<id>
GET https://opendata.camara.cl/wscamaradiputados.asmx/getDiputados_Vigentes
GET https://opendata.camara.cl/wscamaradiputados.asmx/getDiputados_Periodo?prmPeriodoID=<id>
GET https://opendata.camara.cl/wscamaradiputados.asmx/getPeriodoLegislativoActual
GET https://opendata.camara.cl/wscamaradiputados.asmx/getPeriodosLegislativos
GET https://opendata.camara.cl/wscamaradiputados.asmx/getLegislaturaActual
GET https://opendata.camara.cl/wscamaradiputados.asmx/getLegislaturas
GET https://opendata.camara.cl/wscamaradiputados.asmx/getComisiones_Vigentes
```

## Endpoints Senado enlazados

El portal oficial enlaza estos recursos del Senado:

```text
https://tramitacion.senado.cl/wspublico/invoca_proyecto.html
https://tramitacion.senado.cl/wspublico/invoca_tramitacion_fecha.html
https://tramitacion.senado.cl/wspublico/invoca_votacion.html
https://tramitacion.senado.cl/wspublico/senadores_vigentes.php
https://tramitacion.senado.cl/wspublico/invoca_sesion.html
https://tramitacion.senado.cl/wspublico/invoca_diario.html
https://tramitacion.senado.cl/wspublico/comisiones.php
```

Estado: oficiales por estar enlazados desde `opendata.camara.cl`, pero no auditados completamente porque respondieron `403 Forbidden` en esta investigacion.

## Estructuras XML encontradas

### Votaciones por boletin

Operacion: `getVotaciones_Boletin`

Parametro:

- `prmBoletin`: string. El portal indica que para `8575-05` tambien puede usarse `8575`.

Estructura de respuesta:

```xml
<Votaciones>
  <Votacion>
    <ID>int</ID>
    <Fecha>dateTime</Fecha>
    <Tipo />
    <Resultado />
    <Quorum />
    <Sesion>
      <ID>int</ID>
      <Numero>int</Numero>
      <Fecha>dateTime</Fecha>
    </Sesion>
    <Boletin>string</Boletin>
    <Articulo>string</Articulo>
    <Tramite />
    <Informe />
    <TotalAfirmativos>int</TotalAfirmativos>
    <TotalNegativos>int</TotalNegativos>
    <TotalAbstenciones>int</TotalAbstenciones>
    <TotalDispensados>int</TotalDispensados>
  </Votacion>
</Votaciones>
```

### Detalle de votacion

Operacion: `getVotacion_Detalle`

Parametro:

- `prmVotacionID`: int.

Estructura relevante:

```xml
<Votacion>
  <ID>int</ID>
  <Fecha>dateTime</Fecha>
  <Resultado />
  <Sesion>
    <ID>int</ID>
    <Numero>int</Numero>
  </Sesion>
  <Boletin>string</Boletin>
  <Votos>
    <Voto>
      <Diputado>
        <DIPID>int</DIPID>
        <Nombre>string</Nombre>
      </Diputado>
      <Opcion />
    </Voto>
  </Votos>
  <Pareos />
</Votacion>
```

### Sesiones por legislatura

Operacion: `getSesiones`

Parametro:

- `prmLegislaturaID`: int.

Estructura relevante:

```xml
<Sesiones>
  <Sesion>
    <ID>int</ID>
    <Numero>int</Numero>
    <Fecha>dateTime</Fecha>
    <FechaTermino>dateTime</FechaTermino>
    <Tipo />
    <Estado />
  </Sesion>
</Sesiones>
```

### Boletin de sesion

Operacion: `getSesionBoletinXML`

Parametro:

- `prmSesionID`: int.

Respuesta:

- XML completo de boletin de sesion.
- El servicio devuelve `getSesionBoletinXMLResult` en SOAP y XML directo por HTTP GET/POST.

### Diputados vigentes

Operacion: `getDiputados_Vigentes`

Estructura relevante:

```xml
<Diputados>
  <Diputado>
    <DIPID>int</DIPID>
    <Nombre>string</Nombre>
    <Apellido_Paterno>string</Apellido_Paterno>
    <Apellido_Materno>string</Apellido_Materno>
    <Militancia_Actual />
    <Ejercicio_Periodo_Legislativo_Actual />
    <Correo_Electronico>string</Correo_Electronico>
  </Diputado>
</Diputados>
```

## Identificacion de proyecto y boletin

### Como se identifica un boletin

El boletin es el identificador legislativo publico del proyecto de ley.

Ejemplo oficial usado por el portal:

- `8575-05`
- Tambien acepta `8575` para la consulta de votaciones Camara.

Interpretacion tecnica:

- La forma completa contiene numero correlativo y sufijo de materia/comision o clasificacion legislativa.
- La forma corta puede resolver consultas en algunos endpoints, pero no deberia ser la clave canonica de DEO porque pierde informacion.

### Como se identifica un proyecto

En la fuente, el proyecto aparece identificado por su numero de boletin. El endpoint de Proyectos de Ley esta en el dominio Senado (`invoca_proyecto.html`) y no pudo auditarse por 403, pero el portal lo presenta como parte del dominio Tramite Legislativo.

Para DEO, `proyecto` y `boletin` no deberian ser dos entidades canonicas separadas en la primera version. El proyecto de ley deberia ser la entidad, y el boletin completo deberia ser su identificador canonico.

Recomendacion:

```text
canonical_entity_type: legislative_bill
canonical_id: cl-congreso-boletin-<boletin_normalizado>
display_id: <boletin_original>
```

Ejemplo:

```text
display_id: 8575-05
canonical_id: cl-congreso-boletin-8575-05
```

## Relaciones encontradas

### Boletin -> proyecto

El boletin identifica el proyecto. La fuente de proyecto completa esta enlazada desde Senado. Para Camara, el boletin permite recuperar votaciones relacionadas.

### Boletin/proyecto -> votaciones

Endpoint Camara:

```text
getVotaciones_Boletin?prmBoletin=<boletin>
```

Devuelve una coleccion de `Votacion`, cada una con:

- `ID` de votacion.
- fecha.
- resultado.
- quorum.
- sesion asociada.
- boletin.
- articulo.
- tramite.
- informe.
- totales.

### Votacion -> detalle de votos

Endpoint Camara:

```text
getVotacion_Detalle?prmVotacionID=<id>
```

Devuelve:

- datos de votacion;
- sesion;
- boletin;
- totales;
- votos individuales;
- diputados por `DIPID`;
- opcion de voto;
- pareos.

### Legislatura -> sesiones

Endpoint Camara:

```text
getSesiones?prmLegislaturaID=<id>
```

El `ID` de legislatura se obtiene desde:

```text
getLegislaturas
getLegislaturaActual
```

### Sesion -> detalle y boletin de sesion

Endpoints Camara:

```text
getSesionDetalle?prmSesionID=<id>
getSesionBoletinXML?prmSesionID=<id>
```

El boletin de sesion es el documento XML mas cercano al concepto "documento" dentro de la parte Camara auditada.

### Proyecto -> documentos

Estado: parcial.

Documentos confirmados:

- Boletin de sesion XML por `Sesion.ID`.

Documentos pendientes:

- Documentos propios del proyecto de ley desde Senado.
- Diario de sesion Senado.
- Informes, textos comparados, oficios u otros adjuntos que puedan venir en el endpoint Senado de proyecto/tramitacion.

No se debe implementar lectura documental hasta confirmar si esos documentos vienen como XML embebido, URLs, HTML o PDFs.

## Identificador canonico recomendado para DEO

Usar como entidad canonica:

```text
legislative_bill / cl-congreso-boletin-<boletin_completo_normalizado>
```

Reglas propuestas:

- Conservar el boletin original como `display_id`.
- Normalizar a mayusculas, sin espacios, con guion si el sufijo existe.
- No usar solo el correlativo si existe sufijo.
- Guardar variantes como aliases: `8575`, `8575-05`.
- Guardar origen: `congreso-opendata`.

Por que no usar `Votacion.ID` como canonico:

- Identifica un evento de votacion, no el proyecto.

Por que no usar `Sesion.ID` como canonico:

- Identifica una sesion parlamentaria, no el proyecto.

Por que no usar `DIPID`:

- Identifica parlamentarios, no proyectos.

## Modelo conceptual recomendado

```text
LegislativeBill
  canonical_id: cl-congreso-boletin-8575-05
  display_id: 8575-05
  source: congreso-opendata

LegislativeVote
  source_id: camara-votacion-16197
  bill_id: cl-congreso-boletin-8575-05
  session_id: camara-sesion-3162

LegislativeSession
  source_id: camara-sesion-3162
  legislature_id: camara-legislatura-46

LegislativeDocument
  source_id: camara-sesion-boletin-3162
  session_id: camara-sesion-3162
  document_type: session_bulletin_xml
```

## Riesgos tecnicos

- Senado devuelve 403 en la documentacion enlazada durante esta auditoria; requiere prueba desde cliente normal, navegador real o contacto tecnico.
- ASMX usa `tempuri.org` como namespace, senal de servicio ASP.NET antiguo.
- No hay JSON ni CSV documentados.
- Los endpoints GET son comodos, pero no son REST semantico.
- Algunas respuestas pueden incluir datos personales o de contacto de parlamentarios; tratar solo datos institucionales necesarios.
- El parametro `prmBoletin` acepta forma corta en Camara, pero DEO debe preservar forma completa.
- `getSesionBoletinXML` puede devolver XML grande; no consumir masivamente.

## Preguntas pendientes antes de integrar

- Cual es el contrato real del endpoint Senado de Proyectos de Ley.
- Si el endpoint Senado entrega documentos del proyecto o solo metadata/tramitacion.
- Si existe paginacion, limite o recomendacion de frecuencia.
- Si el portal mantiene historico completo o solo datos desde cierto periodo.
- Como se representan proyectos refundidos, boletines asociados o boletines fusionados.
- Si el numero de boletin completo siempre esta disponible en todas las respuestas.

## Fuentes oficiales consultadas

- `https://opendata.camara.cl/`
- `https://opendata.camara.cl/wscamaradiputados.asmx`
- `https://opendata.camara.cl/wscamaradiputados.asmx?op=getVotaciones_Boletin`
- `https://opendata.camara.cl/wscamaradiputados.asmx?op=getVotacion_Detalle`
- `https://opendata.camara.cl/wscamaradiputados.asmx?op=getSesiones`
- `https://opendata.camara.cl/wscamaradiputados.asmx?op=getSesionBoletinXML`
- `https://opendata.camara.cl/wscamaradiputados.asmx?op=getDiputados_Vigentes`
- `https://opendata.camara.cl/wscamaradiputados.asmx?op=getPeriodoLegislativoActual`
- `https://tramitacion.senado.cl/wspublico/invoca_proyecto.html`
- `https://tramitacion.senado.cl/wspublico/invoca_tramitacion_fecha.html`
- `https://tramitacion.senado.cl/wspublico/invoca_votacion.html`

# Official Sources Catalog

Fase: Official Sources Discovery V1.

Este catalogo registra fuentes oficiales candidatas para alimentar DatosEnOrden. No define conectores, no autoriza descarga masiva y no cambia Platform Core, Reading Pipeline, Knowledge Engine ni Publication Engine.

Estados usados:

- No evaluada: fuente identificada, falta revisar contrato tecnico.
- Lista: fuente documentada con acceso razonablemente claro, pero sin conector DEO.
- Parcial: fuente util, pero con formato, licencia, autenticacion, cobertura o estabilidad pendiente de confirmar.
- Lista para integrar: fuente con contrato tecnico claro y ruta DEO ya preparada o cercana, sin implicar consumo automatico.

## Resumen rapido

| Fuente | Institucion responsable | Tipo principal | Formatos encontrados | API publica | Estado para DEO |
| --- | --- | --- | --- | --- | --- |
| Datos Abiertos Legislativos Congreso Nacional | Congreso Nacional, Camara, Senado, BCN | Legislativa, documental | XML, HTML | Si | Lista |
| Biblioteca del Congreso Nacional | Biblioteca del Congreso Nacional | Documental, historica, parlamentaria | HTML, XML, PDF | Parcial | Parcial |
| LeyChile | Biblioteca del Congreso Nacional | Normativa | HTML, XML | Si | Lista |
| Diario Oficial | Subsecretaria del Interior / Diario Oficial | Normativa, documental | HTML, PDF, EPUB | No confirmada | Parcial |
| ChileCompra / Mercado Publico | Direccion ChileCompra | Transaccional | JSON, JSONP, XML, HTML | Si, con ticket | Lista para integrar |
| DIPRES / Presupuesto Abierto | Direccion de Presupuestos, Ministerio de Hacienda | Presupuestaria, estadistica | HTML, CSV/XLS/PDF via portales | Parcial | Parcial |
| Datos.gob.cl | Ministerio de Hacienda | Datos abiertos transversales | CSV, XLS, JSON/CKAN, HTML | Si, CKAN a validar | Lista |
| Contraloria General de la Republica | Contraloria General de la Republica | Control, dictamenes, toma de razon | HTML, PDF, buscadores | No confirmada | Parcial |
| Portal de Transparencia | Consejo para la Transparencia | Transparencia activa y solicitudes | HTML, CSV, XML | Parcial | Lista |
| Consejo para la Transparencia - Datos Abiertos | Consejo para la Transparencia | Casos, fiscalizacion, estudios | CSV, XML, XLS | Descargas publicas | Lista |
| SERVEL | Servicio Electoral | Electoral, historica, estadistica | HTML, PDF, Power BI, archivos historicos | No confirmada | Parcial |
| InfoLobby | Consejo para la Transparencia | Seguimiento, lobby, viajes, donativos | CSV, XML, JSON, RDF, SPARQL | Si | Lista |
| Ministerios y servicios sectoriales | Cada ministerio/servicio, datos.gob.cl y transparencia activa | Sectorial, estadistica, documental | HTML, PDF, CSV, XLS | Variable | No evaluada |

## 1. Datos Abiertos Legislativos Congreso Nacional

- Nombre: Datos Abiertos Legislativos Congreso Nacional.
- Institucion responsable: Congreso Nacional, Camara de Diputadas y Diputados, Senado y Biblioteca del Congreso Nacional.
- URL oficial: `https://opendata.camara.cl/`
- Tipo de informacion: tramitacion legislativa, proyectos de ley, votaciones, periodos legislativos, parlamentarios, sesiones, comisiones y referencias a LeyChile.
- Formato disponible: XML y HTML. El portal declara informacion parlamentaria y legislativa en formato XML.
- API publica: si, expuesta como servicios/enlaces XML por materia.
- CSV: no identificado como formato principal.
- JSON: no identificado.
- XML: si.
- RSS: no identificado.
- PDF: indirecto en documentos parlamentarios, no como contrato principal del portal.
- HTML: si.
- Datos abiertos: si. El portal indica reutilizacion libre de trabas o restricciones.
- Licencia: uso libre indicado por el portal; falta registrar texto legal exacto de licencia antes de integracion.
- Frecuencia de actualizacion: dependiente de actividad legislativa; debe validarse por endpoint.
- Identificador unico: numero de boletin para proyectos de ley; ids de periodo, legislatura, sesion, votacion y parlamentario segun endpoint.
- Documentacion: el portal actua como indice de servicios por dominio.
- Autenticacion: no identificada.
- Cobertura: Senado, Camara y BCN; proyectos, votaciones, sesiones, comisiones, parlamentarios y leyes publicadas.
- Estado para DEO: Lista.
- Notas DEO: fuente prioritaria para relacionar normas, proyectos, actores institucionales y votaciones sin scraping.

## 2. Biblioteca del Congreso Nacional

- Nombre: Biblioteca del Congreso Nacional.
- Institucion responsable: Biblioteca del Congreso Nacional de Chile.
- URL oficial: `https://www.bcn.cl/portal/`
- Tipo de informacion: documentacion legislativa, historia politica, informes, recursos parlamentarios, asesoria legislativa, datos territoriales y acceso a LeyChile.
- Formato disponible: HTML, PDF y servicios vinculados a LeyChile/Datos Abiertos Legislativos.
- API publica: parcial; la via tecnica mas clara es LeyChile y el indice de Datos Abiertos Legislativos.
- CSV: no identificado como formato principal.
- JSON: no identificado.
- XML: si, por LeyChile y servicios legislativos vinculados.
- RSS: no identificado.
- PDF: si, para informes/documentos.
- HTML: si.
- Datos abiertos: parcial; depende del subportal.
- Licencia: pendiente de confirmar por coleccion.
- Frecuencia de actualizacion: variable segun coleccion.
- Identificador unico: depende del recurso; para normativa aplica identificador de norma LeyChile, para proyectos aplica boletin.
- Documentacion: portal BCN y seccion de LeyChile/legislacion abierta.
- Autenticacion: no identificada para consulta publica.
- Cobertura: nacional, legislativa e historica.
- Estado para DEO: Parcial.
- Notas DEO: buena fuente documental y contextual; integrar despues de separar claramente normativa estructurada, informes PDF y contenido historico.

## 3. LeyChile

- Nombre: LeyChile.
- Institucion responsable: Biblioteca del Congreso Nacional.
- URL oficial: `https://www.bcn.cl/leychile/`
- Tipo de informacion: normativa chilena vigente, historica y metadatos de normas.
- Formato disponible: HTML y XML.
- API publica: si, indicada desde Datos Abiertos Legislativos como web service de LeyChile.
- CSV: no identificado.
- JSON: no identificado.
- XML: si; metadatos de norma, encabezado y XML completo de version actualizada.
- RSS: no identificado.
- PDF: no identificado como contrato principal.
- HTML: si.
- Datos abiertos: si, por via del servicio legislativo.
- Licencia: pendiente de texto exacto.
- Frecuencia de actualizacion: segun publicacion y modificacion normativa; debe verificarse por endpoint.
- Identificador unico: identificador de norma LeyChile, numero de ley/decreto/resolucion y fecha de publicacion.
- Documentacion: `https://www.bcn.cl/leychile/consulta/legislacion_abierta_web_service`
- Autenticacion: no identificada.
- Cobertura: normativa nacional chilena.
- Estado para DEO: Lista.
- Notas DEO: prioridad alta para lectura normativa trazable y relacion con Diario Oficial y proyectos de ley.

## 4. Diario Oficial

- Nombre: Diario Oficial de la Republica de Chile.
- Institucion responsable: Diario Oficial, integrado a la Subsecretaria del Interior.
- URL oficial: `https://www.diariooficial.interior.gob.cl/`
- Tipo de informacion: publicacion oficial de leyes, decretos, resoluciones, avisos y otras actuaciones publicas y privadas exigidas por ley.
- Formato disponible: HTML, PDF y EPUB.
- API publica: no confirmada.
- CSV: no identificado.
- JSON: no identificado.
- XML: no identificado.
- RSS: no identificado.
- PDF: si.
- HTML: si.
- Datos abiertos: acceso publico a ediciones, pero sin contrato de datos abiertos estructurados confirmado.
- Licencia: condiciones de uso de publicaciones disponibles en el sitio; revisar antes de reutilizacion.
- Frecuencia de actualizacion: dias habiles de lunes a sabado y ediciones extraordinarias.
- Identificador unico: CVE, fecha de publicacion, seccion, edicion y URL de publicacion.
- Documentacion: secciones "Quienes somos", "Edicion electronica", "Versiones anteriores" y verificacion por CVE.
- Autenticacion: no para consulta publica basica; publicacion en linea puede usar servicios separados.
- Cobertura: Diario Oficial desde 1877 para versiones historicas; edicion electronica vigente desde agosto de 2016.
- Estado para DEO: Parcial.
- Notas DEO: fuente normativa primaria para evidencia de publicacion. Integrar primero por CVE y documentos individuales, no por scraping masivo.

## 5. ChileCompra / Mercado Publico

- Nombre: API de Mercado Publico / ChileCompra.
- Institucion responsable: Direccion de Compras y Contratacion Publica, ChileCompra.
- URL oficial: `https://www.chilecompra.cl/api/`
- Tipo de informacion: licitaciones, ordenes de compra, organismos compradores y proveedores.
- Formato disponible: JSON, JSONP, XML y HTML de documentacion.
- API publica: si, gratuita y de uso publico, con ticket.
- CSV: no como contrato principal de API; existe portal de datos abiertos ChileCompra separado a evaluar.
- JSON: si.
- XML: si.
- RSS: no identificado.
- PDF: no como contrato principal.
- HTML: si.
- Datos abiertos: si, ademas de portal de datos abiertos asociado.
- Licencia: condiciones de uso del API; revisar antes de produccion.
- Frecuencia de actualizacion: datos en tiempo real segun documentacion.
- Identificador unico: codigo de licitacion, codigo de organismo, codigo de proveedor, codigo de orden de compra.
- Documentacion: pagina API de Mercado Publico y modulos de licitacion/orden de compra.
- Autenticacion: ticket solicitado con Clave Unica; se usa como parametro `ticket`.
- Cobertura: compras publicas de organismos que transan en Mercado Publico.
- Estado para DEO: Lista para integrar.
- Notas DEO: ya existe ruta conceptual y tecnica en el repo para carga controlada desde archivo local; no activar consumo API en esta fase.

## 6. DIPRES / Presupuesto Abierto

- Nombre: Direccion de Presupuestos / Presupuesto Abierto.
- Institucion responsable: Direccion de Presupuestos, Ministerio de Hacienda.
- URL oficial: `https://www.dipres.gob.cl/` y `https://presupuestoabierto.gob.cl/`
- Tipo de informacion: presupuesto publico, ejecucion presupuestaria, reportes por partida, capitulo, programa, proveedores/receptores y gestion fiscal.
- Formato disponible: HTML, visualizaciones, reportes descargables y datasets publicados tambien en datos.gob.cl.
- API publica: parcial/no confirmada para Presupuesto Abierto; datos.gob.cl entrega una via abierta a validar.
- CSV: si, en datasets publicados en datos.gob.cl y/o descargas asociadas.
- JSON: posible via CKAN/datos.gob.cl; validar antes de integracion.
- XML: no identificado como contrato principal.
- RSS: no identificado.
- PDF: si, informes y documentos presupuestarios.
- HTML: si.
- Datos abiertos: si, por Presupuesto Abierto y datos.gob.cl.
- Licencia: usar terminos de datos.gob.cl y condiciones DIPRES; pendiente registrar licencia dataset por dataset.
- Frecuencia de actualizacion: mensual para ejecucion presupuestaria observada en datos.gob.cl; anual y periodica para ley/reportes.
- Identificador unico: ano presupuestario, partida, capitulo, programa, subtitulo/item/asignacion, institucion, proveedor/receptor segun dataset.
- Documentacion: sitios DIPRES, Presupuesto Abierto, Biblioteca Digital DIPRES y datasets de datos.gob.cl.
- Autenticacion: no identificada para consulta publica.
- Cobertura: Gobierno Central y servicios publicos segun publicacion.
- Estado para DEO: Parcial.
- Notas DEO: fuente de alto valor ciudadano; integrar despues de fijar granularidad minima y diccionario presupuestario.

## 7. Datos.gob.cl

- Nombre: Portal de Datos Abiertos del Estado.
- Institucion responsable: Ministerio de Hacienda.
- URL oficial: `https://datos.gob.cl/`
- Tipo de informacion: datasets abiertos del sector publico, publicados por instituciones.
- Formato disponible: HTML y formatos de recursos por dataset, tipicamente CSV, XLS, JSON, GeoJSON, PDF u otros segun publicador.
- API publica: si, plataforma compatible con catalogo CKAN a validar tecnicamente.
- CSV: si.
- JSON: si, segun dataset y API de catalogo.
- XML: variable.
- RSS: no identificado.
- PDF: variable.
- HTML: si.
- Datos abiertos: si.
- Licencia: terminos y condiciones de datos.gob.cl; ademas revisar licencia por dataset.
- Frecuencia de actualizacion: definida por cada dataset/institucion.
- Identificador unico: slug/id del dataset, id de recurso, institucion publicadora.
- Documentacion: guias, preguntas frecuentes y tutoriales del portal.
- Autenticacion: no para descarga publica; login solo para publicadores/usuarios.
- Cobertura: transversal del Estado; al momento de revision el portal indica miles de conjuntos de datos y cientos de instituciones.
- Estado para DEO: Lista.
- Notas DEO: debe funcionar como catalogo auxiliar, no como sustituto de la fuente primaria cuando exista una fuente institucional mas especifica.

## 8. Contraloria General de la Republica

- Nombre: Contraloria General de la Republica.
- Institucion responsable: Contraloria General de la Republica.
- URL oficial: `https://www.contraloria.cl/`
- Tipo de informacion: dictamenes, oficios, toma de razon, auditorias, informes, jurisprudencia administrativa, control de legalidad y contabilidad publica.
- Formato disponible: HTML, PDF y buscadores institucionales.
- API publica: no confirmada.
- CSV: no identificado como contrato publico general.
- JSON: no identificado.
- XML: no identificado.
- RSS: no identificado.
- PDF: si.
- HTML: si.
- Datos abiertos: parcial/no confirmado para los dominios principales.
- Licencia: pendiente.
- Frecuencia de actualizacion: continua segun emision de actos, dictamenes e informes.
- Identificador unico: numero de dictamen/oficio, fecha, numero de acto o toma de razon, organismo, expediente cuando corresponda.
- Documentacion: sitio institucional y buscadores de jurisprudencia/actos; requiere auditoria manual especifica.
- Autenticacion: no identificada para consulta publica general; algunos servicios pueden requerir sesion.
- Cobertura: Administracion del Estado, municipalidades y organismos sujetos a fiscalizacion.
- Estado para DEO: Parcial.
- Notas DEO: alto valor para trazabilidad juridico-administrativa, pero debe integrarse solo si existe contrato descargable o autorizacion tecnica clara.

## 9. Portal de Transparencia

- Nombre: Portal de Transparencia del Estado.
- Institucion responsable: Consejo para la Transparencia.
- URL oficial: `https://www.portaltransparencia.cl/` y pagina CPLT `https://www.consejotransparencia.cl/portal-de-transparencia/`
- Tipo de informacion: solicitudes de acceso a informacion, transparencia activa, directorio de organismos y plantillas de publicacion.
- Formato disponible: HTML, descargas y catalogos vinculados desde CPLT.
- API publica: parcial; el CPLT declara posibilidad de descarga y consulta de datos para el Portal.
- CSV: si, via catalogos/datos abiertos CPLT.
- JSON: no confirmado para Portal principal.
- XML: si, en catalogos CPLT.
- RSS: no identificado.
- PDF: si, documentos y guias.
- HTML: si.
- Datos abiertos: si, via catalogo CPLT.
- Licencia: catalogo CPLT permite reutilizacion; revisar condiciones exactas antes de produccion.
- Frecuencia de actualizacion: de acuerdo a cada catalogo.
- Identificador unico: organismo, solicitud/caso, reclamo, decision y codigos internos del portal.
- Documentacion: pagina CPLT de Portal de Transparencia, plantillas, manuales y datos abiertos.
- Autenticacion: no para datos abiertos; solicitudes ciudadanas pueden requerir flujos de usuario.
- Cobertura: organismos regulados por Ley 20.285.
- Estado para DEO: Lista.
- Notas DEO: integrar como fuente de transparencia institucional, separando solicitudes/casos de transparencia activa.

## 10. Consejo para la Transparencia - Datos Abiertos

- Nombre: Catalogo de Datos Abiertos CPLT.
- Institucion responsable: Consejo para la Transparencia.
- URL oficial: `https://www.consejotransparencia.cl/datosabiertos/`
- Tipo de informacion: casos ante el CPLT, organismos reclamados, estados historicos, motivos, infracciones, estudios, Portal de Transparencia, InfoLobby e InfoProbidad.
- Formato disponible: CSV, XML y XLS.
- API publica: descargas publicas; API formal no identificada.
- CSV: si.
- JSON: no como formato principal en CPLT; si aparece en InfoLobby/InfoProbidad.
- XML: si.
- RSS: no identificado.
- PDF: no como contrato principal.
- HTML: si.
- Datos abiertos: si.
- Licencia: el catalogo declara reutilizacion sin registro; revisar condiciones exactas.
- Frecuencia de actualizacion: varios catalogos indican Mar-Sab 05:00 o "de acuerdo a cada catalogo".
- Identificador unico: id de caso, organismo, estado, motivo/infraccion, encuesta o dataset.
- Documentacion: pagina de Datos Abiertos CPLT.
- Autenticacion: no requiere registro segun el catalogo.
- Cobertura: CPLT, Portal de Transparencia, estudios nacionales, InfoLobby e InfoProbidad.
- Estado para DEO: Lista.
- Notas DEO: buena fuente estructurada para iniciar transparencia sin scraping.

## 11. SERVEL

- Nombre: Servicio Electoral de Chile.
- Institucion responsable: Servicio Electoral.
- URL oficial: `https://www.servel.cl/`
- Tipo de informacion: resultados historicos, padrones definitivos, procesos electorales, estadisticas, partidos politicos, campanas, documentos presupuestarios.
- Formato disponible: HTML, PDF, Power BI, archivos historicos y documentos descargables.
- API publica: no confirmada.
- CSV: no confirmado como formato general; puede existir en archivos especificos.
- JSON: no identificado.
- XML: no identificado.
- RSS: no identificado.
- PDF: si.
- HTML: si.
- Datos abiertos: parcial; centro de datos publico, pero contrato estructurado variable.
- Licencia: pendiente de confirmar por recurso.
- Frecuencia de actualizacion: por proceso electoral y publicaciones administrativas.
- Identificador unico: eleccion, circunscripcion/distrito/comuna, mesa, local, candidato/lista/partido, padron y fecha de proceso.
- Documentacion: Centro de Datos, resultados historicos, estadisticas, procesos electorales, archivo historico.
- Autenticacion: no para consulta publica general; consulta individual de datos electorales puede tener restricciones.
- Cobertura: elecciones y plebiscitos nacionales, regionales, municipales y otros procesos publicados.
- Estado para DEO: Parcial.
- Notas DEO: comenzar con resultados historicos agregados y documentos oficiales, no con datos personales de padron.

## 12. InfoLobby

- Nombre: InfoLobby.
- Institucion responsable: Consejo para la Transparencia.
- URL oficial: `https://www.infolobby.cl/`
- Tipo de informacion: audiencias, viajes, donativos, sujetos pasivos, sujetos activos, lobistas y gestores de intereses.
- Formato disponible: CSV, XML, JSON, RDF, SPARQL y HTML.
- API publica: si, endpoint SPARQL y catalogos descargables.
- CSV: si.
- JSON: si, segun catalogos.
- XML: si.
- RSS: no identificado.
- PDF: no como contrato principal.
- HTML: si.
- Datos abiertos: si.
- Licencia: datos abiertos; revisar condiciones especificas del sitio.
- Frecuencia de actualizacion: de acuerdo a cada catalogo/registro.
- Identificador unico: id de audiencia/viaje/donativo, organismo, sujeto pasivo, sujeto activo y fechas.
- Documentacion: Datos Abiertos, ontologia de Ley del Lobby y endpoint SPARQL.
- Autenticacion: no identificada para datos abiertos.
- Cobertura: sujetos obligados por Ley 20.730.
- Estado para DEO: Lista.
- Notas DEO: fuente prioritaria para seguimiento institucional; mantener lenguaje informativo y no inferencial.

## 13. Ministerios y servicios sectoriales

- Nombre: Ministerios y servicios sectoriales.
- Institucion responsable: cada ministerio/servicio; catalogo transversal en datos.gob.cl y obligaciones de transparencia activa.
- URL oficial: `https://www.gob.cl/instituciones/`, `https://datos.gob.cl/`, sitios ministeriales y Portal de Transparencia.
- Tipo de informacion: planes, programas, estadisticas sectoriales, actos administrativos, transferencias, compras, personal, presupuesto, documentos oficiales.
- Formato disponible: HTML, PDF, CSV, XLS y formatos variables por institucion.
- API publica: variable.
- CSV: variable.
- JSON: variable.
- XML: variable.
- RSS: variable.
- PDF: si, muy frecuente.
- HTML: si.
- Datos abiertos: variable; muchos datasets pasan por datos.gob.cl.
- Licencia: depende de cada dataset o sitio institucional.
- Frecuencia de actualizacion: variable por obligacion legal, programa o dataset.
- Identificador unico: organismo, programa, acto administrativo, dataset, periodo, region/comuna, unidad ejecutora.
- Documentacion: datos.gob.cl, transparencia activa, manuales sectoriales y paginas institucionales.
- Autenticacion: generalmente no para informacion publica; algunos sistemas sectoriales requieren usuario.
- Cobertura: Gobierno Central, servicios, subsecretarias y organismos dependientes.
- Estado para DEO: No evaluada.
- Notas DEO: no iniciar integracion ministerial generica; priorizar ministerios cuando exista pregunta ciudadana concreta y dataset oficial estructurado.

## Fuentes oficiales consultadas

- `https://opendata.camara.cl/`
- `https://www.bcn.cl/portal/`
- `https://www.bcn.cl/leychile/`
- `https://www.bcn.cl/leychile/consulta/legislacion_abierta_web_service`
- `https://www.diariooficial.interior.gob.cl/`
- `https://www.diariooficial.interior.gob.cl/quienes-somos/`
- `https://www.diariooficial.interior.gob.cl/edicionelectronica/`
- `https://www.diariooficial.interior.gob.cl/versiones-anteriores/`
- `https://www.chilecompra.cl/api/`
- `https://www.dipres.gob.cl/`
- `https://presupuestoabierto.gob.cl/`
- `https://datos.gob.cl/`
- `https://www.contraloria.cl/`
- `https://www.consejotransparencia.cl/portal-de-transparencia/`
- `https://www.consejotransparencia.cl/datosabiertos/`
- `https://www.infolobby.cl/`
- `https://www.infolobby.cl/DatosAbiertos`
- `https://www.servel.cl/`
- `https://www.servel.cl/centro-de-datos/resultados-electorales-historicos-gw3/`

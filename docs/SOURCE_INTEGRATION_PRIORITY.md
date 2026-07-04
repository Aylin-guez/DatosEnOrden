# Source Integration Priority

Fase: Official Sources Discovery V1.

Este documento prioriza fuentes oficiales candidatas. No autoriza implementacion, conectores, scraping, consumo API ni descarga masiva.

## Criterios

- Valor ciudadano: capacidad de responder preguntas publicas comprensibles.
- Facilidad tecnica: disponibilidad de contrato estable, formatos estructurados, documentacion y autenticacion simple.
- Calidad de datos: identificadores, cobertura, granularidad, trazabilidad y actualizacion.
- Frecuencia de uso: probabilidad de uso en busqueda, expedientes, reportes y biblioteca ciudadana.

## Prioridad 1

Fuentes con alto valor ciudadano y contrato tecnico relativamente claro.

| Fuente | Motivo | Estado recomendado |
| --- | --- | --- |
| ChileCompra / Mercado Publico | Alto valor para compras publicas; API oficial con JSON/XML; identificadores claros para licitaciones, ordenes, compradores y proveedores. | Mantener como primera fuente transaccional; solo carga controlada desde archivo hasta autorizar API. |
| LeyChile | Base normativa estructurada; XML oficial; identificadores normativos; relacion directa con Diario Oficial y Congreso. | Preparar contrato documental/normativo antes de cualquier loader. |
| Datos Abiertos Legislativos Congreso Nacional | Proyectos, votaciones, parlamentarios y sesiones en XML; alto valor para trazar ciclo legislativo. | Auditar endpoints y diccionario antes de integracion. |
| Consejo para la Transparencia - Datos Abiertos | CSV/XML sin registro, casos y Portal de Transparencia; buena estructura para transparencia institucional. | Priorizar datasets de casos y organismos. |
| InfoLobby | CSV/XML/JSON/RDF/SPARQL; alto valor de seguimiento institucional; identificadores por audiencia/viaje/donativo. | Priorizar catalogos descargables antes de SPARQL. |
| Datos.gob.cl | Catalogo transversal; util para descubrir datasets oficiales y DIPRES. | Usar como catalogo auxiliar, no como unica fuente cuando exista portal primario. |

## Prioridad 2

Fuentes de alto valor, pero con contrato tecnico o alcance que requiere mas delimitacion.

| Fuente | Motivo | Estado recomendado |
| --- | --- | --- |
| DIPRES / Presupuesto Abierto | Muy alto valor ciudadano; presupuestos y ejecucion; granularidad requiere diccionario y versionado. | Auditar datasets especificos de ejecucion mensual y ley de presupuestos. |
| Diario Oficial | Fuente primaria de publicacion normativa; CVE y PDF/EPUB utiles; no se confirmo API estructurada. | Integrar solo por documentos identificados y CVE, sin scraping masivo. |
| Portal de Transparencia | Alto valor; cobertura amplia; acceso directo puede tener restricciones; datos abiertos CPLT son la ruta mas clara. | Usar datos abiertos CPLT primero; auditar Portal principal despues. |
| SERVEL | Resultados historicos y estadisticas tienen valor ciudadano; formatos combinan HTML, Power BI y archivos. | Priorizar resultados historicos agregados y documentos oficiales; excluir datos personales. |
| Contraloria | Dictamenes, toma de razon e informes son centrales para control publico; API/descarga estructurada no confirmada. | Requiere auditoria tecnica especifica antes de cualquier integracion. |

## Prioridad 3

Fuentes amplias o heterogeneas que deben esperar una pregunta ciudadana concreta.

| Fuente | Motivo | Estado recomendado |
| --- | --- | --- |
| Biblioteca del Congreso Nacional documental | Alto valor contextual, pero mezcla informes, portales, PDFs y colecciones; LeyChile ya cubre la parte normativa prioritaria. | Mantener como fuente documental candidata. |
| Ministerios y servicios sectoriales | Muy amplia; formatos y calidad dependen de cada organismo; riesgo de integracion desordenada. | Seleccionar caso por caso desde datos.gob.cl o transparencia activa. |
| InfoProbidad | Potencialmente valiosa, pero implica datos sensibles y requiere politica de tratamiento cuidadosa. | Evaluar en fase separada con reglas de privacidad y uso publico. |

## Prioridad sugerida de ejecucion futura

1. Consolidar inventario tecnico final de ChileCompra, LeyChile, Datos Abiertos Legislativos, CPLT Datos Abiertos e InfoLobby.
2. Definir contratos de datos por fuente antes de programar: campos, identificadores, licencia, frecuencia, limites y ejemplos pequenos.
3. Preparar fixtures manuales pequenos y marcados como `LOCAL_TEST_DATA` / `NOT_OFFICIAL_DATA` solo cuando se autorice la fase tecnica.
4. Evaluar DIPRES y Diario Oficial como segunda capa, con una decision explicita sobre granularidad y documentos.
5. Dejar Contraloria, SERVEL y ministerios para auditorias especificas por dominio.

## Recomendacion

La prioridad 1 deberia concentrarse en fuentes con datos estructurados y trazabilidad clara. La primera integracion real no deberia mezclar dominios: compras publicas, normativa, legislativo, transparencia y lobby deben entrar como lineas separadas, con identificadores propios y sin conclusiones automaticas.

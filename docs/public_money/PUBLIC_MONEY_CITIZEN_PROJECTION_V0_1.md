# Proyección ciudadana de Dinero Público v0.1

**Estado:** diseño conceptual. No implementa UI, ruta, menú ni componente productivo.

## Propuesta: `PublicMoneySummary`

`PublicMoneySummary` es una proyección reutilizable, secundaria al expediente, que organiza observaciones monetarias verificadas sin convertirlas en un balance inventado. Debe responder rápidamente:

- ¿cuánto dinero está involucrado y con qué universo?
- ¿de qué organismo salió, a qué entidad llegó y por cuál instrumento?
- ¿qué se rindió, aprobó u observó, y a qué fecha?
- ¿se ordenó devolver dinero y sabemos cuánto fue recuperado?
- ¿qué corresponde a control administrativo, investigación o decisión judicial?

No se muestra si falta evidencia suficiente y no sustituye documentos, fuentes, cronología, limitaciones ni preguntas ciudadanas.

## Estructura propuesta

1. **Alcance del dinero identificado.** Monto, moneda, medida exacta, universo, fecha y fuente. La etiqueta debe decir “transferido”, “presupuestado” u otra métrica real, nunca un término acusatorio.
2. **Instrumentos identificados.** Filas o tarjetas reutilizables con número, fecha, origen, receptor, objeto, monto y evidencia.
3. **Cortes de rendición o ejecución.** Bloques fechados que agrupan solamente métricas de la misma fuente y corte. Deben aclarar que rendido no implica necesariamente aprobado.
4. **Actuaciones posteriores.** Término, liquidación, orden de restitución, cobro o recuperación efectiva como observaciones independientes.
5. **Fiscalización y procedimiento.** Hallazgos administrativos e investigación penal claramente separados, con sus límites epistemológicos.
6. **Lo no acreditado.** Desconocidos explícitos: recuperación sin evidencia, rendiciones no disponibles o ausencia de sentencia en el corpus.

Cada bloque conserva fecha/corte y enlace de evidencia. No puede calcular remanentes si la fuente no los publica o los universos no son comparables.

## Ejemplo: Democracia Viva–Antofagasta

### Convenios y transferencias

**$426.000.000 transferidos mediante tres convenios** entre la SEREMI MINVU Antofagasta y Fundación Democracia Viva:

| Instrumento | Monto | Objeto |
| --- | ---: | --- |
| RE 504/2022 | $200.000.000 | Habitabilidad primaria — Ecuachilepe |
| RE 576/2022 | $170.000.000 | Habitabilidad primaria — Irarrázabal Etapa I |
| RE 641/2022 | $56.000.000 | Diagnósticos e intervención socio-territorial |

### Corte CGR: 30 de junio de 2023

Dentro de ese corte y universo de auditoría, la CGR informó:

- rendido: **$116.963.639**;
- aprobado por la SEREMI: **$12.146.280**;
- por rendir: **$309.036.361**.

La proyección debe explicar que “por rendir” no equivale a dinero robado y que “rendido” no equivale necesariamente a “aprobado”.

### Actuación administrativa posterior

MINVU informó **$391.768.516 ordenados a restituir**. Se presenta como orden administrativa separada del corte CGR. La recuperación efectiva es **no acreditada en el corpus**, no cero ni monto recuperado.

### Proceso y límites

Los hallazgos de la CGR se presentan como fiscalización administrativa. Las formalizaciones documentadas se muestran como estado del proceso penal. No se afirma condena penal de fondo sin resolución judicial competente.

## Reglas de presentación

- No usar una barra única que sume transferido, rendido, observado, restitución ordenada y recuperado.
- No convertir un vacío documental en $0 ni una orden de devolución en pago.
- Mostrar `UNKNOWN` como “No acreditado en el corpus”.
- Mantener indicador, fecha de corte y fuente junto a cada monto.
- Distinguir quien informa, quien fiscaliza y el tribunal competente.
- Evitar color, iconografía o copy que sugiera delito o culpa por asociación.
- Mantener tablas accesibles y su equivalente textual.

## Futura superficie “¿En qué se gastó mi dinero?”

Será una capacidad transversal de DatosEnOrden, no una aplicación separada. Permitirá navegación en ambos sentidos:

`presupuesto → organismo → programa → instrumento → receptor → rendición → fiscalización → hallazgo → investigación → resultado`

y desde una entidad receptora hacia instrumentos y organismos que la evidencia conecte. Reutilizará entidades, documentos, fuentes, evidencias, relaciones y expedientes del Core. No se implementa hasta decidir identidad, observación temporal y comparabilidad conforme al documento de modelo.

## Gates de implementación futura

- `TRANSFER_IS_NOT_THEFT`;
- `RENDERED_IS_NOT_APPROVED`;
- `UNRENDERED_IS_NOT_STOLEN`;
- `RESTITUTION_ORDER_IS_NOT_RECOVERY`;
- `AUDIT_FINDING_IS_NOT_CRIMINAL_GUILT`;
- `FORMALIZATION_IS_NOT_CONVICTION`;
- `AMOUNT_UNIVERSE_REQUIRED`;
- `CUT_OFF_DATE_REQUIRED` cuando corresponda;
- `OCR_IS_NOT_SOURCE`;
- `UNKNOWN_AND_NOT_COMPARABLE_VISIBLE`.

**Schema change required:** No en esta fase. Este documento guía una decisión posterior; no es una especificación de implementación automática.

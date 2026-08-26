# Modelo de Dinero Público v0.1

**Estado:** discovery y diseño. No constituye schema, contrato Core ni una superficie de producto implementada.

**Caso canónico:** `EXP-REAL-DEMOCRACIA-VIVA-ANTOFAGASTA`.

## Propósito

La dimensión de Dinero Público permite seguir evidencia pública desde un instrumento o movimiento hasta ejecución, rendición, fiscalización y resultado. Es una capacidad adicional: no reemplaza expedientes, entidades, fuentes, cronologías ni otras superficies ciudadanas.

Debe representar una compra regular, una transferencia bien rendida, una observación administrativa y una causa judicial sin inferir una relación no acreditada.

## Restricciones confirmadas por el caso canónico

Los $426.000.000 transferidos mediante tres convenios, el corte CGR del 30 de junio de 2023 y la restitución ordenada posterior son observaciones de universos, fechas y efectos distintos. No son componentes sumables de un saldo único.

- presupuestado ≠ adjudicado ≠ convenido/contratado ≠ transferido ≠ pagado;
- ejecutado ≠ rendido ≠ aprobado ≠ observado ≠ rechazado;
- monto investigado ≠ perjuicio acreditado;
- restitución ordenada ≠ recuperado;
- responsabilidad administrativa ≠ civil ≠ penal ≠ condena.

Una transferencia, observación CGR, formalización o decisión administrativa no prueba por sí misma robo, culpabilidad ni condena.

## Reutilización del Core actual

| Capacidad existente | Uso en Dinero Público |
| --- | --- |
| `Entity` | organismos, receptoras, programas e instrumentos identificables |
| `Claim` | afirmaciones acotadas sobre monto, estado, fecha y relación |
| `Evidence` y `SourceRecord` | documento oficial, URL, hash, página y locator |
| `RelationshipPublic` | vínculo documentado entre organismo, convenio y entidad |
| cronología | convenio, acto, corte de auditoría y actuación procesal |
| `CitizenExpedientProjection` | explicación ciudadana, límites y preguntas |

El caso prueba que el Core actual permite una representación honesta. También muestra que el ciudadano debe reconstruir estados monetarios desde claims dispersos.

## Capacidades candidatas, no aprobadas

| Candidato | Problema que resolvería | Capa propuesta | Estado |
| --- | --- | --- | --- |
| Instrumento de dinero público | Identidad de convenio, contrato, transferencia, orden o resolución. | Core candidato | Identidad necesaria, no tabla aprobada. |
| Observación monetaria | Monto con métrica, alcance y fecha de corte. | Core candidato | Confirmado; no es un único `status`. |
| Instantánea de rendición | Transferido, rendido, aprobado, observado o pendiente dentro de un corte. | Core candidato | Confirmado. |
| Acción de restitución/recuperación | Separar orden, cobro, pago y recuperación parcial. | Core candidato | Confirmado. |
| Auditoría y hallazgo | Alcance, hallazgo, recomendación y seguimiento sin atribuir delito. | Reuso + relación | Confirmado. |
| Investigación/procedimiento | Vínculo explícito con etapa y resultado competente. | Reuso + relación | Requiere más casos. |

No se debe convertir esta tabla en enums definitivos ni schema todavía.

## Taxonomía de observaciones monetarias

En vez de una columna lineal de estado, una futura observación declara su familia semántica:

1. Asignación o compromiso: presupuesto, asignación, adjudicación, contratación o convenio.
2. Flujo: transferencia, pago, devolución o reintegro materialmente acreditado.
3. Ejecución y rendición: ejecutado, rendido, aprobado, observado, rechazado o pendiente, con corte y autoridad.
4. Control administrativo: auditoría, hallazgo, medida correctiva, liquidación, término u orden de restitución.
5. Procedimiento y resultado: investigación administrativa o penal, formalización, demanda, sentencia o resolución final.

Una cifra puede tener varias relaciones documentales, pero no adquiere un significado nuevo sólo por aparecer en otro bloque.

## Modelo temporal y de comparabilidad

Cada observación futura debe conservar medida, moneda, monto conocido/`UNKNOWN`/`NOT_COMPARABLE`, alcance documentado, fecha del evento, fecha de corte o período, autoridad, documento de respaldo y corrección posterior si existe.

Sólo se comparan montos de misma medida, universo y corte. De lo contrario la proyección muestra ambas cifras por separado, sin diferencias, porcentajes ni barras apiladas. Una rectificación enlaza la observación anterior; una recuperación parcial es un flujo nuevo, no el estado implícito de una orden.

## Provenance y extracción

Cada dato debe resolver a `claim → evidence → documento oficial → hash → página/locator`. Para originales escaneados, OCR es método de extracción verificado contra la página, nunca fuente autónoma. Un monto, RUT, fecha, acto o nombre ambiguo permanece `UNVERIFIED`, `UNKNOWN` u `OCR_UNCERTAIN`; nunca se normaliza por inferencia aritmética.

## Compatibilidad de fuentes futuras

| Fuente | Aporte probable | Límite |
| --- | --- | --- |
| DIPRES | presupuesto, programa y ejecución agregada | no identifica necesariamente cada receptor o convenio |
| ChileCompra | compra, orden, contrato y proveedor | no equivale a transferencia, rendición ni resultado judicial |
| organismo otorgante / Transparencia | acto, convenio, transferencia y rendición disponible | cobertura y formato varían |
| CGR | auditoría, alcance, hallazgos y seguimiento | hallazgo no es culpabilidad penal |
| Fiscalía | investigación y actuaciones públicas | investigación/formalización no es condena |
| Poder Judicial | resolución y resultado del procedimiento | una resolución puede no decidir el fondo penal |

## Preguntas abiertas antes de schema

1. ¿Qué identidad puede vincular acto, convenio, transferencia y rendición sin inventar equivalencias?
2. ¿Una observación monetaria necesita identidad propia o un claim estructurado versionado?
3. ¿Qué regla reusable declara dos montos comparables?
4. ¿Cómo representar instrumentos y cortes múltiples sin ocultar provenance?

**Schema change required:** No. Antes de decidirlo, contrastar una compra ChileCompra, una transferencia no controvertida y una rendición cerrada correctamente.

# Descubrimiento v0.1: trazabilidad de dinero público

**Caso de descubrimiento:** denominado “Caso Convenios”
**Corte de búsqueda:** 25 de agosto de 2026
**Estado:** discovery oficial suficiente para delimitar el problema; insuficiente para un expediente paraguas con inventario financiero único.

## Decisión de alcance

“Caso Convenios” no debe modelarse, por ahora, como un único hecho, una única
causa judicial ni una única cifra de dinero. La Cuenta Pública 2025 del Ministerio
Público informa, con corte a abril de 2025, 134 RUC asociados, 45 personas
formalizadas (50 formalizaciones) y un monto nacional investigado superior a
$70 mil millones. Esa cifra es el universo de una investigación penal informado
por Fiscalía; no acredita por sí sola transferencias efectuadas, rendiciones
pendientes, observaciones de Contraloría, perjuicio fiscal definitivo, recuperos
ni condenas.

La recomendación es una **colección temática futura** que conecte aristas y
expedientes independientes, no un expediente paraguas que colapse sus estados.
La primera arista potencialmente materializable es la relación entre la Seremi
MINVU de Antofagasta y Fundación Democracia Viva, pero requiere adquirir y
normalizar su corpus primario completo antes de crear un expediente ciudadano.

## Semántica que debe preservarse

Una transferencia no prueba un gasto ejecutado, una irregularidad, un delito ni
una condena. Una observación administrativa no prueba por sí misma un delito.
Una investigación, una formalización, una acusación fiscal o una medida cautelar
no equivalen a culpabilidad. Un monto ordenado restituir tampoco debe exponerse
como monto recuperado sin una fuente que acredite el recupero.

Por eso, los importes no se agregarán sin conservar su universo, fecha de corte,
institución que informa y tipo semántico.

## Confirmado desde fuentes oficiales

### Alcance y estructura del fenómeno

- La Fiscalía denominó “Caso Convenios” a un fenómeno con causas y aristas
  múltiples. Al 25 de junio de 2026 informó que las aristas Democracia Viva,
  Fibra, Tomarte y Fusupo estaban agrupadas en una investigación, y describió
  una contienda de competencia aún en desarrollo.
- La Cuenta Pública 2025 del Ministerio Público, con corte a abril de 2025,
  informó 134 RUC asociados, 45 personas formalizadas, 50 formalizaciones y
  más de $70 mil millones como monto total investigado a nivel nacional.
- El CDE informó el 11 de julio de 2023 que analizaba antecedentes en al menos
  nueve regiones. Esta es evidencia institucional de dispersión territorial,
  no un inventario financiero comparable.

### Arista Democracia Viva — universo administrativo inicial

- MINVU informó que la Seremi de Antofagasta puso término anticipado a tres
  convenios de transferencia celebrados el 20 de septiembre de 2022 con
  Fundación Democracia Viva, para proyectos de habitabilidad primaria.
- La misma comunicación identifica $426.000.000 como monto originalmente
  transferido y, al momento de la liquidación administrativa del 14 de julio de
  2023, ordenó restitución de $391.768.516. MINVU explicó que el 8% correspondía
  a recursos correctamente rendidos, no observados y ejecutados a esa fecha.
- Esos tres valores son un universo administrativo, con fecha de corte y
  metodología propia. No son el total del denominado Caso Convenios, ni el
  monto recuperado, ni una declaración judicial de daño definitivo.
- El Poder Judicial informó que la Corte de Apelaciones de Antofagasta rechazó
  el recurso de protección de Fundación Democracia Viva contra el término de
  los convenios (Rol 6.594-2023). Esa decisión trata la impugnación del acto
  administrativo; no decide responsabilidad penal.
- Fiscalía informó en diciembre de 2023 la formalización de dos imputados en
  la arista Democracia Viva por tres delitos de fraude al Fisco y precisó que
  la etapa judicializada continuaría para que un tribunal oral se pronunciara
  sobre culpabilidad o no. El perjuicio de $426 millones aparece en esa fuente
  como antecedente expuesto por Fiscalía, no como condena.

### Fiscalización administrativa

- Documentación oficial de MINVU identifica el Informe Final de Investigación
  Especial N° 465-1, de 31 de agosto de 2023, de Contraloría, sobre
  transferencias del Programa de Asentamientos Precarios, y el Informe Final
  N° 465-3, de 27 de marzo de 2024, sobre controles para concluir la revisión
  de rendiciones pendientes y cerrar convenios oportunamente.
- Estos antecedentes justifican separar convenio/transferencia, rendición,
  auditoría o informe, hallazgo y medidas de seguimiento. No permiten, sin
  adquirir sus textos completos, convertir cada referencia institucional en un
  hallazgo individual persistido.

## Candidatos, no hechos persistibles todavía

| Candidato | Razón | Estado |
| --- | --- | --- |
| Expediente paraguas “Caso Convenios” | Existe como denominación institucional y fenómeno de múltiples aristas. | No materializar: faltan inventario normalizado y relación primaria entre causas, transferencias, rendiciones y resultados. |
| Expediente “Seremi MINVU Antofagasta — Democracia Viva” | Tiene tres convenios y montos administrativos identificados por MINVU, además de fuentes judiciales y de Fiscalía. | Adquirir primero convenios, resoluciones de término/liquidación, informe CGR y resoluciones judiciales completas. |
| Total nacional transferido | No hay una fuente oficial revisada que entregue un universo único y comparable. | `UNKNOWN / MULTIPLE_UNIVERSES`. |
| Total nacional observado, no rendido, recuperado o condenado | Las fuentes revisadas usan universos y etapas distintas. | `NOT_COMPARABLE`; no sumar ni inferir. |

## Capacidades de Dinero Público descubiertas

| Capacidad candidata | Evidencia que la exige | Equivalente actual | Capa propuesta | Impacto de schema | Confianza |
| --- | --- | --- | --- | --- | --- |
| Movimiento de dinero público | El mismo caso distingue monto transferido, restitución ordenada y monto investigado. | Hechos, documentos y evidencia; ChileCompra representa compras, no necesariamente transferencias. | Core candidato | Por decidir; no crear aún. | Alta |
| Convenio / acto administrativo | Tres convenios y resoluciones de término constituyen instrumentos identificables. | Documento y relación de evidencia. | Core candidato | Puede iniciar como documento tipado y relación; evaluar identidad estable. | Alta |
| Rendición | MINVU distingue recursos correctamente rendidos y revisión de rendiciones pendientes. | No equivalente financiero específico confirmado. | Core candidato | Requiere modelar una relación, no un estado único del movimiento. | Alta |
| Auditoría / hallazgo | Informes CGR y medidas de seguimiento no son equivalentes a fallo penal. | Documento, hecho y fuente. | Core o proyección transversal | Probablemente relación entre informe, entidad y objeto fiscalizado. | Alta |
| Recuperación | Restitución ordenada no acredita cobro efectivo. | No equivalente confirmado. | Core candidato | Debe ser evento o relación independiente, con monto y fecha de corte. | Media |
| Investigación / procedimiento judicial | Fiscalía informa RUC, formalizaciones y audiencias; Pjud informa decisiones específicas. | Cronología, actores, documentos y hechos. | Core candidato | Evaluar identificadores externos y relaciones; no usar estado único de actor. | Alta |

### Regla de modelado propuesta

No usar un único `status` para el dinero. Como mínimo deben ser dimensiones
separables:

1. **Movimiento:** transferido, devuelto/reintegrado cuando se acredite,
   pendiente de restitución cuando una fuente lo indique.
2. **Rendición:** presentada, revisada, observada, aceptada o pendiente, sólo
   con la terminología de la autoridad correspondiente.
3. **Fiscalización:** auditado, con observación/hallazgo y con medida de
   seguimiento, sin equivalencia penal automática.
4. **Proceso:** bajo investigación, formalizado, acusado, resuelto o condenado,
   cada uno con causa, órgano, fecha y fuente.

Esto permite representar una transferencia ordinaria correctamente rendida y un
caso controvertido sin construir un “modelo de corrupción”.

## Prueba de generalización

El modelo candidato debe poder expresar sin juicios implícitos:

- una compra normal de ChileCompra;
- una transferencia pública correctamente rendida;
- una subvención aún en rendición;
- un gasto observado administrativamente sin proceso penal; y
- un proceso penal cuyo resultado aún no es definitivo.

Si una capacidad sólo sirve para una arista del Caso Convenios, debe permanecer
en su proyección o expediente hasta que otro corpus la justifique como Core.

## Fuentes para una futura dimensión transversal

| Fuente | Qué puede probar | Identificadores potenciales | Forma / automatización | Limitaciones | Prioridad |
| --- | --- | --- | --- | --- | --- |
| DIPRES | Reglas presupuestarias, programas y cambios normativos. | Partida, subtítulo, programa, año. | Documental; automatización media. | No acredita ejecución individual. | Alta |
| Organismo ejecutor / transparencia activa | Resoluciones, convenios, transferencias y liquidaciones. | Resolución, convenio, RUT, programa, región. | Mixta; automatización variable. | Fragmentación institucional y formatos heterogéneos. | Alta |
| Contraloría | Auditorías, observaciones, sumarios y seguimientos. | Informe, oficio, entidad fiscalizada, periodo. | Principalmente documental; automatización media. | Una observación no decide responsabilidad penal. | Alta |
| Registro de transferencias | Movimientos y destinatarios cuando el registro aplicable los publique. | Transferencia, entidad, periodo, programa. | Estructurada o mixta; por verificar. | Cobertura y semántica deben certificarse fuente por fuente. | Alta |
| ChileCompra / Mercado Público | Compras, órdenes y procesos de contratación. | Licitación, OC, proveedor, organismo. | Estructurada; alta. | No cubre todas las transferencias ni rendiciones. | Alta |
| Gobiernos Regionales, SUBDERE y ministerios | Convenios, programas y ejecución sectorial. | Acto, convenio, proyecto, región. | Mixta; media. | Heterogeneidad y publicación descentralizada. | Alta |
| Ministerio Público | Estado de investigaciones, audiencias y cifras de su propio universo. | RUC, causa, imputado, fecha. | Documental; media. | No es inventario de gasto ni prueba de condena. | Alta |
| Poder Judicial | Resoluciones, causas y resultados judiciales publicados. | Rol, tribunal, fecha. | Documental; media. | Cobertura pública y acceso dependen del expediente. | Alta |
| CDE | Querellas, acciones civiles y defensa patrimonial del Fisco. | Causa, querella, entidad. | Documental; media. | Una querella es una pretensión, no una condena. | Media |

## Diseño conceptual para una futura vista ciudadana

La futura pregunta “¿En qué se gastó mi dinero?” debe construirse sobre
trazabilidad verificable, no sobre una lista de acusaciones:

`Presupuesto → organismo → programa → instrumento → movimiento → destinatario → objeto → ejecución → rendición → fiscalización → hallazgo → investigación/proceso → resultado`.

### Confirmado desde el caso real

- Deben coexistir varias etapas y varios órganos para un mismo instrumento.
- Los importes necesitan tipo semántico, universo, fecha de corte y fuente.
- Rendición, fiscalización y proceso penal no deben colapsarse.

### Candidato

- Una proyección transversal que conecte movimientos con documentos,
  destinatarios, auditorías y procesos por identificadores trazables.

### No resuelto

- Identidad nacional estable de transferencias entre registros heterogéneos.
- Cobertura, API y licencia del registro de transferencias aplicable.
- Modelo mínimo de relaciones que reutilice DEO Core sin crear un esquema
  financiero paralelo.
- Umbral documental para calcular agregados comparables entre regiones y
  organismos.

## Corpus oficial revisado

- Ministerio Público, *Cuenta Pública 2025*, pp. 15–16 (corte abril 2025):
  https://www.fiscaliadechile.cl/sites/default/files/documentos/cuenta_publica_2025web.pdf
- Ministerio Público, formalización en arista Democracia Viva:
  https://www.fiscaliadechile.cl/actualidad/noticias/regionales/caso-convenios-equipo-de-la-fiscalia-formalizo-por-fraude-al-fisco
- Ministerio Público, competencia de aristas agrupadas (25-06-2026):
  https://www.fiscaliadechile.cl/actualidad/noticias/octavo-juzgado-de-garantia-de-santiago-se-declaro-incompetente-para-conocer
- MINVU, término y liquidación administrativa de tres convenios (14-07-2023):
  https://www.minvu.gob.cl/noticia/minvu-pone-fin-a-los-contratos-con-democracia-viva-y-fundacion-debera-restituir-los-dineros-otorgados-por-la-cartera/
- Poder Judicial, Rol 6.594-2023:
  https://www.pjud.cl/prensa-y-comunicaciones/noticias-del-poder-judicial/98661
- MINVU, referencia a Informes Finales CGR N° 465-1/2023 y 465-3/2024:
  https://documentos.minvu.cl/bitstreams/17200d15-884d-45dd-9847-f42edb37d3aa/download
- CDE, análisis institucional en al menos nueve regiones (11-07-2023):
  https://www.cde.cl/consejo-de-defensa-del-estado-analiza-antecedentes-en-al-menos-nueve-regiones-del-pais-por-caso-fundaciones/
- DIPRES, contexto de reglas presupuestarias de gobiernos regionales:
  https://www.dipres.gob.cl/598/w3-article-314955.html

## Próximo paso verificable

`ACQUIRE_DEMOCRACIA_VIVA_ANTOFAGASTA_PRIMARY_CORPUS`: adquirir de forma
reproducible los tres convenios, las resoluciones de término/liquidación, los
informes CGR completos, las actuaciones CDE aplicables y resoluciones judiciales
publicables. Sólo con ese corpus debe evaluarse un primer expediente real.

## Resultado de adquisición inicial — 25 de agosto de 2026

Se adquirieron al staging local catorce recursos oficiales de MINVU, Ministerio
Público y Poder Judicial, con SHA-256, URL, fecha de recuperación y una
representación normalizada cuando el formato lo permitió. El manifiesto local
ignorado de adquisición está en
`data/tmp/caso_convenios_democracia_viva_20260825/manifest.json`.

La adquisición confirmó la existencia de los instrumentos MINVU identificados
como Resoluciones Exentas N° 504/2022, 576/2022 y 641/2022, además de la
Resolución SERVIU N° 1621/2022. También se localizó y adquirió el Informe Final
de Avance de Investigación Especial N° 465-1/2023 en el repositorio oficial
MINVU, donde consta que su origen es Contraloría General de la República.

No se encontró una versión oficial equivalente con texto seleccionable de los
cinco PDFs inicialmente clasificados `OCR_REQUIRED` ni del Informe N°465-1. Los
tres PDFs de resoluciones SEREMI, la resolución ministerial posterior, la
resolución de transparencia y el Informe N°465-1 son PDFs escaneados sin capa
de texto utilizable por el extractor local disponible. Están preservados y
hasheados con su número de páginas, pero se clasifican como `OCR_REQUIRED`; no
se usan para extraer montos, obligaciones ni hechos persistibles.

El entorno local no cuenta con un motor OCR reutilizable (Tesseract ni un motor
Python equivalente). Por ello no se generó una transcripción OCR ad-hoc ni se
usó OCR de buscadores como autoridad. Esta es una limitación de procesamiento,
no una ausencia del documento oficial.

Se adquirió el seguimiento de Contraloría al Informe de Investigación
Especial N° 465/2023, emitido el 30 de mayo de 2025 y alojado por MINVU. Su
texto completo permite acreditar que Contraloría mantuvo separadas sus
observaciones sobre transferencias, controles y planes de trabajo. No reemplaza
el Informe Final N° 465-1/2023 ni convierte sus observaciones en una conclusión
penal.

Por tanto, el resultado sigue siendo **no materializar todavía**:

- El total de $426.000.000 y la restitución administrativa ordenada de
  $391.768.516 permanecen respaldados por la comunicación oficial MINVU, con
  su fecha de corte de 14 de julio de 2023.
- No se atribuyen aún montos individuales a los tres convenios desde los PDFs
  escaneados.
- No se adquirieron las rendiciones individuales: el acto administrativo de
  transparencia disponible documenta la solicitud y su denegación en el
  contexto investigativo, no el contenido de las rendiciones.
- Las resoluciones de término, liquidación y recursos, los Informes CGR en
  formato extraíble, las rendiciones y las actuaciones judiciales de fondo
  siguen siendo corpus pendiente para una reconstrucción materializable.

## OCR de corpus primario: verificaciones posteriores

El 26 de agosto de 2026 se completó la extracción OCR local por página de los
seis PDFs escaneados del corpus. El OCR conserva texto bruto, imagen de página,
configuración y SHA-256 del PDF oficial; no constituye una fuente independiente.
Los candidatos materiales fueron contrastados visualmente con las páginas
originales antes de clasificarse como verificados.

### Confirmado desde el caso real

- Los tres instrumentos son las Resoluciones Exentas N° 504 (3 de octubre de
  2022), N° 576 (27 de octubre de 2022) y N° 641 (29 de noviembre de 2022).
  Sus montos verificados son, respectivamente, $200.000.000, $170.000.000 y
  $56.000.000. Su suma coincide con el universo de $426.000.000 que CGR
  identifica para tres convenios de Fundación Democracia Viva.
- La Resolución N° 504 refiere habitabilidad primaria en el campamento
  Ecuachilepe; la N° 576, habitabilidad primaria en Irarrázabal Etapa I; y la
  N° 641, diagnósticos socio-territoriales, planes de intervención y acciones
  sociales y comunitarias. Las tres identifican a SEREMI MINVU y SERVIU de
  Antofagasta, junto con Fundación Democracia Viva.
- La N° 641 fija catorce meses (doce de ejecución y dos de cierre
  administrativo) y contempla la devolución de dineros no rendidos cuando
  corresponda. Es una regla del convenio, no prueba de recuperación.
- La Resolución DIJUR N° 1302, de 4 de agosto de 2023, resolvió un recurso
  administrativo relativo a la liquidación del convenio N° 641 y menciona una
  solicitud de reintegro de $52.574.302. Ese monto es una solicitud/orden de
  restitución en ese acto; el corpus no acredita un pago efectivo.
- La Resolución Exenta N° 387, de 25 de agosto de 2023, documenta una
  decisión de acceso a información vinculada con rendiciones solicitadas. No es
  una rendición y no permite reconstruir sus documentos individuales.
- El Informe Final CGR N° 465-1/2023 auditó traspasos de SEREMI MINVU
  Antofagasta a entidades privadas en el Programa de Asentamientos Precarios,
  entre el 1 de enero de 2020 y el 30 de junio de 2023, además de la
  participación de SERVIU. Para los tres convenios con Democracia Viva registró
  ausencia de fundamentos documentados para la designación y deficiencias para
  asociar fondos, prestaciones, tiempos y costos. También mantuvo una
  observación sobre el control de rendiciones mediante planillas y la ausencia
  de información consolidada.
- La tabla de CGR, con corte al 30 de junio de 2023, informa para Democracia
  Viva: $426.000.000 transferidos, $116.963.639 rendidos, $12.146.280 aprobados
  por la SEREMI y $309.036.361 por rendir. Es un estado de rendición a esa
  fecha, no una cifra de recuperación, pérdida definitiva ni responsabilidad
  penal.

### Capacidades refinadas

- **Convenio y acto administrativo** deben permanecer distinguibles: un
  convenio puede ser aprobado, terminado o liquidado por actos diferentes.
- **Rendición** requiere identidad documental propia y fecha de corte; una
  tabla de auditoría o una resolución de transparencia no la sustituye.
- **Recuperación** debe separar orden o solicitud de restitución de pago
  acreditado. El corpus conserva $391.768.516 como total administrativo
  ordenado y `UNKNOWN` para el total efectivamente recuperado.
- Un movimiento puede estar relacionado con varios documentos (convenio, acto
  aprobatorio, transferencia, rendición, auditoría y liquidación), sin que ello
  permita convertir esos estados en uno solo.

### No resuelto

- Documentos individuales de rendición y evidencia oficial de pago/reintegro.
- Asignación documental de los restantes $339.194.214 del total administrativo
  ordenado a los convenios N° 504 y N° 576. No se distribuye por cálculo.
- Resolución penal de fondo: el corpus no certifica una condena penal.

## Materializacion ciudadana v1: representacion con Core existente

### Confirmado desde el caso real

- El expediente ciudadano de esta arista puede expresar los tres convenios,
  sus actos aprobatorios, montos, objeto, estado de rendicion al corte de CGR,
  hallazgos administrativos, ordenes de restitucion y estado penal como
  hechos, limitaciones, cronologia, documentos y fuentes del contrato de
  expediente existente.
- Esa proyeccion conserva las separaciones necesarias: transferencia no es
  sustraccion; rendido no es aprobado; por rendir no es dinero robado; orden
  de restitucion no es recuperacion; y formalizacion o hallazgo de CGR no son
  condena penal.

### Candidate

- Una futura capa transversal de trazabilidad puede dar identidad propia a
  convenio, acto administrativo, movimiento, rendicion, hallazgo y accion de
  recuperacion. La evidencia de este caso demuestra la utilidad de esas
  distinciones, pero no exige una nueva tabla o esquema para este expediente.

### No resuelto

- El Core actual no ofrece aun una visualizacion transversal de flujos de
  dinero; ese limite no impide una proyeccion ciudadana honesta por expediente.
  La eventual vista "En que se gasto mi dinero" debe basarse en mas casos y no
  en una inferencia a partir de esta arista.

## OCR local: primer documento verificado

El 26 de agosto de 2026 se procesó localmente la Resolución Exenta N°504/2022
original de SEREMI MINVU Antofagasta. El archivo original permanece preservado
con SHA-256 `0e04e15e99d67d500bdb1320b9b8bf09931468fc21b019fea625ec55243b6b8a`;
la extracción se guarda por página en staging y no es una fuente independiente.

La revisión visual de las páginas 1 y 3 permite confirmar, para posteriores
candidatos de evidencia: Resolución Exenta N°504 de 3 de octubre de 2022; el
convenio suscrito el 20 de septiembre de 2022 entre SEREMI MINVU, SERVIU
Antofagasta y Fundación Democracia Viva; su objeto de habitabilidad primaria en
el campamento Ecuachilepe; y una disponibilidad presupuestaria de $200.000.000.
Esto no acredita por sí solo una transferencia efectivamente pagada, una
rendición, restitución, recuperación ni responsabilidad administrativa o penal.

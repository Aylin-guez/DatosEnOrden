# Real Data Audit

Auditoria local del proyecto para preparar la transicion desde demos hacia datos publicos descargables. No se revisaron APIs externas en ejecucion y no se propone scraping.

## Resumen

El proyecto ya tiene dos niveles de ingestion:

- ETL mas maduro: ChileCompra, con cliente, normalizador, mapper, pipeline y `GraphLoader`.
- Prototipos por fuente: loaders de samples para Lobby, DIPRES, Transparencia Activa, Diario Oficial, Registro Empresas, Contraloria, SERVEL, Municipalidades, Declaraciones de Intereses y Sanciones/Procedimientos.

El schema actual ya soporta el flujo base:

```text
source -> dataset -> import_job -> source_record -> claim -> evidence -> relationship_public -> expediente
```

## Inventario

| Fuente | Estado | Entrada esperada | Loader | Prioridad | Dificultad |
| --- | --- | --- | --- | --- | --- |
| ChileCompra | Conectado por archivo local y ETL existente | JSON compatible con ChileCompra, objeto con `Listado` o lista de ordenes | `scripts/load_chilecompra_file.py`, `scripts/run_chilecompra_etl.py` | Alta | Media |
| Lobby | Prototipo con sample | JSON local normalizado de reuniones | `scripts/load_lobby_sample.py` | Media | Media |
| DIPRES | Prototipo con sample | JSON local normalizado de presupuesto | `scripts/load_dipres_sample.py` | Media | Media |
| Transparencia Activa | Prototipo con sample | JSON local normalizado de cargos/roles | `scripts/load_transparencia_sample.py` | Media | Alta |
| Diario Oficial | Prototipo con sample | JSON local normalizado de publicaciones | `scripts/load_diario_oficial_sample.py` | Media | Alta |
| Registro Empresas | Prototipo con sample | JSON local normalizado de empresas/personas | `scripts/load_registro_empresas_sample.py` | Baja | Alta |
| Contraloria | Prototipo con sample | JSON local normalizado de informes/observaciones | `scripts/load_contraloria_sample.py` | Media | Alta |
| SERVEL | Prototipo con sample | JSON local normalizado de autoridades | `scripts/load_servel_sample.py` | Baja | Media |
| Municipalidades | Prototipo con sample | JSON local normalizado de proyectos/gasto | `scripts/load_municipalidades_sample.py` | Baja | Media |

## Que ya funciona

- Persistencia comun con `GraphLoader`.
- Exploracion por dataset, entidad, relaciones, timeline y evidencia.
- Entity Resolution como capa previa al expediente.
- Busqueda parcial y normalizada.
- Timeline derivada desde claims/source records.
- ChileCompra desde archivo local usando pipeline comun.

## Que quedo a medias

- La mayoria de fuentes fuera de ChileCompra son prototipos de sample, no loaders de datasets descargables reales.
- No hay scheduler ni ejecucion incremental.
- `last_loaded` se deriva desde base o queda como placeholder operativo.
- No existe separacion visual completa entre “Datos Publicos” y “Demo” en todos los flujos.
- No hay validadores por formato real de cada institucion, solo validacion local minima.

## Dataset necesario por fuente

- ChileCompra: export JSON/CSV convertido a payload compatible, con ordenes de compra, comprador, proveedor, fechas y montos.
- Lobby: dataset descargable de audiencias/reuniones con organismo, contraparte, materia y fecha.
- DIPRES: dataset presupuestario descargable con organismo, programa, ano, monto y clasificacion.
- Transparencia Activa: dataset descargable de cargos/roles con titular, organismo, unidad, fecha o periodo.
- Diario Oficial: metadata descargable de publicaciones; PDF original solo como referencia futura, no almacenamiento pesado.
- Registro Empresas: fuente descargable verificable antes de avanzar.

## Primer objetivo real recomendado

ChileCompra es la fuente mas madura porque ya tiene contratos ETL, normalizador, mapper y loader de archivo. Para declararla lista con datos reales falta:

- Definir fuente descargable concreta y formato operativo.
- Probar un archivo real reducido en entorno local.
- Validar conteos, rechazos y errores.
- Documentar atribucion y fecha de recuperacion.
- Confirmar que expedientes reales abren sin depender del demo.

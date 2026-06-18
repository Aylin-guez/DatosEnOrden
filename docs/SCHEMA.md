# DatosEnOrden - Schema v0.1

## Filosofía

DatosEnOrden se construye sobre un modelo de grafo respaldado por PostgreSQL.

Todo elemento relevante es una entidad.

Toda conexión entre entidades es una relación.

Toda relación debe tener evidencia verificable.

---

# Entidades

Representan objetos del mundo real.

Ejemplos:

* Persona
* Empresa
* Organismo Público
* Contrato
* Licitación
* Partido Político
* Elección
* Ley
* Votación
* Promesa
* Dataset

---

## entity

Tabla principal.

```sql
entity
```

Campos:

```text
id UUID PK

entity_type TEXT

name TEXT

description TEXT

external_id TEXT

status TEXT

created_at TIMESTAMP

updated_at TIMESTAMP
```

Ejemplos:

```text
PERSON

COMPANY

PUBLIC_ORGANIZATION

POLITICAL_PARTY

CONTRACT

TENDER

LAW

VOTE

PROMISE

DATASET
```

---

# Relaciones

Representan conexiones entre entidades.

---

## relationship

```sql
relationship
```

Campos:

```text
id UUID PK

source_entity_id UUID

target_entity_id UUID

relationship_type TEXT

start_date DATE

end_date DATE

notes TEXT

created_at TIMESTAMP
```

Ejemplos:

```text
REPRESENTS

OWNS

RECEIVES_CONTRACT

AWARDS_CONTRACT

MEMBER_OF

VOTED_FOR

PARTICIPATES_IN

FUNDED_BY

RELATED_TO
```

---

# Fuentes

Toda información debe tener origen.

---

## source

```sql
source
```

Campos:

```text
id UUID PK

name TEXT

publisher TEXT

url TEXT

license TEXT

retrieved_at TIMESTAMP

created_at TIMESTAMP
```

Ejemplos:

```text
ChileCompra

SERVEL

DIPRES

Portal Transparencia

INE

Banco Central
```

---

# Evidencia

Conecta relaciones con fuentes.

---

## evidence

```sql
evidence
```

Campos:

```text
id UUID PK

relationship_id UUID

source_id UUID

title TEXT

url TEXT

published_at DATE

excerpt TEXT

created_at TIMESTAMP
```

Ejemplo:

Empresa X

RECIBE_CONTRATO

Ministerio Y

Evidencia:

* Licitación pública
* URL oficial
* Fecha
* Fuente ChileCompra

---

# Datasets

Permite rastrear origen de cargas masivas.

---

## dataset

```sql
dataset
```

Campos:

```text
id UUID PK

name TEXT

description TEXT

source_id UUID

version TEXT

dataset_url TEXT

loaded_at TIMESTAMP
```

---

# Importaciones

Historial ETL.

---

## import_job

```sql
import_job
```

Campos:

```text
id UUID PK

dataset_id UUID

started_at TIMESTAMP

finished_at TIMESTAMP

status TEXT

records_processed INTEGER

error_log TEXT
```

---

# Versionado

Permite trazabilidad futura.

---

## change_log

```sql
change_log
```

Campos:

```text
id UUID PK

entity_name TEXT

entity_id UUID

action TEXT

previous_value JSONB

new_value JSONB

changed_at TIMESTAMP
```

---

# Futuro

Estas tablas NO se implementan inicialmente.

---

## political_promise

Promesas electorales.

---

## claim

Declaraciones públicas.

---

## fact_check

Verificación basada en evidencia.

---

## user_annotation

Observaciones ciudadanas moderadas.

---

# Regla Principal

Sin evidencia:

NO EXISTE.

Sin fuente:

NO EXISTE.

Sin trazabilidad:

NO ENTRA A LA BASE.

```
```

# DatosEnOrden - Information Policy

> El codigo construye el sistema. La documentacion conserva la memoria.

Este documento define como separar conocimiento publico, interno, confidencial y personal dentro del proyecto DatosEnOrden.

## Objetivo

Mantener el repositorio abierto sin publicar:

- ideas de negocio
- estrategia futura
- investigacion competitiva
- prompts internos
- experimentos no validados
- notas personales
- material para inversionistas

El repositorio publico debe conservar lo que ayuda a entender, auditar y extender el sistema:

- codigo
- arquitectura
- esquema tecnico
- documentacion tecnica
- metodologia
- decisiones tecnicas
- vision publica del proyecto

## Categorias

### PUBLIC

Informacion destinada a GitHub y a lectores externos.

Incluye:

- codigo fuente
- migraciones
- schemas y contratos tecnicos
- arquitectura
- ADRs
- changelog
- vision
- roadmap publico
- politica legal y etica minima
- fuentes publicas y su atribucion
- documentacion de ETLs ya validada para publicacion

Regla:

- Si ayuda a reproducir o entender el sistema sin exponer estrategia sensible, puede ser publica.

### INTERNAL

Informacion de trabajo del equipo que puede compartirse dentro del proyecto, pero no necesariamente en la portada del repositorio.

Incluye:

- notas tecnicas de implementacion
- revisiones de schema
- roadmaps operativos
- borradores de decisiones
- guias de trabajo interno
- pruebas de concepto ya validadas pero no pulidas

Regla:

- Puede vivir en el repositorio solo si no expone estrategia sensible o datos privados.
- Si su valor principal es organizativo y no documental, debe moverse a `private/`.

### CONFIDENTIAL

Informacion estrategica que no debe subirse a GitHub.

Incluye:

- planes de negocio
- ideas comerciales no publicas
- notas para inversionistas
- analisis competitivo
- pricing
- asociaciones o alianzas no anunciadas
- prompts internos de IA
- experimentos no validados
- estrategias de producto futuras

Regla:

- Nunca debe publicarse en el repositorio abierto.
- Debe almacenarse solo en `private/` o en un canal equivalente controlado.

### PERSONAL

Informacion estrictamente personal y no necesaria para el proyecto publico.

Incluye:

- notas personales
- recordatorios privados
- contexto laboral no destinado al proyecto
- material sensible de uso individual

Regla:

- No debe mezclarse con documentacion del proyecto.
- Si se conserva, debe vivir solo en `private/personal_notes/`.

## Estructura recomendada

### Publico

```text
README.md
ROADMAP.md
VISION.md
SCHEMA.md
ARCHITECTURE.md
DECISIONS.md
CHANGELOG.md
LEGAL_ETHICS.md
SOURCES.md
docs/
src/
tests/
database/
alembic/
```

### Privado local

```text
private/
  prompts/
  business/
  investor_notes/
  experiments/
  future_ideas/
  market_research/
  personal_notes/
```

## Inventario actual del repositorio

### Permanecer publico

Estos archivos son compatibles con una publicacion abierta y documentan la base tecnica del proyecto:

- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/CHANGELOG.md`
- `docs/DECISIONS.md`
- `docs/LEGAL_ETHICS.md`
- `docs/ROADMAP.md`
- `docs/SCHEMA.md`
- `docs/SOURCES.md`
- `docs/VISION.md`
- `docs/etl/CHILECOMPRA.md`
- `docs/adr/0001-postgresql-sqlalchemy-alembic.md`
- `docs/adr/0002-etl-contracts-before-source-specific-logic.md`
- `docs/DEVELOPMENT.md`

### Mantener privado

Estos archivos contienen trabajo interno, borradores o material estrategico que no deberia ir a GitHub:

- `docs/IDEAS.md`
- `docs/SCHEMA_REVIEW.md`
- `docs/TECHNICAL_ROADMAP.md`

### Dividir entre publico y privado

Estos documentos pueden tener una version publica resumida y una version privada con detalle estrategico:

- `docs/ROADMAP.md`
- `docs/DECISIONS.md`
- `docs/SCHEMA.md`
- `docs/ARCHITECTURE.md`
- `README.md`

## Regla de clasificacion

Clasifica cada archivo o nota segun la informacion mas sensible que contenga.

Si un documento mezcla categorias, usa esta prioridad:

1. PERSONAL
2. CONFIDENTIAL
3. INTERNAL
4. PUBLIC

Esto significa:

- si un archivo tiene aunque sea una seccion confidencial, no debe publicarse completo
- si un documento puede dividirse, publica solo la parte tecnica y mueve el resto a `private/`
- si una nota no ayuda a reproducir, auditar o entender el sistema, no pertenece al repositorio publico

## Politica operativa

- No crear prompts internos dentro de `docs/`.
- No guardar ideas de negocio en archivos publicos.
- No mezclar experimentos personales con documentacion tecnica.
- No publicar material de inversionistas.
- No publicar research competitivo.
- No tratar borradores como documentacion oficial.

## Criterio practico

Preguntate lo siguiente antes de guardar algo en el repo publico:

1. ¿Ayuda a entender o reproducir el sistema?
2. ¿Expone estrategia, negocio o material sensible?
3. ¿Se puede resumir sin perder valor tecnico?

Si la respuesta a 2 es si, o a 1 es no, va a `private/`.

## Nota sobre este cambio

Este documento no elimina informacion. Solo fija un limite claro entre memoria publica y trabajo interno.

# DatosEnOrden UX Guidelines

## Purpose

DatosEnOrden should read first as a civic explanation tool, not as a database browser. The interface can expose technical traceability, but the main view should help a citizen understand what public records say and what they do not say.

## Citizen-first principles

- Start with meaning: explain what appears in the records before showing tables, IDs, predicates, or URLs.
- Keep entity pages centered on one question: what public information is available for this entity?
- Use compact metrics for orientation: datasets involved, evidence count, connected entities, and relationship count.
- Present timelines as a sequence of public records, not as internal claim events.
- Prefer short cards with source, date or period, plain explanation, and evidence count.

## Neutral language rules

- Use descriptive wording: "aparece asociado", "se registro", "fuente cargada", "evidencia disponible".
- Do not imply crimes, irregularities, intent, influence, corruption, risk, or guilt.
- Always distinguish records from conclusions.
- Include a neutral caution when showing multi-source connections: connections do not imply causality or wrongdoing.
- For local samples, keep the sample status visible in documentation and avoid presenting sample records as official data.

## Explanation guidelines

- Relationship explanations should translate internal types into plain Spanish.
- Good: "El organismo aparece asociado a un informe de control."
- Good: "Se registro la ejecucion de un proyecto."
- Avoid exposing raw labels like `ORGANIZATION_HAS_CONTROL_REPORT` in the main investigation flow.
- If the source is unknown or generic, say "fuente publica" rather than inventing a specific source.

## Technical information separation

Keep these fields out of the primary story cards:

- entity IDs
- source record IDs
- claim IDs
- relationship IDs
- dataset keys
- raw URLs
- internal predicates
- internal relationship types

Show them only in a "Detalles tecnicos" section for traceability and developer review.

## Search results

Search should show:

- entity name
- human entity type
- short explanation
- count of claims and relationships
- dataset hints when available

Search should not use raw identifiers as the main visible result content.

## Investigation page structure

Recommended order:

1. Entity name and narrative summary.
2. Dataset badges.
3. Compact metrics.
4. Investigation timeline or story flow.
5. Source-specific cards.
6. Relationship cards.
7. Evidence cards.
8. Context and caution.
9. Detalles tecnicos.

## Review checklist

- Can a non-technical reader explain why the entity is shown?
- Are internal IDs hidden from the main narrative?
- Are all claims phrased neutrally?
- Is evidence available for verification?
- Are sample/demo records clearly separated from official records?

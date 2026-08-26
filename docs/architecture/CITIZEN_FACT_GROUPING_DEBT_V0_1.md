# Citizen fact grouping — recorded UX debt

## Observation

Some citizen expedients contain many independently supported facts. Rendering each
fact as an equal-weight card preserves provenance, but can make the reader rebuild
the conceptual structure alone.

The Human QA of **Control preventivo de identidad** identified useful candidate
groups: who and when a person may be controlled; how identity can be established;
the specific vehicle-related register rule; what the rule does not establish by
itself; and what happens when identity cannot be verified in place.

## Intended capability

`CitizenExpedientProjection` may later support optional, semantic fact groups.
Each group would remain a projection of the same immutable statements and their
existing evidence. It must not discard, merge, or weaken individual provenance.

## Reuse test

The pattern appears potentially useful for Ciberseguridad, Protección de Datos,
Democracia Viva and longer legislative expedients. It has not yet been shown to be
needed in enough distinct structures to justify a new schema or a renderer-specific
abstraction.

## Decision

Recorded only. No schema change, new Core entity, expedient revision, or
expedient-specific UI branch is authorized by this note.

# Public REAL Expedient Contract V0.1

Classification: **PUBLIC**

## Decision

REAL expedients use the existing PostgreSQL application persistence boundary. They are immutable, versioned investigation structures that reference authoritative graph content; they do not copy claim, evidence, relationship, entity, document, or source payloads.

The original schema had no expedient tables. Revision `202608120001` now implements the additive schema and a PostgreSQL repository adapter. It has been exercised only against isolated temporary PostgreSQL databases; applying it to the persistent content database remains a separate authorization gate.

## Existing architecture and gap

`application/laboratory` exposes one hard-coded in-memory DEMO (`EXP-001`) through list/get functions used by the Reflex laboratory state. The application already has PostgreSQL repositories and persisted sources, source records, claims, evidences, entities, relationships, import jobs, and change logs. Provenance authority and public sanitizers also already exist.

Missing pieces are: a persisted expedient aggregate, immutable versions, structured reference associations, a PostgreSQL repository adapter, idempotent provisioning, provenance eligibility lookup for every reference, and a transition reader that combines persisted expedients with the temporary DEMO provider.

## Domain contract

Required per version:

- `expedient_id`, stable across versions;
- `title`, `question`, and a concise `summary`;
- explicit `provenance_class` (`REAL`, `DEMO`, `TEST`, or `UNKNOWN`);
- lifecycle `status` (`draft`, `published`, or `withdrawn`);
- positive `version`;
- at least one claim, evidence, and source reference for a REAL expedient;
- `created_at` and `updated_at`, assigned by persistence.

Optional structured references are relationships, entities, documents, and additional sources. Optional narrative statements carry a stable statement ID, section, text, epistemic class, and claim/evidence support references.

Derived values include public counts, navigation projections, `what_we_know`, `how_we_know`, `what_is_missing`, `what_could_change`, open questions, and timelines. Derived text is navigation/editorial structure, never the authoritative source of a fact. Every `FACT` or `SUPPORTED_INFERENCE` statement must link to a claim or evidence included in the same version.

## Provenance and lifecycle

Provenance and lifecycle remain separate. Missing provenance never means REAL. A REAL version is accepted only when every referenced item is independently classified REAL and publicly usable. DEMO, TEST, UNKNOWN, mixed provenance, and rejected-only support fail closed.

Only `published` versions are public. `draft` is authoring-only. `withdrawn` preserves history but is not a normal public result. More states should be added only after a demonstrated workflow requires them.

## PostgreSQL schema

The migration adds:

1. `real_expedient`: stable ID, explicit provenance, current version and timestamps.
2. `real_expedient_version`: immutable title, question, summary, lifecycle and fingerprint.
3. `real_expedient_reference`: typed logical IDs for claim, evidence, relationship, entity, document and source.
4. `real_expedient_narrative`: ordered structured statements and epistemic classification.
5. `real_expedient_narrative_support`: claim/evidence support links for each statement.

References use logical stable IDs. A polymorphic database foreign key cannot target all authoritative tables, and official documents are currently catalog artifacts rather than first-class database rows. The application provenance authority validates every reference before insert; database constraints restrict type vocabulary, ownership and uniqueness.

Indexes should cover `(provenance_class, current_version)`, public status on current versions, and reverse lookup by each referenced ID. Check constraints should enforce the provenance and lifecycle vocabularies and positive versions. Unique keys make reference insertion deterministic and duplicate-free.

No JSON payload should duplicate graph content. No SQLite or file-backed parallel store is permitted.

## Idempotency, conflicts, and versioning

Provisioning computes a canonical content fingerprint after validation. `create_if_absent` inserts version 1 only when the ID is absent. Repeating an identical request returns the stored version without writing. The same ID with a different fingerprint is an explicit conflict.

Revisions use optimistic version matching and append exactly `current_version + 1`. Previous version rows and their references remain immutable. No revision silently overwrites prior narrative or associations. A transaction must insert the version, statements, references, and updated current-version pointer atomically.

## Public projection and security

The browser DTO contains only the public ID, title, question, summary, provenance label, lifecycle, version, sanitized structured statements, sanitized reference IDs, and public timestamps. Navigation resolves those IDs through application services; the UI never queries the database directly.

The projection excludes fingerprints, SQL details, filesystem paths, raw metadata, operator notes, debug/session values, private provenance internals, and test fields. Official URLs continue to come only from validated REAL source/document metadata and are never fabricated from identifiers.

## EXP-001 transition

The composed application reader queries persisted expedients first, then falls back only for the exact legacy ID `EXP-001`. EXP-001 remains DEMO and is not duplicated in PostgreSQL. After the adapter is deployed and certified, a separately authorized process may migrate EXP-001 as DEMO and remove the hardcode; dual implementations are transitional, not permanent.

## Remaining implementation gate

- authorize and back up the persistent content database;
- run migration prechecks and apply revision `202608120001`;
- verify the new tables are empty and the existing content baseline is unchanged;
- wire the existing provenance authority into the eligibility port for the provisioning command;
- adapt the existing public laboratory state to the composed reader without direct database access;
- integrate metrics through provenance authority when the first REAL expediente is provisioned.

Before execution, review migration downgrade behavior, take a database backup, run on an isolated copy, and prepare repository/integration tests. No REAL content should be provisioned until these gates pass.

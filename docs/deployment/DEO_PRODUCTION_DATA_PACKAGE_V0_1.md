# DEO Production Data Package V0.1

Status: public contract. The package contains only public data state and no credentials or
private operational instructions.

## Purpose and boundary

`DEO_PRODUCTION_DATA_PACKAGE_V0_1` is the independent release contract for authorized REAL
content. A code release and a data release are separate artifacts. Compatibility is explicit in
the manifest; changing only data does not require rebuilding the application artifact.

V0.1 is an additive snapshot format. It is designed so a later contract can add delta operations
without changing the canonical row representation, package lineage, or conflict rules.

## Authority and selection

The exporter calls the existing T1 provenance authority. It does not classify records itself.
Only `build_public_usable_content` may select database graph content. Eligibility is:

- exact dataset identity classified `REAL` by the canonical provenance manifest;
- source-record lifecycle `normalized`, `validated`, or `published`;
- claims and relationships with a public-usable lifecycle and REAL dependency closure;
- evidences and entities reachable from that public-usable closure;
- REAL expedients whose current immutable version is `published` and whose references are all
  independently REAL and public usable.

REAL records with lifecycle `rejected` do not enter the package. DEMO, TEST and UNKNOWN fail
closed. `EXP-001` remains the explicit code-generated laboratory demo and is never transported by
the data package or counted in REAL metrics.

## Included tables and order

1. `source`
2. `dataset`
3. `source_record`
4. `entity`
5. `evidence` (initially with nullable `claim_id`)
6. `claim`
7. `relationship_public`
8. `real_expedient`
9. `real_expedient_version`
10. `real_expedient_reference`
11. `real_expedient_narrative`
12. `real_expedient_narrative_support`

The importer restores `evidence.claim_id` in a second pass. All work happens in one transaction
and constraints are forced before commit.

`alembic_version` is not imported as content. Its exact required value is a compatibility gate.
Schema is always created by Alembic before a package import.

## Excluded content

- `import_job`, `change_log`, retry/rate-limit state and staging state;
- source-record `error_log` and local `processed_at` history;
- DEMO, TEST, UNKNOWN and REAL rejected records;
- raw duplicate entity/evidence source snapshots;
- raw contact email, phone, address, contact-person and identifier fields;
- passwords, connection URLs, tokens, keys, user/session identifiers and personal paths.

Acquisition, event, publication, normalization and source creation timestamps remain distinct.
Package creation time lives in the manifest. Import time is emitted by the importer and never
rewrites source temporal fields.

## Archive and manifest

The archive is a deterministic ZIP layout:

```text
manifest.json
data/source.jsonl
data/dataset.jsonl
...
```

Every JSON object is canonical UTF-8 with sorted keys. Rows are sorted by declared primary key.
Each table entry declares path, primary key, dependencies, row count and SHA-256. The logical
content hash covers the contract, provenance policy, required schema and all table hashes. The
package ID is `DEO-PROD-DATA-NNNN-<logical-hash-prefix>`.

The manifest includes `PACKAGE_ID`, `CREATED_AT`, `SOURCE_DB_REVISION`,
`REQUIRED_SCHEMA_REVISION`, explicit code compatibility, classification, table manifest, row
counts, content hashes, dependencies, provenance policy, export tool version, temporal policy and
lineage. `created_at` is intentionally outside the logical hash.

## Export and verification

Export from the authorized local database configuration:

```powershell
.venv\Scripts\python.exe scripts/export_production_data.py --release-number 1
```

Future application releases are added explicitly with repeatable
`--compatible-code-release <40-HEX-SHA>`. The allowlist, not Git-hash ordering, is authoritative;
`min_code_release` and `max_code_release` record its declared endpoints.

The output is written under ignored `private/releases/data/`, with a `.sha256` sidecar. The
exporter refuses a wrong Alembic revision, an ineligible expedient reference, operational errors,
secret-like keys, Windows paths or residual email content.

Verification is mandatory before opening a target transaction. The importer checks the external
archive SHA-256, member safety, exact member set, canonical encoding, every content hash, every row
count, logical hash and package ID.

## Import safety

The CLI reads the database URL only from normal application configuration; it is not accepted as a
command-line argument. The operator must provide the exact target database name, target kind, code
release and archive SHA-256. Production additionally requires the package ID as confirmation:

`--code-release` identifies the application release that will consume the imported state, not the
working copy from which the operational importer happens to run.

```bash
python scripts/import_production_data.py \
  --package /secure-upload/<package>.zip \
  --sha256 <ARCHIVE_SHA256> \
  --expected-database datosenorden_beta \
  --target-environment production \
  --code-release <CODE_RELEASE> \
  --confirm-production <PACKAGE_ID>
```

The importer rejects administrative databases, an identity mismatch, wrong Alembic revision,
unsupported PostgreSQL major, non-explicit code compatibility, invalid confirmation or conflicting
content. Existing identical primary keys are no-ops. Existing different rows abort and roll back
the entire transaction. A successful run emits inserted/unchanged counts, target counts, public
metrics and an import timestamp.

## Rollback

V0.1 never deletes or overwrites content. For the first import into an otherwise empty target,
rollback is database recreation followed by Alembic migration. Future non-empty production must
take a verified logical backup before import. A data rollback must use an explicitly certified
inverse/superseding package or a database restore; application rollback does not imply data
rollback.

## Future DATA RELEASE 0002

The next release declares `base_package_id`, `supersedes` and either:

- another additive snapshot, whose identical rows remain no-ops; or
- a future versioned delta contract with explicit insert/update/tombstone operations.

Updates keep stable primary identities. Different content under an existing identity is a conflict
unless the future contract explicitly authorizes a version transition. Expedients append immutable
versions and advance `current_version` under an expected-version check. Source lifecycle changes,
withdrawals and deletions require explicit tombstones; absence from a package never means delete.

Autonomous production ingestion starts its own `import_job`, retry and rate-limit history. Local
ingestion history is never promoted.

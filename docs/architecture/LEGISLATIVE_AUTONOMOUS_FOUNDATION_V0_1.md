# Legislative Autonomous Foundation V0.1

## Scope and boundary

This public-product foundation is read-only. It registers official legislative sources, discovers only caller-supplied stable identities, acquires bounded artifacts, records a hash manifest, compares snapshots, and assesses candidates. It does not write PostgreSQL, extract claims, resolve entities, provision expedients, schedule work, or publish.

## Registry and traceability

`LEGISLATIVE_SOURCE_REGISTRY` declares Senate, Chamber and LeyChile official hosts, allowed resource types, identity schemes, limits and public-usability prerequisites. `OfficialResourceDescriptor` is a pre-validated resource identity. `AcquisitionManifest` records the URL, content type, byte count, SHA-256, retrieval time, HTTP status and method. A changed hash is a review signal, never a public fact.

Temporal fields are separate: an event date, effective date, acquisition time, and a legislative status. Supported statuses include proposal, discussion, chamber/congress approval, promulgation, publication, force, rejection and withdrawal. Their values are not interchangeable.

## How this enables autonomous DEO

```
SOURCE REGISTRY
  -> SCHEDULED DISCOVERY
  -> ACQUISITION
  -> CHANGE DETECTION
  -> IDENTITY RESOLUTION
  -> PROVENANCE
  -> FACT/EVENT EXTRACTION
  -> EXPEDIENT CANDIDATE ASSESSMENT
  -> REVIEW / POLICY GATE
  -> VERSIONED EXPEDIENT
  -> PUBLIC PROJECTION
  -> CHANGE FEED
  -> OPTIONAL SOCIAL DISTRIBUTION
```

Only the first four steps and a conservative candidate assessment are implemented here. A future scheduler can supply an explicit `DiscoveryQuery`, compare manifests, and emit a `ChangeEvent`. All changes remain `REVIEW_REQUIRED`; no automatic publication is enabled. A later social candidate may consume a human-approved meaningful or major change only after an expedient version and public projection exist.

## Public-safety rules

The client permits HTTPS to registered hosts only, validates redirected hosts, enforces a per-source timeout and byte cap, validates content type, hashes content, and stages by SHA-256. It rejects arbitrary URLs and does not expose staging paths or raw acquisition metadata to browser-facing code. REAL eligibility remains exclusively under the canonical provenance authority.

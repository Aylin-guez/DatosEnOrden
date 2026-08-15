# Legislative REAL Normalization Contract V0.1

An official legislative resource is REAL only when its host, canonical bulletin identity, acquisition manifest, artifact content and normalized field/event are all verified. HTTP success alone is not a fact.

The canonical matter identity is `cl-congreso-boletin-<bulletin>`. Senate and Chamber observations remain independent `SourceRecord` instances under that shared identity. A disagreement becomes `SOURCE_CONFLICT` and blocks automatic progression. Facts are only structured claims linked to an observation's evidence URL and artifact SHA-256.

Snapshots hash normalized matter identity, source artifact hashes, status and event keys. First observation is `BASELINE`; identical snapshots are `UNCHANGED`; new events are meaningful; approval, promulgation, publication, force or rejection are major. All changes remain review-required. This enables a future scheduler to reacquire a registered matter, compare snapshots, identify affected expedients and produce an update candidate without auto-publishing.

`EXP-REAL-LEGISLATIVE-15975-25` references the canonical `PUBLIC_PROJECT` entity `cl-congreso-boletin-15975-25`. A future lookup can therefore follow a bulletin's canonical entity reference to dependent expedients without matching titles or URLs.

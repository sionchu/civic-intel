# Batch Ingestion

## Purpose

Civic Intel must scale from reviewed single-pull feeder staging to source-bounded full
enumeration without weakening SourcePolicy, identity isolation or evidence provenance.

The canonical L3 collection path is:

```text
Official source universe
        ↓
Source-specific enumerator
        ↓
SourcePolicy
        ↓
Source
        ↓
SourceSnapshot
        ↓
FeederObservation
        ↓
Deterministic materialization gate
        ├── AUTO_CREATE
        ├── AUTO_LINK
        ├── REVIEW_REQUIRED
        └── HARD_CONFLICT
        ↓
Canonical Person
        ↓
Claim / ClaimEvidence
        ↓
verification/publication gate
```

The public-official-profiler is an optional deep-research consumer of canonical identity and
evidence. It is not the required ingestion path.

---

## Collection boundary

Full enumeration means:

> enumerate the complete bounded scope of one reviewed official API or structured disclosure.

It does not mean unrestricted crawling.

Allowed examples:

- every page in a reviewed National Assembly roster API;
- every page/date window in a reviewed official personnel API;
- every institution in a reviewed ALIO/CleanEye universe;
- every reviewed corporation code in a defined OpenDART public-governance scope.

Still prohibited:

- generic web spiders;
- search-result bulk ingestion;
- ordinary employee directories;
- ordinary union/member directories;
- broad personal contact harvesting.

---

## Maturity

Every feeder uses:

```text
L0 RESEARCHED
L1 CONTRACT_STAGED
L2 SINGLE_PULL
L3 FULL_ENUMERATION
L4 PRODUCTION_SYNC
```

### L0

Source and policy strategy researched.

### L1

Canonical/staging contract plus deterministic offline fixtures exist.

### L2

A reviewed live-capable source-specific connector can fetch a single page/entity.

### L3

The bounded source universe can be completely enumerated with:

- pagination/cursor coverage;
- coverage validation;
- persistent source runs;
- checkpoint/resume;
- idempotent observations;
- deterministic offline full-enumeration tests.

### L4

Adds operational synchronization:

- scheduled/incremental refresh;
- source freshness semantics;
- change/tombstone reconciliation;
- operational retries/monitoring.

L4 infrastructure is out of the first batch transition milestone.

---

## Source-level capture

`SourcePolicy`, `Source` and `SourceSnapshot` remain canonical.

`SourceSnapshot` is the source-level immutable capture.

It keeps:

- fetched time;
- content hash;
- allowed metadata;
- fulltext only when SourcePolicy explicitly permits it.

Do not create a second raw source archive.

---

## Record-level observation

A `FeederObservation` represents one normalized provider record within a SourceSnapshot.

Minimum semantics:

```text
feeder
scope_key
provider_record_key
snapshot_id
run_id
recorded_at
provider_observed_at?
semantic_scope
identity_hints
normalized
content_hash
```

Only SourcePolicy-permitted, public-interest fields may be stored.

### Version rule

```text
same provider key + same normalized hash
→ unchanged

same provider key + changed normalized hash
→ new immutable observation
```

Old observations are not overwritten.

---

## Source runs and checkpoints

`SourceRun` is the operational audit record.

Minimum states:

```text
RUNNING
SUCCESS
PARTIAL
FAILED
```

`SourceCheckpoint` stores the latest safely committed cursor for one:

```text
(feeder, scope_key)
```

Checkpoint advancement is transactional with persisted observations.

A run may be PARTIAL while retaining a valid resumable checkpoint.

Therefore a single `last_synced_at` field is not sufficient to describe ingestion state.

---

## Pagination safety

An L3 enumerator must fail closed on coverage ambiguity.

For page-based sources verify as available:

- starts at required first page;
- provider total count;
- page size;
- expected page count;
- page number response;
- total count stability;
- duplicate page content;
- duplicate/conflicting provider record keys;
- final unique record coverage.

Absence of complete coverage must not silently produce an "exact" roster.

---

## National Assembly reference

The National Assembly member source is the first L3 reference because it already has:

- reviewed SourcePolicy;
- live source-specific connector;
- provider identity `MONA_CD`;
- deterministic parser;
- privacy-minimized staging.

Full enumeration uses the member API without name/party/district filters.

`MONA_CD` is the provider record identity anchor.

The observation still stores a separate content hash so later roster changes create a new
immutable observation version.

Contact fields exposed by the provider are never persisted.

---

## Identity vs materialization

Civic Intel separates:

1. research identity evidence;
2. canonical materialization permission.

A research identity may be sufficiently supported for a reviewed profile target while still
being too ambiguous for automatic cross-Person merging.

### Materialization actions

Initial batch milestone:

```text
AUTO_CREATE
AUTO_LINK
REVIEW_REQUIRED
HARD_CONFLICT
```

No fuzzy AUTO_MERGE is required.

### AUTO_CREATE

An authoritative public roster with a stable unique provider key may create a new Person when
no same-name ambiguity or contradiction requires review.

### AUTO_LINK

A later observation with the exact already accepted provider identity may link to the existing
Person.

### REVIEW_REQUIRED

Same-name and cross-lane matches without an exact accepted provider identity remain review
items.

### HARD_CONFLICT

Exact contradictions fail closed.

---

## Numeric scores

Identity scores are not probabilities and cannot be canonical merge authority.

The canonical identity contracts contain no numeric score. They expose explicit deterministic
decision classes and reasons. Materialization uses its own action gate and must not reconstruct
a threshold from identity hints, evidence counts or similarity values.

---

## Materialization provenance

Canonical materialization should retain:

```text
Person
↑
PersonObservationLink
↑
FeederObservation
↑
SourceSnapshot
↑
Source
↑
SourcePolicy
```

Batch-derived ClaimEvidence should additionally be able to reference the exact
FeederObservation.

This does not replace Source/Snapshot evidence.

---

## Publication

Workers do not gain publication authority from L3 enumeration.

Safe path:

```text
observation
→ materialization decision
→ Person
→ DRAFT FACT
→ ClaimEvidence
→ existing validation gate
→ PUBLISHED only on success
```

Any failed identity, policy, reference or publication gate rolls back the coherent
materialization transaction.

---

## Reviewed/manual path

`ReviewedPersonBundle` remains valid for:

- deterministic regressions;
- manual overrides;
- exceptional reviewed onboarding;
- complex or contested cases.

It is not the required normal path for every feeder-discovered person.

---

## Persistence

Batch foundation adds only the minimum operational/record-level tables:

```text
source_runs
source_checkpoints
feeder_observations
```

The identity/materialization slice later adds:

```text
person_observation_links
identity_review_items
```

and may add:

```text
claim_evidence.feeder_observation_id
```

for exact provider-row provenance.

Do not introduce a second source archive or a generic event-sourcing platform.

---

## Runtime boundary

SQLite remains sufficient for deterministic development/integration tests.

Schema choices should remain PostgreSQL compatible.

Alembic is the only schema change path.

Runtime startup verifies the schema head and never calls `create_all()` or silently migrates.

---

## Infrastructure deferral

L3 does not justify:

- Temporal;
- Airflow;
- Celery;
- Kafka;
- Kubernetes;
- Splink;
- vector databases;
- graph databases;
- MCP.

These may be evaluated after real L3 workloads demonstrate a need.

---

## Concrete L3 feeder proofs

Gwanbo personnel notices are the second concrete L3 feeder. They reuse the canonical
SourcePolicy/Source/Snapshot/Observation/Run/Checkpoint persistence while keeping a separate
source-specific HTML POST connector and parser.

The Gwanbo policy is metadata-only because its current official Open API page does not state a
reuse license. Notice titles are not treated as structured person or career fields.

The NEC local-winner source is the third L3 feeder. It uses the same persistence transaction
without extracting a generic page-runner framework. Its bounded universe is one unfiltered
`(sgId, sgTypecode)` scope and its exact provider row key is `huboid`.

National Assembly bill participation is the fourth L3 feeder. Its bounded universe is one
unfiltered Assembly `AGE`, its provider row key is `BILL_ID`, and every row must expose complete
parseable `RST_MONA_CD`/`PUBL_MONA_CD` fields. Observations are multi-person legislative events;
they do not create Persons or turn participation into a performance/faction claim.

The NEC local-candidate source is the fifth L3 feeder. Its bounded universe is one unfiltered
`(sgId, sgTypecode)` scope and its provider row key is `huboid`. It stores privacy-minimized
candidate-registration observations with candidate-submitted disclosure semantics and no winner
inference or Person creation.

ALIO public-institution executives are the sixth L3 feeder. The bounded universe is the
unfiltered item 4 institution directory and the provider-ranked current disclosure for each
unique `apbaId`. The disclosure-bound `disclosureNo:row ordinal` key is an observation identity,
not a stable Person identifier, so the existing materialization gate keeps every ALIO row in
`REVIEW_REQUIRED`. Raw report HTML, gender and disclosure-staff contacts are excluded.

The concrete feeders now demonstrate the shared repository transaction while retaining distinct
source contracts, coverage rules and semantic boundaries. Any future helper must remain small and
must be earned by verified duplication; a generic crawler or universal page runner is still not
justified.

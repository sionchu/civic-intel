# Civic Intel — Batch Ingestion DB Target

## Principle

DB 확장은 기존 provenance graph를 보존해야 한다.

현재 canonical source layer:

```text
SourcePolicy
→ Source
→ SourceSnapshot
```

새 batch DB는 이것을 대체하지 않는다.

추가:

```text
SourceRun
SourceCheckpoint
FeederObservation
```

identity phase:

```text
PersonObservationLink
IdentityReviewItem
```

Claim provenance extension:

```text
ClaimEvidence → optional FeederObservation
```

---

# 1. Existing tables to KEEP

다음은 SSOT다.

```text
source_policies
sources
source_snapshots
source_origin_clusters

people
person_aliases

claims
claim_evidence

organizations
offices
appointments

events
relationships
decision_episodes
hypotheses
profile_snapshots
...
```

`raw_observations` 또는 `raw_api_payloads` 같은 병렬 source truth table을 만들지 않는다.

---

# 2. Migration Phase 1 — implemented in `0003`

Batch run/checkpoint/observation persistence is implemented in Alembic revision `0003`.

## 2.1 `source_runs`

SQL-like target:

```sql
CREATE TABLE source_runs (
    id VARCHAR(36) PRIMARY KEY,

    feeder VARCHAR(100) NOT NULL,
    scope_key VARCHAR(300) NOT NULL,

    started_at DATETIME NOT NULL,
    finished_at DATETIME NULL,

    status VARCHAR(32) NOT NULL,

    checkpoint_before TEXT NULL,
    checkpoint_after TEXT NULL,

    records_seen INTEGER NOT NULL DEFAULT 0,
    observations_created INTEGER NOT NULL DEFAULT 0,
    observations_unchanged INTEGER NOT NULL DEFAULT 0,

    error_code VARCHAR(120) NULL,
    error_summary TEXT NULL,

    metadata_json JSON NOT NULL
);
```

indexes:

```text
ix_source_runs_feeder
ix_source_runs_status
ix_source_runs_started_at
(feeder, scope_key)
```

### Rules

status:

```text
RUNNING
SUCCESS
PARTIAL
FAILED
```

- `RUNNING`: run opened
- `SUCCESS`: requested scope complete and consistency checks pass
- `PARTIAL`: some committed progress, later source/page failure
- `FAILED`: no safely reusable progress or fatal precondition

`error_summary`:

- redacted
- no credential
- no raw request URL containing key
- no raw provider payload

---

## 2.2 `source_checkpoints`

```sql
CREATE TABLE source_checkpoints (
    id VARCHAR(36) PRIMARY KEY,

    feeder VARCHAR(100) NOT NULL,
    scope_key VARCHAR(300) NOT NULL,

    cursor TEXT NULL,
    metadata_json JSON NOT NULL,

    updated_at DATETIME NOT NULL,

    last_run_id VARCHAR(36) NULL
        REFERENCES source_runs(id),

    UNIQUE(feeder, scope_key)
);
```

indexes:

```text
(feeder, scope_key) UNIQUE
last_run_id
```

### Cursor examples

Assembly:

```text
"12"
```

Gwanbo if page-based:

```text
"47"
```

Gwanbo scope key:

```text
"2026-08-01:2026-08-31"
```

date window feeder:

```text
"2026-08-31"
```

복잡한 universal cursor class hierarchy를 만들지 않는다.

source-specific metadata는 `metadata_json` 사용.

### Metadata examples

Assembly:

```json
{
  "page_size": 1000,
  "expected_pages": 3,
  "list_total_count": 298,
  "source_contract": "assembly_member_roster"
}
```

### Rule

checkpoint advance와 page observations commit은 같은 transaction boundary에 둔다.

---

## 2.3 `feeder_observations`

```sql
CREATE TABLE feeder_observations (
    id VARCHAR(36) PRIMARY KEY,

    feeder VARCHAR(100) NOT NULL,
    scope_key VARCHAR(300) NOT NULL,

    provider_record_key VARCHAR(500) NOT NULL,

    snapshot_id VARCHAR(36) NOT NULL
        REFERENCES source_snapshots(id),

    run_id VARCHAR(36) NOT NULL
        REFERENCES source_runs(id),

    recorded_at DATETIME NOT NULL,
    provider_observed_at DATETIME NULL,

    semantic_scope VARCHAR(120) NOT NULL,

    identity_hints_json JSON NOT NULL,
    normalized_json JSON NOT NULL,

    content_hash VARCHAR(64) NOT NULL,

    UNIQUE (
        feeder,
        scope_key,
        provider_record_key,
        content_hash
    )
);
```

indexes:

```text
(feeder, provider_record_key)
snapshot_id
run_id
content_hash
semantic_scope
```

### Meaning

`provider_record_key`

원천 provider가 부여한 identity/row key.

예:

```text
MONA_CD
```

`provider_record_key` 자체는 observation version ID가 아니다.

`content_hash`

policy-approved normalized record의 deterministic canonical JSON hash.

추천 canonicalization:

```python
json.dumps(
    normalized_payload,
    ensure_ascii=False,
    sort_keys=True,
    separators=(",", ":"),
)
```

UTF-8 → SHA-256.

hash에 포함하지 말 것:

- fetched timestamp
- run id
- credentials
- transient request metadata
- random UUID
- disallowed provider fields

### Identity hints

Identity Resolution에 필요한 최소한:

Assembly example:

```json
{
  "canonical_name": "홍길동",
  "aliases": ["洪吉童", "Hong Gil-dong"],
  "birth_date": "1970-01-02",
  "external_ids": {
    "assembly_mona_cd": "M-001"
  }
}
```

### normalized_json

Assembly example:

```json
{
  "member_code": "M-001",
  "canonical_name": "홍길동",
  "aliases": ["洪吉童", "Hong Gil-dong"],
  "birth_date": "1970-01-02",
  "party": "정당",
  "district": "지역구",
  "reelection": "재선",
  "election_type": "지역구",
  "committees": "위원회"
}
```

must NOT contain:

```text
TEL_NO
E_MAIL
phone
email
raw provider row
API KEY
```

---

# 3. Source / Snapshot idempotency

## Source

`Source.url` existing unique.

persist algorithm conceptually:

```text
lookup by canonical URL
    ↓
not exists
    → insert Source

exists
    ↓
same policy identity
    → reuse

different incompatible policy
    → fail closed
```

Provider credentials must never be part of canonical URL.

## Snapshot

Current `IngestionPipeline` computes content hash even when fulltext cannot be stored.

This is useful.

Prefer:

```text
same Source + same content_hash
→ reuse existing snapshot
```

if easy and compatible.

But do not add a new DB unique constraint without testing current corpus/migrations.

Operational fetch attempts are already represented by SourceRun, so duplicate identical snapshot rows are usually unnecessary.

---

# 4. Transaction boundary

Recommended per-page transaction:

```text
BEGIN

SourcePolicy check was already done before fetch

persist/reuse Source
persist/reuse SourceSnapshot

for each normalized provider record:
    create FeederObservation if unique hash does not exist
    else count unchanged

update checkpoint

COMMIT
```

if any DB integrity/normalization conflict:

```text
ROLLBACK page
checkpoint does not move
```

Network fetch happens before DB transaction where practical to avoid long-held locks.

---

# 5. Run lifecycle

## Start

```text
insert SourceRun(status=RUNNING)
load SourceCheckpoint
record checkpoint_before
```

## Page complete

update:

```text
records_seen
observations_created
observations_unchanged
checkpoint
```

## Success

```text
status = SUCCESS
finished_at
checkpoint_after
```

## Partial

if earlier pages committed and later page fails:

```text
status = PARTIAL
finished_at
checkpoint_after = last committed cursor
error_code
redacted error summary
```

## Failed

precondition/source contract failure before useful progress:

```text
status = FAILED
```

---

# 6. Migration Phase 2 — implemented in `0004`

Assembly identity links, review items and exact claim/observation provenance are implemented in
Alembic revision `0004`.

## 6.1 `person_observation_links`

```sql
CREATE TABLE person_observation_links (
    id VARCHAR(36) PRIMARY KEY,

    person_id VARCHAR(36) NOT NULL
        REFERENCES people(id),

    observation_id VARCHAR(36) NOT NULL
        REFERENCES feeder_observations(id),

    action VARCHAR(40) NOT NULL,
    decision_class VARCHAR(80) NOT NULL,

    linked_at DATETIME NOT NULL,
    superseded_at DATETIME NULL,

    review_item_id VARCHAR(36) NULL
);
```

indexes:

```text
person_id
observation_id
decision_class
```

### Purpose

```text
Observation → Person
```

materialization provenance.

### Split support

잘못 연결된 경우 record 삭제보다:

```text
superseded_at = now
```

후 새 link 생성.

full event-sourcing framework는 필요 없다.

---

## 6.2 `identity_review_items`

```sql
CREATE TABLE identity_review_items (
    id VARCHAR(36) PRIMARY KEY,

    observation_id VARCHAR(36) NOT NULL
        REFERENCES feeder_observations(id),

    candidate_person_id VARCHAR(36) NULL
        REFERENCES people(id),

    reason_code VARCHAR(100) NOT NULL,
    details_json JSON NOT NULL,

    status VARCHAR(32) NOT NULL,

    created_at DATETIME NOT NULL,
    resolved_at DATETIME NULL,
    resolution_note TEXT NULL
);
```

status:

```text
OPEN
RESOLVED
REJECTED
```

No review UI required in current Epic.

---

## 6.3 Claim evidence → observation

Preferred extension:

```sql
ALTER TABLE claim_evidence
ADD COLUMN feeder_observation_id VARCHAR(36) NULL
REFERENCES feeder_observations(id);
```

index:

```text
feeder_observation_id
```

### Why

A SourceSnapshot can contain many provider rows.

Claim-level provenance should be able to identify the exact source record from which the claim was normalized.

Existing Golden/Reviewed claims:

```text
feeder_observation_id = NULL
```

allowed.

---

# 7. Materialization action table

Recommended:

| Situation | Action |
|---|---|
| authoritative feeder, unique provider key, no same-name ambiguity | `AUTO_CREATE` |
| provider key already linked to Person | `AUTO_LINK` |
| same name exists but no exact provider link | `REVIEW_REQUIRED` |
| cross-lane continuity only | `REVIEW_REQUIRED` for materialization |
| DOB/provider hard contradiction | `HARD_CONFLICT` |
| fuzzy score only | never auto |

No cross-person `AUTO_MERGE` required in this Epic.

---

# 8. Assembly first FACT transaction

Concept:

```text
FeederObservation
    ↓
MaterializationGate = AUTO_CREATE
    ↓
Person
    ↓
Claim(DRAFT, FACT, HELD_ROLE, 국회의원)
    ↓
ClaimEvidence(
    source_id,
    snapshot_id,
    feeder_observation_id
)
    ↓
validate_claim_publication()
    ↓
PUBLISHED only on success
```

transaction failure anywhere:

```text
Person + Claim + Evidence + Link all rollback
```

No orphan Person.

---

# 9. Repository boundary

Canonical implementation:

```text
packages/persistence/repository.py
```

contains shared SQLAlchemy repository behavior used by both API and workers.

Batch worker DB writes must not result in a second independent session/repository implementation.

The previous API-local repository module was removed.

- all internal imports use the shared package;
- `ARCHITECTURE.md` records the dependency direction;
- only one repository implementation remains;
- API and worker tests use the same repository;
- there is no module-level schema creation;
- runtime still requires the Alembic head.

---

# 10. Alembic Rules

Every persistence change:

- explicit migration
- deterministic downgrade
- fresh DB upgrade
- populated fixture DB upgrade
- downgrade one revision
- re-upgrade

Do not:

- use `create_all()` in runtime
- silently create missing tables
- auto-migrate on API startup

Current architecture invariant remains:

> Alembic is the only runtime schema change path.

---

# 11. SQLite / PostgreSQL compatibility

Current dev/test default uses SQLite.

Do not introduce PostgreSQL-only data types in foundation unless truly necessary.

Use existing:

```text
String
Text
Integer
DateTime(timezone=True)
JSON
ForeignKey
UniqueConstraint
Index
```

patterns.

JSON fields must contain JSON-serializable deterministic values.

---

# 12. Future L4 — explicitly deferred

Do NOT add now:

```text
source_schedules
distributed leases
worker heartbeats
queue offsets
Kafka event log
CDC infrastructure
Temporal workflow state
```

L3 data model should not prevent L4, but must not pre-build it.

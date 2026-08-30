# Batch ingestion L3 transition

Status: planned / active when implementation begins.

## Objective

Move Civic Intel from reviewed single-pull staging and person-by-person onboarding to a
policy-first, resumable, source-bounded full-enumeration pipeline.

The first complete reference feeder is the National Assembly member roster.

The second-source proof is official Gwanbo personnel data, subject to fresh verification of
the actual API/schema/rights before implementation.

---

## Baseline

At plan creation handoff:

```text
master: 52b32da5c8c0ec577ca81f7bd1a8c18037557304
Alembic head: 0002
open person-specific issue: #55
```

Recheck these values before implementation and replace them here with actual values.

### Existing pieces to preserve

- SourcePolicy
- Source
- SourceSnapshot
- Claim / ClaimEvidence
- Golden Set 001
- ReviewedPersonBundle regression path
- IngestionPipeline
- OpenAssemblyMemberConnector
- AssemblyRosterStager
- existing publication gate

### Known RE0

- feeder `MERGED` status is ambiguous
- current identity resolvers use numeric scores
- SqlAlchemyRepository currently lives under `apps/api`
- no persistent full-enumeration run/checkpoint/observation layer

---

# Milestone A — Governance alignment

- [ ] read all governing docs
- [ ] verify HEAD
- [ ] run baseline `make verify`
- [ ] update feeder maturity to L0–L4
- [ ] update V0 scope for source-bounded official enumeration
- [ ] keep generic broad crawling prohibited
- [ ] add `BATCH_INGESTION.md` to docs index
- [ ] clarify profiler is deep enrichment, not mandatory ingestion
- [ ] document ReviewedPersonBundle as manual/regression path
- [ ] defer #55 without changing current regression semantics
- [ ] verify docs/code terminology

Evidence:

```text
fill during execution
```

Commit:

```text
fill during execution
```

---

# Milestone B — Batch persistence + Assembly L3

## Persistence

- [ ] search for equivalent persistence contracts before adding
- [ ] decide canonical shared repository location
- [ ] ensure only one SqlAlchemyRepository implementation
- [ ] add SourceRun contract/row
- [ ] add SourceCheckpoint contract/row
- [ ] add FeederObservation contract/row
- [ ] add indexes/uniqueness
- [ ] add reversible Alembic migration
- [ ] add repository CRUD/transaction helpers
- [ ] keep SourceSnapshot as source-level capture
- [ ] no raw-payload truth store

## Assembly

- [ ] full unfiltered pagination
- [ ] total count consistency
- [ ] page consistency
- [ ] MONA_CD uniqueness/conflict checks
- [ ] page transaction
- [ ] checkpoint
- [ ] partial status
- [ ] resume
- [ ] unchanged rerun no-op
- [ ] changed row new observation
- [ ] privacy/contact exclusion
- [ ] credential redaction
- [ ] CLI or operational entrypoint only if justified

## Tests

- [ ] multi-page
- [ ] unchanged rerun
- [ ] changed row
- [ ] failed page
- [ ] resume
- [ ] total count mismatch
- [ ] duplicate page
- [ ] conflicting MONA_CD
- [ ] policy denied
- [ ] secret absent
- [ ] TEL_NO absent
- [ ] E_MAIL absent
- [ ] SQLite migration integration
- [ ] existing staging regression

Evidence:

```text
fill during execution
```

Commit:

```text
fill during execution
```

---

# Milestone C — Deterministic identity RE0

- [ ] inspect all current resolver call sites
- [ ] define explicit decision classes
- [ ] remove or isolate numeric score
- [ ] no score in materialization
- [ ] update cross-lane rules
- [ ] preserve reviewed research identity semantics where justified
- [ ] distinguish research resolution from materialization permission
- [ ] update ProfileResearchTarget serialization
- [ ] update docs
- [ ] update tests

Acceptance cases:

```text
name only → review
birth conflict → fail closed
exact external id → explicit resolved class
official career bridge → research evidence, not auto merge
```

Evidence:

```text
fill during execution
```

Commit:

```text
fill during execution
```

---

# Milestone D — Safe materialization

## Persistence

- [ ] PersonObservationLink
- [ ] IdentityReviewItem
- [ ] reversible migration
- [ ] optional ClaimEvidence → FeederObservation FK if coherent

## Gate

- [ ] AUTO_CREATE
- [ ] AUTO_LINK
- [ ] REVIEW_REQUIRED
- [ ] HARD_CONFLICT
- [ ] no fuzzy AUTO_MERGE

## Assembly

- [ ] new unique MONA_CD can create one Person
- [ ] same MONA_CD rerun reuses Person
- [ ] same Korean name without provider link does not merge
- [ ] minimal HELD_ROLE FACT
- [ ] exact observation provenance
- [ ] publication validator required
- [ ] coherent transaction rollback

## Regression

- [ ] Golden Set green
- [ ] ReviewedPersonBundle imports green
- [ ] Kim Hyun-ji neutral controversy semantics unchanged
- [ ] Ha Jung-woo/Im Moon-young regressions unchanged

Evidence:

```text
fill during execution
```

Commit:

```text
fill during execution
```

---

# Milestone E — Gwanbo second-source L3

## Research

- [ ] verify official current API
- [ ] verify exact endpoint
- [ ] verify authentication
- [ ] verify pagination
- [ ] verify provider record identifier
- [ ] verify rate limit
- [ ] verify license
- [ ] review metadata/fulltext/AI/commercial rights
- [ ] write SourcePolicy

## Implementation

- [ ] connector
- [ ] source-specific enumeration
- [ ] SourceRun
- [ ] checkpoint/resume
- [ ] FeederObservation
- [ ] policy-minimized normalized personnel record
- [ ] no guessed career fields
- [ ] reuse CivilServiceCareerEpisode semantics where applicable
- [ ] mocked deterministic tests
- [ ] no new generic framework unless proven by Assembly+Gwanbo duplication

Evidence:

```text
fill during execution
```

Commit:

```text
fill during execution
```

---

# Milestone F — Final audit

## Verification

- [ ] targeted tests
- [ ] `make verify`
- [ ] fresh Alembic upgrade
- [ ] Alembic downgrade one revision
- [ ] Alembic re-upgrade
- [ ] inspect actual CI if available
- [ ] local results labelled local

## Clean-v0

- [ ] no duplicate repository
- [ ] no duplicate raw truth store
- [ ] no old path drift
- [ ] no unused batch abstractions
- [ ] no numeric score materialization shortcut
- [ ] no credential persistence
- [ ] no contact/private field persistence
- [ ] no generic crawler
- [ ] no person-by-person #55 work mixed in
- [ ] docs match implementation

## Deferred list confirmed

- [ ] Splink
- [ ] Vector DB
- [ ] MCP
- [ ] Temporal/Airflow/Celery/Kafka
- [ ] L4 scheduler
- [ ] all feeder conversions
- [ ] UI redesign

Final ending HEAD:

```text
fill during execution
```

---

# Stop condition

Stop this execution plan after:

1. Assembly is genuinely L3;
2. batch DB is persistent and resumable;
3. deterministic materialization gate exists;
4. ambiguous identities enter review;
5. Gwanbo proves the same foundation on a second official source;
6. full verification and migration roundtrip pass;
7. final diff contains no unnecessary parallel architecture.

Then propose exactly one next feeder as Next Best Action.

# Batch ingestion L3 transition

Status: active — Milestones A–B complete, Milestone C in progress.

## Objective

Move Civic Intel from reviewed single-pull staging and person-by-person onboarding to a
policy-first, resumable, source-bounded full-enumeration pipeline.

The first complete reference feeder is the National Assembly member roster.

The second-source proof is official Gwanbo personnel data, subject to fresh verification of
the actual API/schema/rights before implementation.

---

## Baseline

Implementation baseline verified on 2026-08-31:

```text
master: a56e7a665ce6de5bd12b11c75cbdc57ed4f40ffa
Alembic head: 0002
person-specific issue #55: deferred; no person-by-person work is in this plan
```

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

- [x] read all governing docs
- [x] verify HEAD
- [x] run baseline `make verify`
- [x] update feeder maturity to L0–L4
- [x] update V0 scope for source-bounded official enumeration
- [x] keep generic broad crawling prohibited
- [x] add `BATCH_INGESTION.md` to docs index
- [x] clarify profiler is deep enrichment, not mandatory ingestion
- [x] document ReviewedPersonBundle as manual/regression path
- [x] defer #55 without changing current regression semantics
- [x] verify docs/code terminology

Evidence:

```text
HEAD: a56e7a665ce6de5bd12b11c75cbdc57ed4f40ffa
Alembic: .venv/Scripts/python.exe -m alembic heads -> 0002 (head)
make verify -> RUNNER_UNAVAILABLE because GNU make is unavailable on this Windows host.
Equivalent baseline gates executed individually:
- ruff -> All checks passed
- mypy -> Success: no issues found in 47 source files
- pytest -> 181 passed, 1 warning
- packages.verification.quality -> passed: true
- web lint -> exit 0
- web typecheck -> exit 0
- web tests -> 2 passed
- web build -> compiled successfully
Terminology audit: no MERGED/ISSUE_OPEN/UNRESEARCHED feeder status remains outside this
historical Known RE0 note.
```

Commit:

```text
0fb6e0e P0: align batch ingestion L3 governance
```

---

# Milestone B — Batch persistence + Assembly L3

## Persistence

- [x] search for equivalent persistence contracts before adding
- [x] decide canonical shared repository location
- [x] ensure only one SqlAlchemyRepository implementation
- [x] add SourceRun contract/row
- [x] add SourceCheckpoint contract/row
- [x] add FeederObservation contract/row
- [x] add indexes/uniqueness
- [x] add reversible Alembic migration
- [x] add repository CRUD/transaction helpers
- [x] keep SourceSnapshot as source-level capture
- [x] no raw-payload truth store

## Assembly

- [x] full unfiltered pagination
- [x] total count consistency
- [x] page consistency
- [x] MONA_CD uniqueness/conflict checks
- [x] page transaction
- [x] checkpoint
- [x] partial status
- [x] resume
- [x] unchanged rerun no-op
- [x] changed row new observation
- [x] privacy/contact exclusion
- [x] credential redaction
- [x] CLI or operational entrypoint only if justified

## Tests

- [x] multi-page
- [x] unchanged rerun
- [x] changed row
- [x] failed page
- [x] resume
- [x] total count mismatch
- [x] duplicate page
- [x] conflicting MONA_CD
- [x] policy denied
- [x] secret absent
- [x] TEL_NO absent
- [x] E_MAIL absent
- [x] SQLite migration integration
- [x] existing staging regression

Evidence:

```text
Alembic head: 0003
Canonical repository: packages/persistence/repository.py
Implementation search: exactly one `class SqlAlchemyRepository`; no apps.api.repository import.
Targeted: pytest test_batch_assembly.py test_repository.py test_migrations.py
          test_assembly_staging.py test_open_assembly.py -> 26 passed
Full local verification after implementation:
- ruff -> All checks passed
- mypy -> Success: no issues found in 48 source files
- pytest -> 190 passed, 3 warnings
- packages.verification.quality -> passed: true
- web lint/typecheck -> exit 0
- web tests -> 2 passed
- web build -> compiled successfully
Migration regression upgrades a fresh DB through 0003, downgrades 0003 -> 0002 -> 0001,
re-upgrades to head, and preserves a populated Person row.
Privacy regression proves TEL_NO, E_MAIL, provider contact value and API secret are absent from
observations, Source URLs, snapshot metadata, run receipts and error summaries.
```

Commit:

```text
pending Milestone B commit
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

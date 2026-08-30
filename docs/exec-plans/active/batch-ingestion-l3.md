# Batch ingestion L3 transition

Status: completed — stop condition met on 2026-08-31.

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
620012e P0: add resumable Assembly L3 ingestion
```

---

# Milestone C — Deterministic identity RE0

- [x] inspect all current resolver call sites
- [x] define explicit decision classes
- [x] remove or isolate numeric score
- [x] no score in materialization
- [x] update cross-lane rules
- [x] preserve reviewed research identity semantics where justified
- [x] distinguish research resolution from materialization permission
- [x] update ProfileResearchTarget serialization
- [x] update docs
- [x] update tests

Acceptance cases:

```text
name only → review
birth conflict → fail closed
exact external id → explicit resolved class
official career bridge → research evidence, not auto merge
```

Evidence:

```text
Explicit IdentityDecisionClass replaces identity score/threshold fields.
Acceptance cases:
- name only -> REVIEW / CONTEXT_REVIEW
- exact birth contradiction -> UNRESOLVED / BIRTH_DATE_CONFLICT
- exact external id -> RESOLVED / EXTERNAL_ID
- official career bridge -> RESOLVED / OFFICIAL_CAREER_CONTINUITY with
  decision_scope=RESEARCH_IDENTITY_ONLY in ProfileResearchTarget serialization
Targeted identity/profile regression -> 36 passed, 1 warning
Full local verification:
- ruff -> All checks passed
- mypy -> Success: no issues found in 48 source files
- pytest -> 191 passed, 3 warnings
- packages.verification.quality -> passed: true
- web lint/typecheck -> exit 0
- web tests -> 2 passed
- web build -> compiled successfully
Search confirms no identity score or threshold remains; origin-source deduplication retains its
separate similarity heuristic and is not identity or materialization authority.
```

Commit:

```text
a9fa069 P0: replace identity scores with explicit decisions
```

---

# Milestone D — Safe materialization

## Persistence

- [x] PersonObservationLink
- [x] IdentityReviewItem
- [x] reversible migration
- [x] optional ClaimEvidence → FeederObservation FK if coherent

## Gate

- [x] AUTO_CREATE
- [x] AUTO_LINK
- [x] REVIEW_REQUIRED
- [x] HARD_CONFLICT
- [x] no fuzzy AUTO_MERGE

## Assembly

- [x] new unique MONA_CD can create one Person
- [x] same MONA_CD rerun reuses Person
- [x] same Korean name without provider link does not merge
- [x] minimal HELD_ROLE FACT
- [x] exact observation provenance
- [x] publication validator required
- [x] coherent transaction rollback

## Regression

- [x] Golden Set green
- [x] ReviewedPersonBundle imports green
- [x] Kim Hyun-ji neutral controversy semantics unchanged
- [x] Ha Jung-woo/Im Moon-young regressions unchanged

Evidence:

```text
Alembic head: 0004
Targeted materialization/migration/API/Golden/reviewed-person regression -> 35 passed;
final materialization + migration check -> 7 passed after linked-provider conflict coverage.
AUTO_CREATE writes Person + PUBLISHED HELD_ROLE FACT + ClaimEvidence + PersonObservationLink in
one transaction only after validate_claim_publication succeeds.
ClaimEvidence.feeder_observation_id retains exact provider-row provenance.
AUTO_LINK requires an existing accepted provider-key link and is idempotent for the same
observation. Same-name observations produce OPEN review items; exact birth-date contradictions
produce HARD_CONFLICT review items. Synthetic publication failure leaves the observation intact
and rolls back Person, Claim, Evidence and link.
Full local verification:
- ruff -> All checks passed
- mypy -> Success: no issues found in 49 source files
- pytest -> 197 passed, 3 warnings
- packages.verification.quality -> passed: true
- web lint/typecheck -> exit 0
- web tests -> 2 passed
- web build -> compiled successfully
```

Commit:

```text
bb0c6f1 P0: add safe batch identity materialization
```

---

# Milestone E — Gwanbo second-source L3

## Research

- [x] verify official current API
- [x] verify exact endpoint
- [x] verify authentication
- [x] verify pagination
- [x] verify provider record identifier
- [x] verify rate limit; none published, so sequential bounded windows only
- [x] verify license; none stated on the API page, so downstream reuse is blocked
- [x] review metadata/fulltext/AI/commercial rights
- [x] write SourcePolicy

## Implementation

- [x] connector
- [x] source-specific enumeration
- [x] SourceRun
- [x] checkpoint/resume
- [x] FeederObservation
- [x] policy-minimized normalized personnel record
- [x] no guessed career fields
- [x] reuse CivilServiceCareerEpisode semantics where applicable; list metadata stops before it
- [x] mocked deterministic tests
- [x] no new generic framework unless proven by Assembly+Gwanbo duplication

Evidence:

```text
Official contract reviewed on 2026-08-31:
- UI: https://open.gwanbo.go.kr/OpenApi/web/personnelList
- list: POST https://open.gwanbo.go.kr/OpenApi/web/personnelListAjax
- request: themaSe=06, reqFrom/reqTo, currentPage/rowPerPage
- provider key: cntntSeqNo from the official fnDetail contract
- authentication: none exposed or sent
- rate limit/reuse license: not stated; page footer states all rights reserved

SourcePolicy permits FETCH + STORE_METADATA only. Fulltext, excerpts, AI transmission and
commercialization are blocked. Original-file URL/body and print flags are not persisted.
identity_hints is empty because the list exposes no structured person identity. No title-derived
Person or CivilServiceCareerEpisode is created.

Targeted Gwanbo tests -> 7 passed, 1 cache warning.
Coverage includes official POST contract, multi-page enumeration, unchanged rerun, immutable
change version, failure/resume, total change, duplicate key, empty official shape and policy
denial.

Live local probe, scope 2026-08-01:2026-08-31:
- status SUCCESS
- pages_committed 1
- unique_records 0
The current official endpoint returned an empty result; this is recorded as current live source
behavior and is not promoted to evidence of a permanently empty source.

Full local verification after Gwanbo:
- ruff -> All checks passed
- mypy -> Success: no issues found in 52 source files
- pytest -> 204 passed, 4 warnings
- packages.verification.quality -> passed: true
```

Commit:

```text
6d53562 P0: add Gwanbo personnel notice L3 feeder
```

---

# Milestone F — Final audit

## Verification

- [x] targeted tests
- [x] `make verify` attempted; GNU make unavailable on this Windows host
- [x] fresh Alembic upgrade
- [x] Alembic downgrade one revision
- [x] Alembic re-upgrade
- [x] inspect actual CI if available
- [x] local results labelled local

## Clean-v0

- [x] no duplicate repository
- [x] no duplicate raw truth store
- [x] no old path drift
- [x] no unused batch abstractions
- [x] no numeric score materialization shortcut
- [x] no credential persistence
- [x] no contact/private field persistence
- [x] no generic crawler
- [x] no person-by-person #55 work mixed in
- [x] docs match implementation

## Deferred list confirmed

- [x] Splink
- [x] Vector DB
- [x] MCP
- [x] Temporal/Airflow/Celery/Kafka
- [x] L4 scheduler
- [x] all feeder conversions
- [x] UI redesign

Evidence:

```text
Canonical make verify runner:
- RUNNER_UNAVAILABLE: GNU make is not installed on this Windows host.

Equivalent canonical commands executed locally:
- ruff -> All checks passed
- mypy -> Success: no issues found in 51 source files
- pytest -> 204 passed, 4 warnings
- packages.verification.quality -> passed: true
- web lint -> exit 0
- web typecheck -> exit 0
- web tests -> 2 passed
- web build -> compiled successfully
- targeted batch/materialization/migration tests -> 23 passed, 3 warnings

Independent migration DB:
- fresh upgrade -> 0004
- downgrade -1 -> 0003
- re-upgrade -> 0004 (head)

GitHub Actions inspected:
- baseline master SHA a56e7a6 run 33327647910: CI_RUNNER_BLOCKED before any step
- annotation: recent account payments failed or spending limit must be increased
- no GitHub check exists for the local implementation commits; no CI PASS is claimed

Clean-v0 audit:
- exactly one class SqlAlchemyRepository, in packages/persistence/repository.py
- no apps.api.repository import or API-local implementation
- no raw observation/payload truth table
- source-specific connectors only; no generic crawler/framework
- origin deduplication retains its separate similarity score, while identity and
  materialization contain no numeric threshold authority
- contact/credential exclusion tests pass; no secret or provider contact field persists
- deferred infrastructure and person-specific issue #55 are absent from the implementation diff
- git diff --check passed
```

Final ending HEAD:

```text
Implementation HEAD: 6d53562
Closure metadata: recorded by the commit containing this completed ExecPlan; a self-referential
commit SHA is intentionally not embedded.
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

## Next Best Action

Promote the NEC local elected-office winner roster from L2 to L3, bounded by election code and
office class, using the existing official connector and `huboid` identity anchor on the same
run/checkpoint/observation foundation.

# Civic Intel System Overview

Status: repository orientation document; non-governing summary.

Operational snapshot: 2026-09-28, repository baseline `6f1b512`. The application/persistence
topology below reflects source inspected at architecture-refactor base `0c52cd4`; it is not a
runtime, staging or deployment verification claim.

This document explains the project as one system: why it exists, how data moves, what the
architecture protects, how source gates work, which source scopes are actually collected, what
remains blocked, and what the next decision boundary is.

It is **not** a replacement for the governing contracts. When details conflict, use the more
specific authority:

1. [AGENTS.md](../../AGENTS.md) — execution rules and non-negotiable invariants.
2. [ARCHITECTURE.md](../../ARCHITECTURE.md) — canonical dependency and evidence boundaries.
3. [Civic Intel North Star](../product/CIVIC_INTEL_NORTH_STAR.md) — long-term product direction.
4. [V0 scope](../product/V0_SCOPE.md) — current delivery boundary.
5. [Feeder source coverage](FEEDER_SOURCE_COVERAGE.md) — source maturity and acquisition gates.
6. Source-specific architecture and active/blocked execution plans — exact source contracts.
7. [HANDOFF.md](../../HANDOFF.md) — current operational evidence and next concrete action.

## 1. Why Civic Intel exists

Civic Intel is an evidence-backed public-governance intelligence platform. Its purpose is not to
tell a reader what political conclusion to reach. It is to make public records traceable enough
that a reader can inspect people, institutions, actions, money, decisions and change and make an
independent judgment.
The product principle is:

> **Evidence underneath. Curiosity on top.**

A useful Civic Intel result starts with an interesting question but ends at inspectable evidence.
The system therefore optimizes for provenance, scope, correction visibility and reproducibility,
not for outrage, partisan persuasion or opaque engagement ranking.

The long-term discovery vocabulary is:

| Primitive | Reader question |
|---|---|
| CHANGE | What changed? |
| CONTRADICTION | Which records or propositions do not agree? |
| COMPARISON | How do comparable subjects differ? |
| CONNECTION | What documented institutional or activity connection exists? |
| MONEY | How did a public or disclosed monetary record change? |

These are product primitives, not permission to create five new databases or infer motives,
wrongdoing, ideology, friendship or influence.

## 2. What the project is not

Civic Intel is not:

- a generic crawler or scraped copy of government websites;
- a name-matching people graph;
- a political ranking, persuasion or ideology-scoring engine;
- a raw-data lake with a second truth store;
- an AI system that can publish facts, merge identities or repair missing provenance on its own;
- a system where successful collection automatically means public publication;
- a system where an official source automatically grants unrestricted storage or redistribution.

The project deliberately keeps **acquisition, identity, truth posture, publication and analysis as
different decisions**.
## 3. System architecture

Keep code dependencies distinct from runtime call flow. The domain is framework-independent;
application owns use-case orchestration and repository/UoW ports; SQLAlchemy persistence
adapters implement those ports. The adapter imports inward-facing port/result types, while runtime
calls flow from composition roots through use cases into the UoW.

The current code dependency boundaries are:

```text
packages/domain: independent contracts and enums
packages/verification, packages/connectors → packages/domain
packages/application → packages/domain + verification/rendering; defines ports
packages/persistence → implements application ports with SQLAlchemy adapters
apps/api, workers: composition roots; apps/web → apps/api
```

Runtime calls flow API/workers → application use case → UoW port → session-bound adapter →
SQLAlchemy session.

`packages/application` may also call project verification/rendering collaborators. It must not
own SQLAlchemy sessions or import persistence. `packages/persistence` contains session-bound
repositories and row mappers; `Database` / `SqlAlchemyUnitOfWork` are the single canonical engine,
session and transaction boundary. See [Architecture](../../ARCHITECTURE.md) for the precise layer
contract.

The evidence/data path is:

```text
Official source or reviewed packet
        ↓
SourcePolicy
        ↓
Source
        ↓
SourceSnapshot
        ↓
FeederObservation
        ↓
deterministic candidate/materialization rules
        ↓
Person or Organization
        ↓
Claim ──→ ClaimEvidence
        │          ↓
        └────── Source / Snapshot / Observation provenance
        ↓
publication gate
        ↓
API / Web read model
        ↓
Derived Intelligence such as CHANGE or MONEY
```

`SourceRun` and `SourceCheckpoint` describe collection operations. They are not truth records.
### 3.1 Evidence Core

The Evidence Core owns canonical semantics:

- `Person` and `Organization` are canonical entities.
- `Claim` states one proposition about exactly one supported canonical subject.
- `ClaimEvidence` points to the evidence supporting, refuting or contextualizing that Claim.
- `SourcePolicy` defines what a source may be used for.
- `SourceSnapshot` is the sole canonical source-level capture.
- `FeederObservation` is an immutable, policy-minimized record-level observation.
- temporal fields separate valid time from system-recording/supersession time.

Every rendered factual item must retain:

```text
Claim → ClaimEvidence → Source → SourcePolicy
```

and, when the data came through a feeder:

```text
ClaimEvidence → FeederObservation → SourceSnapshot → Source
```

Visibility and truth are separate. A `PUBLISHED` record is not automatically `FACT`; an explicit
`UNKNOWN` may be published as unresolved, and conflicting SUPPORT/REFUTE evidence remains visible.

### 3.2 Application, persistence and schema

Named application services own use-case transactions through `UnitOfWorkFactory` and `UnitOfWork`
ports. The UoW composes session-bound acquisition, identity, profile, review, onboarding,
organization, public and administration repositories on one SQLAlchemy session. Application
services validate then explicitly commit; the UoW context rolls back remaining work on exit.
Public API routes construct `DirectoryView` with one read UoW per request, so that projection reads
share a coherent database snapshot. API and workers use the same Database/UoW implementation;
there is no `SqlAlchemyRepository` facade or parallel worker persistence stack.

Pydantic contracts own semantics; SQLAlchemy rows persist them; `packages/persistence/mapping.py`
maps row/contract representations. Alembic is the only schema creation/change path. Runtime
startup checks declared reader-compatible revisions `0006`, `0007` and `0008` (expected head
`0008`); it never silently creates or seeds the database.
### 3.3 Acquisition and workers

Workers compose their source-specific connector/enumerator and `IngestionPipeline` with
`SourceLifecycle` and the shared `AcquisitionService`. They may:

- fetch only a reviewed, source-bounded scope;
- normalize policy-permitted fields;
- persist Source/Snapshot/Observation/run/checkpoint state;
- request deterministic materialization through a reviewed contract.

Workers may **not** publish Claims or bypass identity/publication gates.

Generic crawling is prohibited because it destroys source semantics and provenance, not because
large datasets are inherently disallowed. A complete official API can be fully enumerated when its
universe, rights, pagination, keys, corrections and QA are explicitly defined.

### 3.4 Identity and materialization

Provider identity is not canonical identity.

Examples:

- National Assembly `MONA_CD` is a provider anchor within its contract.
- NEC `huboid` is election-scope provider identity, not a universal Person ID.
- MOIS `org_code`, org.go `orgCode` and ALIO `apbaId` are provider organization identifiers,
  not Civic Intel Organization UUIDs.
- ALIO and OpenDART executive rows generally do not publish a stable universal Person ID.

Name equality, fuzzy similarity, embeddings, co-mention or organizational proximity cannot
authorize a Person merge. Safe deterministic source-context nodes may be created only under a
source-specific contract, and ambiguous/cross-lane cases fail closed to human review.

### 3.5 Publication

Collection, materialization and publication are separate.

```text
collected observation ≠ canonical identity ≠ published Claim
```
A Claim becomes public only through the normal publication gate with eligible evidence, source
policy and subject state. Private review metadata and operational receipts are not public facts.

### 3.6 Derived Intelligence

Derived Intelligence operates over already eligible Evidence Core inputs. It does not become a
canonical FACT merely because its inputs are FACTs.

The current proof points are:

- Assembly historical role sequence → source-specific CHANGE.
- ALIO Item 12 annual institution-head business expense → source-specific MONEY.
- Both share the additive `SOURCE_NEUTRAL_DERIVED_CHANGE_TRACE_V1` evidence/subject trace, while
  keeping their domain-specific comparability and interpretation rules separate.

Every derived result should retain methodology/version, exact input scope, time range, units,
coverage, missingness, limitations and correction behavior.

## 4. Source gate model

Technical access is never enough. Every acquisition lane begins with a source contract and
`SourcePolicy`.

### 4.1 Maturity levels

| Level | Meaning |
|---|---|
| L0 RESEARCHED | Source, purpose and policy strategy are understood; no ingestion contract proven. |
| L1 CONTRACT_STAGED | Source-specific contracts and deterministic fixtures/packets exist. |
| L2 SINGLE_PULL | One reviewed live pull or reproducible rights-approved packet proves the bounded path. |
| L3 FULL_ENUMERATION | The declared bounded universe has validated coverage, persistent runs/checkpoints, resume and idempotent observations. |
| L4 PRODUCTION_SYNC | Scheduled/incremental refresh, freshness, reconciliation and monitoring exist. |

`BLOCKED` qualifies a path. It does not mean the subject matter is useless; it means the currently
examined acquisition route lacks a safe/complete contract.
### 4.2 What must be proven before L3

A source-specific full-enumeration contract should answer all of these:

1. **Authority / rights** — may we fetch, retain, transform and expose the fields we need?
2. **Bounded universe** — what exactly counts as complete?
3. **Stable source identity** — what key identifies a source record inside that universe?
4. **Pagination / coverage** — how do we prove no pages or records were silently skipped?
5. **Version / correction semantics** — how do amended, withdrawn or repeated records behave?
6. **Field minimization** — which fields are necessary, and which private/sensitive fields are dropped?
7. **Provenance** — can every observation point back to one exact SourceSnapshot/Source?
8. **Determinism** — can parsing/normalization be reproduced in offline tests?
9. **Operational recovery** — are run/checkpoint/resume/idempotency semantics explicit?
10. **Identity boundary** — does the source identify a Person/Organization, or only nominate a candidate?
11. **Publication boundary** — what additional evidence/review is needed before a public Claim exists?

A successful download, fixture or manually counted packet is not L3 by itself.

## 5. Three different meanings of “status”

Civic Intel deliberately distinguishes:

| Axis | Question |
|---|---|
| Repository/source maturity | Has the connector/contract reached L0/L1/L2/L3? |
| Operational DB coverage | Has that scope actually been loaded successfully into this database? |
| Public/review state | Have identities and Claims been reviewed and published? |

This distinction prevents statements such as “the source is implemented, therefore all data is
collected” or “the data is collected, therefore it is public.”

## 6. Current operational snapshot — 2026-09-28

The Mac PostgreSQL database currently contains:

| Canonical/operational object | Count |
|---|---:|
| Current People | 9,120 |
| Current Organizations | 374 |
| Current Claims | 14,397 |
| Published Claims | 5,576 |
| ClaimEvidence rows | 14,397 |
| Sources | 4,589 |
| SourceSnapshots | 4,589 |
Current persisted feeder observations:

| Feeder / bounded scope | Stored observations | Current proven state |
|---|---:|---|
| National Assembly current member roster | 299 | L3 scope collected; SUCCESS checkpoint |
| National Assembly bill participation, Assembly age 22 | 19,651 | L3 bounded full-term scope collected; SUCCESS |
| NEC 2026 local-election candidate scopes | 6,756 | L3 selected election/type scopes collected; SUCCESS |
| ALIO item 4 current public-institution executives | 3,799 | L3 current-directory observation coverage; SUCCESS |
| MOIS standard Organization codes, current `stop_selt=0` | 133,930 | L3 current universe, 134 pages; SUCCESS |
| OpenDART listed-company 2025 annual-report executives | 35,022 | L3 declared listed-company universe loaded; checkpoint 3,994 companies |
| Gukgam 2026 reviewed schedule packet | 57 | Seven reviewed committee scopes loaded; SUCCESS |
| ALIO Item 12 institution-head business expense | 15 | L2 bounded proof: C0019, C0129, C0908 only |

These counts describe **this operational database**, not a claim that every possible Civic Intel
source or every person/institution in Korea has been collected.

## 7. Current Gukgam / Organization review boundary

The Gukgam source schedule itself is collected, but organization binding/publication coverage is
not complete.

Current read-only operator state:

- status: `CURRENT_HUMAN_REVIEW_READY`;
- existing published Gukgam target Claims: 110;
- additional exact-one Gukgam occurrences awaiting review: **41**;
- Organizations represented by those 41 occurrences: **27**;
- reviewed DRAFT manifest SHA:
  `9bb202c3de7c219382f69c91b8b0014bba7442428b673b55ac7ebbf766e711a9`;
- `claim_commit_authorized=false`.
The independent MOIS proposal lane currently reports:

- **70** proposed Organizations;
- **74** Gukgam occurrences covered by those proposals;
- **0** ambiguous exact provider-name matches;
- **159** distinct Gukgam labels still unmatched after that proposal set;
- `materialization_authorized=false`.

These are two separate approval boundaries:

```text
Gukgam exact-one existing Organization
    → human review
    → reviewed Gukgam Claim manifest
    → fresh preflight
    → explicit Claim commit

MOIS exact provider-name proposal
    → human review
    → source-specific reviewed Organization materialization manifest
    → fresh preflight
    → explicit Organization commit
    → later, separately reviewed Gukgam Claim work
```

Exact name equality is discovery evidence. It is not approval.

The private operator console at `/admin/review?tab=manifest` is the current review control plane.
It is read-only for these lanes and links reviewers to the canonical Organization, MOIS observation
and Gukgam schedule observation records.

## 8. What is not fully collected

“Collection complete” is always scope-specific. Important incomplete or blocked lanes include:

| Lane | Current state | Why it is not “done” |
|---|---|---|
| ALIO Item 12 business expense | L2 bounded 3-institution proof | Full institution annual-row universe and correction contract have not been selected/proven as L3. |
| Gukgam Organization coverage | Source schedule collected; binding incomplete | 41 existing-Organization occurrences and 70 MOIS proposals require review; 159 labels remain unmatched. |
| CleanEye local-public-institution executives | L0 RESEARCHED; BLOCKED | No approved repeatable named-executive route under the current source/robots contract. |
| Government Public Ethics employment review | L1 CONTRACT_STAGED; L3 blocked | Complete result universe, correction/coverage and permitted route contract unresolved. |
| National Assembly asset disclosure | L0 RESEARCHED; BLOCKED | Release coverage, revision/key semantics and permitted acquisition route unresolved. |
| Presidential Office/personnel lanes | L1 CONTRACT_STAGED; live/L3 blocked | Source-specific route/rights contract is not yet sufficient for automated live ingestion. |
| Assembly historical member careers | L1 packet parser; L3 blocked | No complete code manifest, stable row key or correction/version contract. |
| Assembly proposal-reason / major-content text | L0 RESEARCHED; BLOCKED | No verified structured source; bill-detail HTML scraping remains prohibited. |
| Government-funded research-career profiles | L0 RESEARCHED; automated path blocked | No complete staff universe, stable profile key or reuse/version contract. |

The full detailed matrix, including additional L0/L1/L2 lanes, is maintained in
[Feeder source coverage](FEEDER_SOURCE_COVERAGE.md).

## 9. Why some useful data stays blocked

A blocked lane protects the integrity of the product. Typical reasons are:

- the official source does not define a complete universe;
- the available page has no stable record key;
- correction/withdrawal semantics are unknown;
- robots/terms/route constraints do not support repeatable automation;
- only a curated or transformed copy exists while the original source contract is unclear;
- the data exposes names but no stable identity anchor;
- fields contain unnecessary private information;
- a packet can support human-reviewed research but cannot justify automated L3 collection.

Where appropriate, a rights-approved **finite human-assisted packet** may still support L1/L2 work.
That does not silently promote the source to L3.

## 10. Operator and approval architecture

The private operator surface is a control plane over canonical data, not a second database.

```text
canonical DB
   ↓ read-only/revalidated review projection
operator console
   ↓
human decision
   ↓
reviewed manifest / signed or hashed receipt
   ↓
fresh transaction-time revalidation
   ↓
explicit bounded commit
```
Important properties:

- review screens do not imply approval;
- stale artifacts fail closed instead of being treated as current state;
- write-capable admin operations use explicit previews/revalidation/receipts;
- the public API never inherits private operator authority;
- source collection, Organization materialization, identity resolution and Claim publication remain
  separate operations.

See [Operator Console](../operations/OPERATOR_CONSOLE.md) and
[Admin operations](ADMIN_OPERATIONS.md).

## 11. Repository structure

| Path | Responsibility |
|---|---|
| `packages/domain/` | Canonical Pydantic contracts and enums; semantic authority. |
| `packages/connectors/` | Source-specific acquisition/parsing adapters. |
| `packages/verification/` | Deterministic source/domain validation and publication checks. |
| `packages/application/` | Use-case services, repository/UoW ports and API read projections. |
| `packages/persistence/` | Canonical engine/UoW, session-bound SQLAlchemy adapters, row mappings and reviewed persistence paths. |
| `workers/` | Bounded collection, enumeration, review preparation and materialization entry points. |
| `packages/rendering/` | Evidence-backed public and derived read-model construction. |
| `apps/api/` | FastAPI public/private read boundaries and operator endpoints. |
| `apps/web/` | Next.js public site and private operator UI. |
| `migrations/` | Alembic-only persistence schema evolution. |
| `tests/` | Golden, unit, integration, migration, API and source-contract regression coverage. |
| `docs/architecture/` | Canonical technical/source contracts. |
| `docs/product/` | Product direction and current scope. |
| `docs/exec-plans/` | Active, completed and blocked implementation/source-gate evidence. |
| `docs/operations/` | Runtime, deployment and operator procedures. |

## 12. Verification model

A claim that something “works” must identify the layer proven.

- unit/integration tests prove code semantics;
- Golden Set proves canonical evidence-quality invariants;
- migration tests prove schema evolution;
- PostgreSQL load/read tests prove database support;
- backup/restore proves operational recoverability;
- browser QA proves rendered behavior;
- GitHub CI proves the committed revision;
- deployment smoke proves the deployed revision.
A build is not browser verification. Local runtime is not CI. CI is not deployment.

The normal milestone gate is:

```text
targeted tests
→ make verify
→ final diff review
→ coherent commit
→ GitHub CI
→ operational/deployment verification when claimed
```

See [Definition of done](../workflows/DEFINITION_OF_DONE.md) and
[Change control](../workflows/CHANGE_CONTROL.md).

## 13. Architectural decisions that prevent overfitting

The project intentionally avoids two opposite failures.

### Failure A — source-specific copy/paste everywhere

When two implementations prove the same invariant, shared execution machinery may be extracted.
Example: ALIO and NEC source-context Person materializers now share only their proven persistence
seam while retaining source-specific eligibility and Claim semantics.

### Failure B — premature generic framework

The project does not introduce a generic ingestion, event, analytics or orchestration framework
before concrete sources prove the abstraction. Source-specific correction, identity and field
semantics remain explicit.

The same rule applies to Derived Intelligence: Assembly CHANGE and ALIO MONEY share a common
evidence trace, not a generic “compare anything” engine.

## 14. Current conclusion

The project is past the stage of proving whether an evidence-first architecture can work.

It has now demonstrated:

- canonical provenance and publication gates;
- multiple full-enumeration official-source lanes;
- deterministic source-context materialization;
- Organization-scoped Claim/Evidence;
- public Person/Organization evidence surfaces;
- source-neutral evidence tracing across two Derived Intelligence domains;
- a private, current-state operator review surface;
- PostgreSQL migration, backup/restore, CI and standalone web verification.
The project has **not** demonstrated complete national coverage of every desired source.

The current bottleneck is not “scrape more data.” It is:

1. review the 41 Gukgam existing-Organization occurrences;
2. independently review the 70 MOIS Organization proposals;
3. produce reviewed manifests only from explicit human decisions;
4. commit only after fresh no-write preflight/revalidation;
5. reassess the remaining 159 unmatched Gukgam labels;
6. only then choose the next acquisition expansion, such as an L3 ALIO Item 12 universe or a
   previously blocked source whose gate can actually be reopened.

This ordering preserves the purpose of Civic Intel: more coverage is useful only when it remains
traceable, reviewable and semantically correct.

## 15. Recommended reading order

For a new engineer or agent:

1. this overview;
2. [ARCHITECTURE.md](../../ARCHITECTURE.md);
3. [Civic Intel North Star](../product/CIVIC_INTEL_NORTH_STAR.md);
4. [V0 scope](../product/V0_SCOPE.md);
5. [Feeder source coverage](FEEDER_SOURCE_COVERAGE.md);
6. [Identity resolution](IDENTITY_RESOLUTION.md);
7. [Batch ingestion](BATCH_INGESTION.md);
8. [Source parsing and semantics](SOURCE_PARSING_AND_SEMANTICS.md);
9. [Operator Console](../operations/OPERATOR_CONSOLE.md);
10. [HANDOFF.md](../../HANDOFF.md);
11. the one active execution plan and any source-specific blocked plan relevant to the task.

The repository should be read from **purpose → architecture → source gate → current evidence → next
bounded action**, not from the latest worker or UI file backward.

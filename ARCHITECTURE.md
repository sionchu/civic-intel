# Architecture

For a single end-to-end orientation covering purpose, architecture, source gates, current collection
coverage and the present review boundary, start with
[System Overview](docs/architecture/CIVIC_INTEL_SYSTEM_OVERVIEW.md). This file remains the governing
architecture boundary.

Long-term product direction and the Evidence Core / Derived Intelligence / Product boundary
are defined in [Civic Intel North Star](docs/product/CIVIC_INTEL_NORTH_STAR.md). Future analysis
and access layers consume this architecture; they do not alter current canonical contracts or gates.

## Authority and dependency direction

`packages.domain` owns framework-independent contracts and enums. `packages.application`
defines repository/UoW ports and use-case orchestration; its current services cover acquisition,
administration, identity, onboarding, Organizations, profiles, public reads and review. Verification
and rendering remain explicit collaborators rather than ORM concerns.

`packages.persistence.models` owns SQLAlchemy rows and `mapping.py` translates rows to/from domain
contracts. Session-bound adapters are grouped by capability in `acquisition.py`, `administration.py`,
`identity.py`, `onboarding.py`, `organizations.py`, `profiles.py`, `public.py` and `review.py`.
`Database` and `SqlAlchemyUnitOfWork` in `packages/persistence/database.py` own the engine/session
factory and compose those adapters on one session. They implement the ports defined by
`packages/application/ports.py`; this adapter-to-port dependency is the boundary inversion, not a
second session/repository implementation.

The runtime call path is API or worker composition → application service/use case → UoW port →
session-bound persistence adapter. The API opens one read UoW per public request and gives that
snapshot to `DirectoryView`; operator commands use the Administration service. Workers compose
their source-specific connector/enumerator with `IngestionPipeline`, `SourceLifecycle` and the
shared acquisition service. They keep coverage, cursor and parser rules source-specific. See
[`Application`](packages/application/context.py), [UoW ports](packages/application/ports.py) and
[`Database` / `SqlAlchemyUnitOfWork`](packages/persistence/database.py).

Application use cases own transaction boundaries and call `commit()` only after validation and
all related writes succeed. A UoW context closes the session and rolls back any uncommitted work.
Read UoWs enforce no-write behavior and use a coherent read transaction; SQLite writes begin with
`BEGIN IMMEDIATE`, while admin operations retain their database-specific locking and state
revalidation. Source-page records and checkpoint advancement commit atomically. Admin mutations,
append-only receipts, replay detection and signed-preview revalidation remain one transaction.

Pydantic contracts define canonical semantics; SQLAlchemy rows persist them; Alembic is the only
schema creation/change path. Runtime readiness accepts declared reader-compatible revisions
`0006`, `0007` and `0008` (expected head `0008`); startup does not call `create_all()` or seed
Golden Set 001. Golden seeding remains an explicit disposable development/test operation against
an empty migrated database. API and workers use the same UoW/session implementation; FastAPI never
reads module-level fixture dictionaries.

## Evidence and publication

Publication is a visibility decision (`PublicationStatus`). Truth posture is expressed
separately by `EpistemicStatus` and `asserted_as_true`. FACT requires explicit assertion
and supporting evidence. UNKNOWN may be PUBLISHED only as a non-asserted unresolved result
with a resolution note.

Every rendered factual item must traverse Claim, ClaimEvidence, Source, and SourcePolicy.
`Claim` targets exactly one canonical Person or current Organization; the ClaimEvidence and
source-policy/provenance gates are shared. Person profile routes remain person-scoped.
Origin clusters determine independent-source counts. SUPPORT and REFUTE remain distinct.
Decision episodes may be rendered only when they explicitly reference a published Claim and
its ClaimEvidence; legacy or incomplete episode records stay out of the public projection.
Review-only identity and source-operational metadata are not public data. The API review surface
is disabled by default. The private local-OS operator factory supports explicit token-gated
admin commands with signed previews, transaction revalidation and append-only receipts; public
callers never inherit that authority. See [Admin operations](docs/architecture/ADMIN_OPERATIONS.md).

Anonymous Source reads are reachability-scoped: a Source is public only when a current publishable
Claim/Evidence path on a public eligible Person or Organization reaches it. The public Source DTO
is an allowlist and never serializes the complete SourcePolicy. Public read failures distinguish
missing records, insufficient eligible inputs, source-version conflict and service failure;
transport failure is not an `UNKNOWN` Claim.

The canonical `apps/web` has two locally verified runtime artifact contracts. Next standalone
contains its server, generated `.next/static` tree and optional `public` directory. The local
Worker contains the ESM fetch entry in `dist/server` and assets in `dist/client`; it rejects
admin paths and non-GET/HEAD requests before dispatch. Next and Worker builds run serially
because they share generated type inputs. Artifact verification fails closed when required
runtime parts are absent; compilation alone does not establish runtime or browser acceptance.
Sites metadata packaging requires the real registered hosting manifest. Packaging, cloud-to-Mac
connectivity and deployment remain pending; the [local Worker receipt](docs/receipts/gukgam-worker-build-20261003.json)
records only local synthetic HTTP verification.

## Deployment, public access and cost gates

Runtime architecture, deployment topology, public exposure and search indexing are separate
decisions. Creating production services or domains may create billable resources and requires
explicit owner approval after a read-only plan review. Public Web exposure and indexing are also
separate approval steps; API and PostgreSQL remain private. A provider API marked free or reusable
does not authorize a request, credential acquisition, infrastructure spend, retention or
redistribution. See [Evidence Preview deployment preparation](docs/operations/EVIDENCE_PREVIEW_DEPLOYMENT.md)
and the current
[Gukgam research and public-gate plan](docs/exec-plans/active/gukgam-2026-ontology-research.md).

## Temporal and analysis model

Material records carry valid time (`valid_from`, `valid_to`) and system time
(`recorded_at`, `superseded_at`). Decision episodes carry action, target, outcome, and
independent origin IDs. Strong relationships require typed evidence. Hypotheses encode
an explicit H0/H1/H2 matrix plus an ordinary explanation and falsifier.

## Collection boundary

Workers may normalize policy-approved input and create snapshots. They cannot publish.
Golden tests use manually reviewed offline excerpts; no live connector, crawler, or raw
search-result ingestion participates in Golden Set 001.

Live-capable connectors are opt-in and source-specific. They must have an explicit reviewed
SourcePolicy before `IngestionPipeline` can fetch. Credentials stay outside discovered
source URLs and persisted metadata. The National Assembly member connector intentionally
retains metadata only, not raw response fulltext, because the provider rows may contain
contact fields that are unnecessary for identity resolution.

Cross-source hierarchy, typed source-record parsing, normalization, locator and revision
semantics are defined in [Source parsing and semantics](docs/architecture/SOURCE_PARSING_AND_SEMANTICS.md).
The document is a boundary reference for future source-specific work; it does not add a live
source/feeder, parser framework or persistent model. A narrow source-specific parser may be used
for a bounded reviewed packet without changing the L3 boundary.

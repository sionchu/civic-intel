# Architecture

Long-term product direction and the Evidence Core / Derived Intelligence / Product boundary
are defined in [Civic Intel North Star](docs/product/CIVIC_INTEL_NORTH_STAR.md). Future analysis
and access layers consume this architecture; they do not alter current canonical contracts or gates.

## Authority and dependency direction

`packages/domain → packages/verification + packages/connectors → packages/persistence + workers → apps/api → apps/web`

Pydantic contracts define canonical semantics. SQLAlchemy rows persist those contracts;
Alembic is the only schema creation/change path. API and workers share the single
`packages.persistence.SqlAlchemyRepository`; FastAPI never reads module-level fixture
dictionaries. Normal runtime startup
only verifies that the configured database is at the current Alembic head. It does not
call `create_all()` and does not seed Golden Set 001. Golden seeding is an explicit,
disposable development/test operation against an empty migrated database.

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
is disabled by default because V0 has no authenticated operator boundary; test/internal callers
must opt in explicitly.

Anonymous Source reads are reachability-scoped: a Source is public only when a current publishable
Claim/Evidence path on a public eligible Person or Organization reaches it. The public Source DTO
is an allowlist and never serializes the complete SourcePolicy. Public read failures distinguish
missing records, insufficient eligible inputs, source-version conflict and service failure;
transport failure is not an `UNKNOWN` Claim.

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

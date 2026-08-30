# Architecture

## Authority and dependency direction

`packages/domain → packages/verification + packages/connectors → workers + apps/api → apps/web`

Pydantic contracts define canonical semantics. SQLAlchemy rows persist those contracts;
Alembic is the only schema-change path. FastAPI reads through `SqlAlchemyRepository`,
never module-level fixture dictionaries. Golden Set 001 seeds a database for deterministic
offline development, but the database remains the runtime source of truth.

## Evidence and publication

Publication is a visibility decision (`PublicationStatus`). Truth posture is expressed
separately by `EpistemicStatus` and `asserted_as_true`. FACT requires explicit assertion
and supporting evidence. UNKNOWN may be PUBLISHED only as a non-asserted unresolved result
with a resolution note.

Every rendered factual item must traverse Claim, ClaimEvidence, Source, and SourcePolicy.
Origin clusters determine independent-source counts. SUPPORT and REFUTE remain distinct.

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

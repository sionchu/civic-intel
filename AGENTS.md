# Repository instructions

Read `ARCHITECTURE.md`, `docs/INDEX.md`, `docs/product/V0_SCOPE.md`,
the architecture documents governing the touched feeder/identity path, the role file
matching the work, `docs/workflows/CHANGE_CONTROL.md`,
`docs/workflows/DEFINITION_OF_DONE.md`, and any active execution plan before changing
behavior.

For web UI changes, read the root `DESIGN.md` first and treat its semantic tokens and existing
components as the visual contract.

For batch/full-enumeration work also read:

- `docs/architecture/BATCH_INGESTION.md`
- `docs/architecture/FEEDER_SOURCE_COVERAGE.md`
- `docs/architecture/IDENTITY_RESOLUTION.md`
- `.agents/skills/batch-ingestion-foundation/SKILL.md`

## Non-negotiable invariants

- Preserve `rendered item → Claim → ClaimEvidence → Source → SourcePolicy`.
- Displayability and truth assertion are separate. A published UNKNOWN is an explicit
  unresolved result and must never be promoted to FACT.
- Every source-processing path starts with SourcePolicy. Technical access is not permission.
- Generic or unbounded crawling is prohibited. SourcePolicy-approved, source-bounded full
  enumeration of an official API or structured disclosure is allowed when the governing
  product/source documents permit it.
- `SourceSnapshot` is the canonical source-level capture. Do not add a second raw-payload
  truth store. Record-level feeder observations must retain only policy-permitted normalized
  fields plus exact snapshot provenance.
- Credentials, private contact fields, unnecessary addresses and provider secrets must never
  enter Source URLs, snapshots, observations, checkpoints, run receipts or error summaries.
- Identity-specific output requires a resolved identity, but a research-level identity
  resolution is not automatically permission to merge canonical Persons.
- Name-only, organizational proximity, co-mention, numeric scores, fuzzy similarity and
  embeddings cannot authorize automatic Person merges.
- In the batch path, authoritative provider identifiers may support narrowly defined
  AUTO_CREATE/AUTO_LINK rules. Ambiguous or cross-lane cases fail closed to review.
- Workers may collect/normalize and request verified materialization; they may not bypass
  Claim/Evidence publication gates.
- Checkpoints advance only with committed source/snapshot/observation data.
- Do not model private-family discovery or precise residence in publishable contracts.

## Statement and curated-source ingestion

- Treat partisan, advocacy, media, research and other curated compilations as discovery sources
  unless their reviewed `SourcePolicy` and field authority explicitly permit stronger use. They may
  nominate statement candidates; they do not by themselves establish a canonical position,
  contradiction, wrongdoing or truth claim.
- Prefer deterministic extraction from structured/native text and layout-aware parsing before OCR
  or model-assisted extraction. For PDFs preserve exact document, page, section/table and column or
  side locators. OCR is a candidate transcription when no reliable text layer exists, not source
  truth.
- Separate seed extraction from source verification: discovery candidate -> locate the primary or
  original source -> capture `SourceSnapshot` -> persist a policy-minimized `FeederObservation` ->
  resolve identity -> pass the normal Claim/ClaimEvidence publication gate. If the primary source
  cannot be verified, keep the item discovery/review-only.
- Preserve exact quote boundaries, source-reported date, role/context, source URL or attachment
  locator, and parser/normalization revision. Never guess or synthesize missing quote text, dates,
  sources, identities or provenance.
- Model assistance is advisory only for context summaries, topic suggestions, quote-boundary
  proposals and related-statement retrieval/reranking. It cannot generate quotation text, repair
  missing provenance, authorize a Person merge, or label a statement as a lie, flip-flop or
  contradiction.
- A source-provided taxonomy may be retained as source-scoped metadata, but it is not automatically
  a canonical Civic Intel taxonomy. Related statements may be grouped by explicit topic/evidence;
  relations such as clarifies, qualifies, supersedes or potentially contrasts remain derived and
  reviewable, and fail closed to UNKNOWN when evidence is insufficient.

## Canonical persistence rules

- Pydantic contracts own semantics; SQLAlchemy rows persist them; Alembic is the only schema
  creation/change path.
- Reuse `SourcePolicy`, `Source` and `SourceSnapshot` for batch ingestion.
- Before adding a table, class or repository, search for a semantic equivalent.
- Keep one canonical SQLAlchemy repository/session implementation shared by API and workers;
  do not create parallel persistence logic.
- Every persistence change requires a forward and reversible Alembic migration plus
  deterministic regression coverage.
- Runtime startup verifies schema head; it does not create tables or auto-migrate.

## Change discipline

- Extend canonical contracts in place; never add `v2`, `new`, `final` or parallel alternatives.
- Prefer the smallest coherent vertical slice that proves the next maturity level.
- Do not introduce generic orchestration frameworks before two concrete source implementations
  demonstrate the common abstraction.
- Do not add Temporal, Airflow, Celery, Kafka, Kubernetes, Splink, a vector database, a graph
  database or MCP merely because they may be useful later.
- Keep existing Golden Set and reviewed-person regressions intact unless the governing change
  explicitly requires updating their semantics.
- `ReviewedPersonBundle` remains a manual/regression/exception path; it is not the required
  normal path for every batch-discovered Person.
- Run narrow checks while working and `make verify` before milestone completion.
- For schema changes run an Alembic upgrade/downgrade/upgrade round trip.
- Re-read the final diff and remove dead helpers, duplicate semantics, obsolete paths and
  documentation drift.

Release plans may defer otherwise valid product capabilities. Treat those exclusions as scoped
to the named release, not as permanent architecture prohibitions. Any later implementation still
requires its own approved plan and the same source, identity, privacy, migration and publication
gates.

## Long-running agent behavior

For an approved multi-milestone execution plan:

1. verify current HEAD and baseline;
2. implement one coherent milestone;
3. run targeted checks and full verification;
4. inspect the diff;
5. make a coherent commit;
6. update the active execution plan with evidence;
7. continue to the next planned milestone without asking for routine confirmation.

Stop and request user action only for meaningful cost, destructive data loss, ownership
transfer, weaker security/public access, secret exposure, or unresolved source-rights
questions that block safe implementation.

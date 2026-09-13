# ALIO Item 12 Claim-backed MONEY projection v0

Status: completed on 2026-09-14.

## Objective

Expose the smallest read-only ALIO Item 12 MONEY result that is downstream of the canonical
organization Claim/Evidence publication path. The result must consume published annual
organization Claims, exact ClaimEvidence and the repository-complete immutable observation set;
the bounded worker remains observation-only.

## Baseline and boundaries

- Baseline and remote `master`: `f982900ad931ec41d3a23bc9001c84cb9e504cc8`.
- Reuse `Claim`, `ClaimEvidence`, `SourcePolicy`, `Source`, `SourceSnapshot` and
  `FeederObservation`; add no table, migration, generic money model or parallel evidence store.
- Use only the source-specific `DISCLOSED_BUSINESS_EXPENSE` / ALIO Item 12 contract. A provider
  `apbaId` remains source-scoped context and never becomes a canonical Organization ID.
- Do not add automatic ALIO-to-Organization binding, organization enumeration, scheduled sync,
  raw report/attachment storage, Person materialization or a generic `/money` route.

## Contract

- The projection accepts only current published FACT organization Claims with one exact SUPPORT
  ClaimEvidence item and an observation-backed `SourceSnapshot → Source → SourcePolicy` chain.
- Claim qualifiers, subject text and amount text must match the normalized observation; the
  projection does not treat Claim text as a second source of numeric truth.
- The caller supplies all immutable observation versions for each referenced
  `(feeder, scope_key, provider_record_key)`. More than one content hash fails closed; the code
  does not call a changed value a correction or select a latest version.
- The public route is
  `GET /organizations/{organization_id}/money?earlier_fiscal_year=...&later_fiscal_year=...`.
  It returns a derived read result with both Claim IDs and selected source/snapshot/observation
  provenance. It returns no result when the organization has no eligible published Claims.
- The result is not a Claim or FACT and is not an allegation about personal spending, waste,
  corruption, causation, performance or peer superiority.

## Acceptance criteria

- A two-year reviewed Organization Claim fixture produces the deterministic Item 12 comparison
  through the API route and preserves both Claim IDs plus exact provenance.
- Missing, mismatched, non-published, non-current, non-FACT, multi-evidence, non-SUPPORT,
  excerpt-bearing, source/snapshot-mismatched or qualifier-divergent inputs fail closed.
- Multiple immutable content hashes for one referenced provider record key fail closed.
- Existing observation-only MONEY output remains `BLOCKED` and cannot be used by the route.
- Existing Person Claim/Evidence behavior and all project verification gates remain intact.

## Implementation

- Added `build_alio_head_expense_money_from_claims()` as a source-specific read-model builder;
  it reuses the existing Item 12 validation and percentage-delta semantics without adding a
  persistent financial model.
- Added `GET /organizations/{organization_id}/money` with explicit fiscal-year query parameters.
  The route loads only current published organization Claims and their evidence, then expands the
  referenced observation keys to the complete repository version set before projection.
- Preserved the observation-only builder as `publication_status: BLOCKED`; the new result is a
  derived read result with `epistemic_status: null`, both Claim IDs, serialized ClaimEvidence and
  source/snapshot/observation provenance.
- Updated the organization Claim, Item 12 feeder, source-semantics, North Star, index and
  handoff documentation. No migration or persistent model changed.

## Verification evidence

- Targeted Item 12 regression: `20 passed, 2 warnings`.
- Full Python suite: `316 passed, 4 warnings`.
- Ruff `apps packages workers tests migrations`: passed.
- mypy `packages workers apps/api`: success for 55 source files.
- Golden quality checks: all checks true.
- Web lint, typecheck, test (`5 passed`) and production build: passed.
- Markdown check: 56 repository Markdown files, 73 relative links, 0 broken links.
- `git diff --check`: passed. `make verify` was attempted but `make` is unavailable on this
  Windows host; its constituent commands passed directly.

## Maturity decision and not executed

The projection contract is complete, but ALIO Item 12 remains `L2 SINGLE_PULL` for the three
known-positive institution observation proof. This milestone does not promote the feeder to L3,
enumerate the full directory, bind `apbaId` automatically, run scheduled sync or publish live
annual organization Claims. Without a reviewed canonical Organization binding and imported annual
Claims, the public route returns no MONEY result.

## Next concrete action

Authorize one manually reviewed ALIO `apbaId` to existing-Organization binding and import exactly
two annual Item 12 Claims through the canonical importer before exercising the route with live
data.

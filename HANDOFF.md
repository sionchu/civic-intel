# HANDOFF

## Objective

Complete Evidence Directory v0 as a read-only product surface over Civic Intel's existing
evidence-first contracts. Keep OpenWatch and future feeder expansion out of this milestone.

## Scope

Public resolved-person roster, evidence-backed person profile, explicit epistemic/stance/conflict
rendering, source-policy audit projection, and a separate read-only identity review surface.
Reuse the existing `Person -> Claim -> ClaimEvidence -> Source -> SourcePolicy` path and, when
present, `ClaimEvidence -> FeederObservation -> SourceSnapshot -> Source` provenance. No schema,
migration, feeder, search infrastructure, or new persistence abstraction.

## Acceptance criteria

- Public `/people` and person-related public routes expose only current `RESOLVED` identities.
- Profile sections keep `AVAILABLE`/`PARTIAL`/`UNKNOWN`; claims show existing epistemic status and
  evidence stance without inventing truth, confidence, or scoring semantics.
- A claim containing both `SUPPORT` and `REFUTE` is visibly marked `SOURCE CONFLICT` without
  downgrading or deleting the claim.
- Profile and source cards expose human-readable provenance/policy summaries while placing UUIDs
  and snapshot/observation references in audit details.
- `/admin/review` is read-only and exposes existing review actions, observations, candidates and
  source/snapshot provenance without normalized payload or fulltext leakage.
- Existing Golden Set, batch materialization and reviewed-person behavior remains intact.

## Completed

- Confirmed baseline before implementation: `master` and `origin/master` both at
  `f8b36706103d6562252b730ee8d7892c539e7ddd`; the worktree was clean.
- Read the repository governing documents, active execution plans, public-official-profiler and
  batch-ingestion guidance, then inspected the actual domain contracts, SQLAlchemy repository,
  profile projection, API, web app and regression fixtures.
- Added repository read helpers for current public people, a single feeder observation and its
  source snapshot; no model/table/migration was added.
- Added the public API boundary that filters `RESOLVED` and non-superseded people and returns 404
  for unresolved/review identities on person, claims, relationships and assets routes.
- Extended the existing profile projection and claim payload with evidence stance plus exact
  snapshot/feeder-observation references and a derived support/refute conflict marker.
- Added a source-policy summary projection for source cards and preserved the canonical raw
  `SourcePolicy` response for audit compatibility.
- Added `/admin/review` read-only projections over existing `IdentityReviewItem`,
  `FeederObservation`, `SourceSnapshot` and `Source` records. No approval, merge or publication
  action is available.
- Updated the Next.js roster/profile UI and added the read-only review route. Main content uses
  names, labels and source titles; UUIDs and hashes are behind audit details. No OpenWatch data or
  new unsupported asset/vote/score UI was added.
- Added deterministic API and UI regressions for identity filtering, epistemic/provenance trace,
  conflict visibility, review actions, payload minimization and directory scope.
- Connected the migrated Golden fixture database to the local FastAPI and Next.js development
  servers and manually inspected the roster, resolved profile, conflict profile, populated review
  queue and blocked review-identity route in the in-app browser. Temporary review observations,
  identities, servers and database were removed after inspection.

## Current checkpoint

Implementation is complete in the working tree and all direct verification commands pass. The
only runner limitation is that GNU Make is unavailable on this Windows host, so the Makefile's
constituent commands were executed directly. The seven existing L3 feeders and the blocked MPM,
National Assembly asset, CleanEye and roll-call source gates are unchanged.

## Decisions and reasons

- `public_people()` is the API/read-side boundary; the web page does not merely hide unresolved
  identities.
- Existing profile projection and publication validation remain canonical. `source_conflict` is a
  derived read-model flag from existing evidence stances, not a new epistemic or database field.
- Source cards expose a compact policy summary; raw policy fields remain available from the
  existing source endpoint and are shown only in audit-oriented detail where appropriate.
- Review items expose identifiers and provenance needed for human review but deliberately omit
  `FeederObservation.normalized`, source snapshot metadata and fulltext from the review payload.
- No `ReviewedPersonBundle` main path, generic evidence graph, shadow review model, provider
  ingestion, OpenWatch integration or dependency was introduced.

## Verification evidence

Executed locally on 2026-09-12:

- `.venv\Scripts\python.exe -m pytest -o addopts='' tests/test_api.py tests/test_profile_projection.py -q`:
  17 passed, 2 warnings.
- `.venv\Scripts\python.exe -m pytest -o addopts='' --disable-warnings`: 269 passed.
- `.venv\Scripts\python.exe -m ruff check apps packages workers tests`: passed.
- `.venv\Scripts\python.exe -m mypy packages workers apps/api`: success, 51 source files.
- `.venv\Scripts\python.exe -m packages.verification.quality`: passed=true; all Golden Set
  checks passed.
- `npm --prefix apps/web run lint`: passed.
- `npm --prefix apps/web run typecheck`: passed.
- `npm --prefix apps/web test`: 4 passed.
- `npm --prefix apps/web run build`: passed; `/`, `/admin/review` and `/people/[id]` built.
- Temporary-database Alembic `upgrade head -> downgrade -1 -> upgrade head`: passed.
- Connected runtime smoke review: API returned the Golden roster, a 12-section resolved profile,
  and populated `REVIEW_REQUIRED`/`HARD_CONFLICT` review items with source provenance; the public
  roster omitted inserted `REVIEW`/`UNRESOLVED` identities and their profile routes returned 404.
  Browser inspection showed `SOURCE CONFLICT` with both `SUPPORT` and `REFUTE`, compact policy
  summaries, collapsed audit details and no approval/merge/publish controls.
- Temporary runtime cleanup: `.tmp-evidence-directory.db` and sidecar files removed; local API/Web
  development servers stopped.
- `git diff --check`: passed before final documentation update; rerun after commit staging.
- `make verify`: runner-unavailable because GNU Make is not installed; every constituent command
  was run directly. No GitHub Actions result was claimed locally.

## Not executed

No feeder implementation, OpenWatch acquisition, asset/vote/ideology/graph/search feature, raw
provider payload browser, schema change, migration file, dependency install, admin write action or
production deployment was performed.

## Blockers

None for Evidence Directory v0 implementation. Existing source-gate maturity decisions remain
unchanged: MPM is L1 CONTRACT_STAGED with L3 blocked; National Assembly asset disclosure and
CleanEye remain L0 RESEARCHED; BLOCKED. Those lanes require their own source-contract evidence
before any promotion.

## Modified files

- `apps/api/main.py`
- `apps/web/app/admin/review/page.tsx`
- `apps/web/app/data.ts`
- `apps/web/app/layout.tsx`
- `apps/web/app/page.tsx`
- `apps/web/app/people/[id]/page.tsx`
- `apps/web/app/styles.css`
- `apps/web/app/types.ts`
- `apps/web/tests/ui.test.mjs`
- `packages/persistence/repository.py`
- `packages/rendering/profile_projection.py`
- `tests/test_api.py`
- `HANDOFF.md`

## Next concrete action

Request an independent review of the Evidence Directory v0 read surface and the next source-gate
milestone before implementing another feeder.

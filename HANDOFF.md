# HANDOFF

## Objective

Complete Evidence Directory v0 as a read-only product surface over Civic Intel's existing
evidence-first contracts. Keep OpenWatch and future feeder expansion out of this milestone.

## Scope

Public resolved-person roster, evidence-backed person profile, explicit epistemic/stance/conflict
rendering, source-policy audit projection, and a separate read-only identity review surface that
is unavailable from the public API unless an internal/test caller explicitly enables it.
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
- An explicitly enabled internal `/admin/review` surface is read-only and exposes existing review
  actions, observations, candidates and source/snapshot provenance without normalized payload or
  fulltext leakage; the public API does not register this route by default.
- Decision episodes are public only when linked to a published Claim and its ClaimEvidence; legacy
  or incomplete episode rows fail closed instead of being rendered as FACT.
- Public claim, relationship and episode reads exclude superseded temporal rows.
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
- Completed an independent read-only review and hardened the three findings: unlinked decision
  episodes no longer bypass Claim/Evidence, the review route is disabled by default and no longer
  linked from public navigation, and superseded public temporal records are filtered out.
- Connected the migrated Golden fixture database to the local FastAPI and Next.js development
  servers and manually inspected the roster, resolved profile, conflict profile, populated review
  queue and blocked review-identity route in the in-app browser. Temporary review observations,
  identities, servers and database were removed after inspection.

## Current checkpoint

Evidence Directory v0 and its post-review hardening are complete in the working tree and all
direct verification commands pass. The only runner limitation is that GNU Make is unavailable on
this Windows host, so the Makefile's constituent commands were executed directly. The seven
existing L3 feeders and the blocked MPM, National Assembly asset, CleanEye and roll-call source
gates are unchanged. The 2026-09-12 official MPM revalidation confirmed 125 mixed `취업` board
posts over 9 pages, 405 mixed ethics-board posts over 27 pages, bundled historical PDF posts,
and no published row identity, correction/version or attachment reuse contract. MPM remains
`L1 CONTRACT_STAGED; L3 promotion blocked`.
The same-day National Assembly revalidation found a page-based Gazette catalog with 61 `재산`
matches across 7 pages and current 2026-54, 2025-51, 2024-107 and 2024-36 publication entries.
That confirms publication-level origin candidates only; asset disclosure/item keys,
correction/republication semantics, complete curated-to-origin reconciliation and a permitted
automated route remain unresolved. The asset lane remains `L0 RESEARCHED; BLOCKED`.
The 2026-09-12 Presidential Office route review found a 923-item briefing index with bounded
search/page navigation and stable-looking detail IDs, but no typed personnel universe,
action-level version contract or blanket reuse permission. The inspected detail page also rendered
the page-level KOGL type 4 notice (attribution, noncommercial use, no modification), which does
not by itself authorize Civic Intel fulltext retention, derivative normalization, automated
enumeration or commercial republication. The same page contains ten action subjects in one
narrative and no row-level action keys, so a reviewed ordinal would remain snapshot-scoped only.
Presidential personnel remains `L1 CONTRACT_STAGED`; live collection is disabled pending route-
and rights-specific approval.
The first follow-on cross-lane case is now fixed as a research-only fixture: the same official
briefing explicitly pairs 이원주의 current 기후에너지환경부 에너지전환정책실장 role with the
planned 메가프로젝트 보좌관 designation. The case reuses the existing profile-target and
cross-lane identity contracts, preserves the exact briefing reference on both observations, and
does not create a Person, CareerEpisode or publishable FACT.
The 2026-09-12 labor source-contract gate then evaluated 민주노총 current/history leadership pages,
경사노위 structure and dated committee posts/attachments, and the fragmented 한국노총 official
footprint as independent lanes. The aggregate labor standard-data path remains
`L1 CONTRACT_STAGED`; the federation/commission lanes remain `L0 RESEARCHED` or
`DISCOVERY_ONLY` with no stable universal roster, row identity, correction/version or reuse
contract sufficient for L3. A finite, rights-approved source packet may still support human-
assisted staging under the playbook.
The same-day MOJ/Supreme Court gate evaluated official prosecutor personnel releases, Court
Gazette issue tables and a later Gazette correction entry. Both legal lanes remain
`L1 CONTRACT_STAGED`: a rights-approved single release/issue packet can support human-reviewed
L2 staging, but neither route exposes a unified complete personnel universe, row-level Person key
or sufficient automated coverage contract for L3.
The first MOJ packet preflight identified post `602956` with six attachment references (`490100`–
`490105`) and a page-level `공공누리 2유형` label. Because the current MOJ policy still denies
fetch and the exact attachment/third-party-rights boundary is not represented, no attachment was
downloaded, normalized or stored; the legal lane remains L1 and L2 is not claimed.

## Decisions and reasons

- `public_people()` is the API/read-side boundary; the web page does not merely hide unresolved
  identities.
- Existing profile projection and publication validation remain canonical. `source_conflict` is a
  derived read-model flag from existing evidence stances, not a new epistemic or database field.
- Source cards expose a compact policy summary; raw policy fields remain available from the
  existing source endpoint and are shown only in audit-oriented detail where appropriate.
- Review items expose identifiers and provenance needed for human review but deliberately omit
  `FeederObservation.normalized`, source snapshot metadata and fulltext from the review payload.
- V0 has no authenticated operator boundary, so `create_app()` does not register `/admin/review`
  unless the caller explicitly opts into the internal/test surface; public navigation does not
  advertise it.
- A decision episode's raw `source_ids` are not sufficient publication evidence. Its projection
  derives evidence and source IDs from an explicitly linked published Claim and ClaimEvidence.
- Public temporal reads use non-superseded claims, relationships and decision episodes; historical
  rows remain persistence data rather than current public profile content.
- No `ReviewedPersonBundle` main path, generic evidence graph, shadow review model, provider
  ingestion, OpenWatch integration or dependency was introduced.
- Labor federation, social-dialogue and affiliate pages are separate source lanes. `record_id`,
  page/post IDs and local crosswalk keys are not canonical Person authority; official identity
  anchors remain primary and name-only linking is prohibited.
- The labor source gate uses the existing `Claim`/`ClaimEvidence` and
  `CommitteeMembershipEpisode` semantics if a future lane closes. It does not assume or add a
  `LaborLeadershipEpisode`, generic roster schema, crawler or packet importer.
- MOJ and Supreme Court personnel remain independent source lanes. Release/attachment IDs and
  Gazette issue/order/row locators identify packets, not Persons; Court Gazette corrections must
  become explicit immutable observation versions.
- The MOJ packet candidate is a manifest-only preflight. A page-level KOGL type-2 label is not
  treated as blanket permission for attachment retention, production fetching or redistribution;
  the existing `SourcePolicy` gate remains authoritative.

## Verification evidence

Executed locally on 2026-09-12:

- `.venv\Scripts\python.exe -m pytest -o addopts='' tests/test_api.py tests/test_profile_projection.py -q`:
  21 passed, 2 warnings.
- `.venv\Scripts\python.exe -m pytest -o addopts='' --disable-warnings`: 276 passed after
  hardening.
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
- Independent Sol review completed read-only; it identified one provenance bypass and two public
  exposure/temporal-read risks, all rechecked against the repository and covered by the hardening
  tests.
- Re-opened the official MPM filtered/full board, historical page, current result detail and
  copyright-policy pages; the source-contract decision remained blocked and no MPM bytes, rows,
  connector, importer or runtime dependency were added.
- Re-opened the official National Assembly Gazette index with the `재산` title filter and
  inspected the publication pagination, dates, preview/download controls and recent origin
  candidates; no asset row or raw Gazette file was retained.
- Re-opened the official Presidential Office briefing list, title-filtered personnel searches,
  a multi-action detail page, the organization page and the copyright-policy page; the detail page
  visibly rendered the KOGL type 4 notice, and no live page body or raw provider payload was
  retained.
- Added and verified the fixture-only civil-service -> Presidential personnel cross-lane case for
  이원주; no live Presidential adapter, source fetch, Person materialization or schema change was
  introduced.
- Re-opened and compared the official 민주노총 current/history leadership pages, 한국노총 official
  subsite/publication/affiliate footprint, and 경사노위 structure, board and dated committee-post
  pages. The result was an independent source-contract gate; no labor page/attachment bytes,
  connector, importer, migration or runtime dependency was added.
- Re-ran `.venv\\Scripts\\python.exe -m pytest -o addopts='' tests/test_labor_leadership.py
  tests/test_cross_lane_identity.py -q`: 18 passed, and `.venv\\Scripts\\python.exe -m ruff
  check apps packages workers tests`: passed after the documentation update.
- Re-ran `.venv\\Scripts\\python.exe -m pytest -o addopts='' tests/test_legal_careers.py
  tests/test_labor_leadership.py tests/test_cross_lane_identity.py -q`: 25 passed; Ruff and
  `git diff --check` also passed after the legal source-gate update.
- Re-opened official MOJ personnel-release pages and attachments metadata, the Supreme Court
  personnel release, 2026 Court Gazette issue tables, the later Gazette correction entry and the
  Court copyright policy. No legal attachment bytes, connector, importer, migration or runtime
  dependency was added.
- Confirmed the MOJ post `602956` attachment manifest and page-level `공공누리 2유형` against
  the official KOGL type-2 terms. The packet remained offline because the repository policy still
  denies fetch and the exact attachment rights boundary was not closed.
- Public default `create_app()` returns 404 for `/admin/review`; the test/internal opt-in path
  retains the read-only review regression coverage.
- Hardening Alembic `upgrade head -> downgrade -1 -> upgrade head` round-trip passed; no migration
  was needed because decision links remain in the existing JSON temporal payload.

## Not executed

No feeder implementation, labor federation/commission acquisition, MOJ/Supreme Court legal
personnel acquisition, OpenWatch acquisition, asset/vote/ideology/graph/search feature, raw
provider payload browser, schema change, migration file, dependency install, admin write action,
authenticated operator system or production deployment was performed. No official labor or
legal attachment was downloaded or retained. The public review route remains intentionally
unavailable until an operator access boundary is designed.

## Blockers

Evidence Directory v0 has no implementation blocker. Source work remains bounded by rights and
contract gaps: MPM is L1 CONTRACT_STAGED with L3 blocked; National Assembly asset disclosure and
CleanEye remain L0 RESEARCHED; BLOCKED; and the labor federation/commission lanes lack a complete
universe, stable row identity, correction/version semantics and reuse contract. Those lanes can
reopen for a finite reviewed packet only when the playbook gates close. MOJ/Supreme Court legal
personnel likewise remain L1 with a conditional human-assisted packet path rather than a live
enumerator; the first MOJ packet is still pending packet-specific rights clearance.

## Modified files

- `ARCHITECTURE.md`
- `apps/api/main.py`
- `apps/web/app/admin/review/page.tsx`
- `apps/web/app/data.ts`
- `apps/web/app/layout.tsx`
- `apps/web/app/page.tsx`
- `apps/web/app/people/[id]/page.tsx`
- `apps/web/app/styles.css`
- `apps/web/app/types.ts`
- `apps/web/tests/ui.test.mjs`
- `packages/domain/contracts.py`
- `packages/persistence/repository.py`
- `packages/rendering/profile_projection.py`
- `tests/test_api.py`
- `tests/golden/fixtures/profile_target_lee_wonjoo_001.json`
- `tests/test_profile_target_golden_lee_wonjoo.py`
- `docs/architecture/LABOR_LEADERSHIP_FEEDER.md`
- `docs/architecture/LEGAL_CAREER_FEEDER.md`
- `docs/architecture/FEEDER_SOURCE_COVERAGE.md`
- `HANDOFF.md`

## Next concrete action

Resolve packet-specific rights and third-party ownership for MOJ post `602956` attachments before
any download or deterministic extraction, while keeping Presidential personnel at
`L1 CONTRACT_STAGED`, the Lee Won-joo case fixture-only, labor federation/commission lanes at
their documented human-assisted ceiling, and the legal lane at L1.

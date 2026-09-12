# HANDOFF

## Objective

Complete Evidence Directory v0 and its site v1 read-only product surface over Civic Intel's
existing evidence-first contracts. Keep OpenWatch and future feeder expansion out of this
milestone.

## Scope

Public resolved-person roster, evidence-backed person profile, explicit epistemic/stance/conflict
rendering, source-policy audit projection, responsive site shell, and a separate read-only identity
review surface that is unavailable from the public API unless an internal/test caller explicitly
enables it.
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

- Confirmed the Assembly-to-Evidence Directory milestone baseline before implementation:
  `master` and `origin/master` were both at `f2d2e7e8516f3de33c75aa3641911ec21738fff0`;
  the worktree was clean. The remote remained at that revision after fetch.
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
- Completed the Evidence Directory site v1 pass with the repository `DESIGN.md` visual contract,
  Korean-first responsive shell, client-side displayed-name roster filter, profile map/coverage
  navigation, source-policy cards and a visually explicit read-only review surface. The site uses
  only the existing API and domain contracts; no feeder, source, schema or persistence path changed.
- Added deterministic API and UI regressions for identity filtering, epistemic/provenance trace,
  conflict visibility, review actions, payload minimization and directory scope.
- Completed an independent read-only review and hardened the three findings: unlinked decision
  episodes no longer bypass Claim/Evidence, the review route is disabled by default and no longer
  linked from public navigation, and superseded public temporal records are filtered out.
- Connected the migrated Golden fixture database to the local FastAPI and Next.js development
  servers and manually inspected the roster, resolved profile, conflict profile, populated review
  queue and blocked review-identity route in the in-app browser. Temporary review observations,
  identities, servers and database were removed after inspection.
- Connected the existing National Assembly L3 enumerator to the existing Assembly materialization
  transaction through a source-specific `enumerate_and_materialize()` path. Successful runs carry
  the exact committed observation IDs; resumed runs restore prior page IDs from the checkpoint's
  provider-key/hash manifest before materializing newly committed pages.
- Added deterministic Assembly-to-Evidence Directory regressions for first materialization,
  unchanged reruns, changed provider versions, same-name review, birth-date hard conflict,
  publication rollback, resume coverage and public `/people`/profile provenance. No other feeder,
  schema, migration, dependency or UI path changed.

## Current checkpoint

Evidence Directory v0 and its post-review hardening are complete in the working tree and all
direct verification commands pass. The only runner limitation is that GNU Make is unavailable on
this Windows host, so the Makefile's constituent commands were executed directly. The seven
existing L3 feeders and the blocked MPM, National Assembly asset, CleanEye and roll-call source
gates are unchanged. The 2026-09-12 official MPM revalidation confirmed 125 mixed `취업` board
posts over 9 pages, 405 mixed ethics-board posts over 27 pages, bundled historical PDF posts,
and no published row identity, correction/version or attachment reuse contract. MPM remains
`L1 CONTRACT_STAGED; L3 promotion blocked`.
On 2026-09-13 the site v1 milestone completed locally. The public home now presents the 10
resolved identities, filters only the displayed canonical name in the browser, and routes to the
existing evidence-backed profile/source projection. Profile section coverage, epistemic status,
conflict markers, audit details and source-policy summaries remain visible. The internal review
route is still unlinked and read-only; with the default API it renders the existing unavailable
state because `/admin/review` is not registered without explicit internal/test opt-in.
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
The 2026-09-13 rights revalidation also checked the official KOGL type-2 terms and MOJ copyright
policy: type 2 permits attributed non-commercial sharing/derivatives, while MOJ requires a
work-level rights check and consultation for unmarked material. The inspected page did not expose
per-attachment ownership or third-party scope, and a metadata-only HEAD probe self-redirected for
each attachment route; no body, preview or bytes were retrieved. The rights gate therefore remains
open/blocking, with no L2 or L3 promotion.
The post's listed publishing department, `검찰과`, is the official routing signal for a packet-
specific rights decision; no external inquiry was sent.
The 2026-09-13 follow-on research-career gate inspected the official KDI researcher directory,
organization tree and director/history routes as a candidate source for NKIS-discovered
researchers. KDI exposes bounded current profile views with names, departments, titles and topic
text, but the inspected routes do not declare a complete staff universe, stable profile key,
effective/version or correction semantics. KDI's Open API is publication metadata only, and its
copyright policy states 공공누리 제3유형 (출처표시+변경금지) without a profile-specific
normalization/storage/republication contract. The KDI automated profile path remains
`L0 RESEARCHED; BLOCKED`; no staff crawler, adapter, Person materialization or schema was added.
The same-day CleanEye source-specific revalidation found 423 local public enterprises and 892
invested/contributed institutions, both dated 2026-06-30; the official REST catalog still lists
34 datasets without a named-executive dataset; and the exact named-executive routes return only
`HEAD 405 / Allow: GET, POST` under a current `robots.txt` of `Disallow: /`. Those results provide
no route permission, request-pacing, complete-coverage, version or storage contract. CleanEye
remains `L0 RESEARCHED; BLOCKED`; no HTML collector, source request, payload or schema was added.

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
- Site v1 treats `DESIGN.md` as the visual contract: restrained semantic tokens, Korean-first
  hierarchy, visible UNKNOWN/PARTIAL/conflict states and evidence paths, and no decorative claim
  beyond the existing data. The roster filter is a display-only canonical-name filter and never
  performs identity resolution.
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
- NKIS `ResearchOutput` and institute employment are separate lanes. The KDI directory is not
  an employment universe or identity authority: a bounded reviewed packet may become an L1/L2
  human-assisted source observation only after exact scope and profile-data rights are recorded;
  no name-only identity link, automatic Person materialization or second researcher registry is
  allowed.
- CleanEye's institution selectors and named-executive HTML routes remain a source-specific
  research lane. The 2026-09-13 all-path robots and method revalidation does not grant collection
  permission or fill the missing coverage/version contract; only a permitted finite packet may
  proceed through conditional human review, with no disclosure-row-to-Person promotion.

## Verification evidence

Executed locally on 2026-09-12 and 2026-09-13:

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
- `npm --prefix apps/web test`: 5 passed.
- `npm --prefix apps/web run build`: passed; `/`, `/admin/review` and `/people/[id]` built.
- Site v1 final runtime review used the disposable Golden database with the local API and Next
  server. The in-app browser rendered the 10-person roster, reduced the displayed roster to one
  result for `이원주`, followed a profile link, and showed the default read-only/unavailable review
  state without approval, merge or publication controls.
- Direct desktop captures of the home roster, profile and review surface were opened and
  inspected. A 390x844 emulation capture of the home and profile showed no horizontal overflow;
  the profile layout measured 350px and the source grid collapsed to one column after the final
  responsive adjustment. No Next error overlay appeared during these route checks.
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
- Revalidated the official [MOJ packet](https://www.moj.go.kr/bbs/moj/182/602956/artclView.do),
  [KOGL type-2 terms](https://www.kogl.or.kr/info/licenseType2.do) and [MOJ copyright policy](https://www.moj.go.kr/moj/129/subview.do).
  The six attachment routes were probed with HEAD only and self-redirected without usable metadata;
  no attachment body, preview or bytes were retrieved or retained. The source policy's fail-closed
  permissions and L1 decision were left unchanged.
- Recorded the post's listed publishing department, `검찰과`, as the official routing signal for
  packet-specific rights consultation; no external inquiry or contact detail was stored.
- Revalidated `moj_prosecution_personnel_policy()` with `terms_checked_at=2026-09-13` while
  keeping fetch, fulltext, AI, excerpt and commercial permissions disabled; targeted legal tests,
  full Python tests and Ruff passed after the policy metadata update.
- Re-opened the official [CleanEye enterprise](https://www.cleaneye.go.kr/siteGuide/pubCompStatus.do),
  [invested/contributed](https://www.cleaneye.go.kr/siteGuide/iptCompStatus.do),
  [REST catalog](https://www.cleaneye.go.kr/user/openDataSet.do),
  [copyright policy](https://www.cleaneye.go.kr/user/copyrightPolicy.do) and
  [robots](https://www.cleaneye.go.kr/robots.txt) surfaces. Current establishment totals are
  423 and 892 at 2026-06-30, the catalog lists 34 datasets without named executive status, and
  the two named routes return `HEAD 405 / Allow: GET, POST`. No route body, row payload or
  attachment was requested or retained; the L0 source gate remains blocked.
- Re-opened the official [NKIS institution directory](https://nkis.re.kr/org.do), [KDI researcher
  directory](https://www.kdi.re.kr/introduce/expert), [KDI organization tree](https://www.kdi.re.kr/introduce/org),
  [KDI Open API](https://www.kdi.re.kr/share/openAPI) and [KDI copyright policy](https://www.kdi.re.kr/servicePolicy/copyright).
  The source-contract result was recorded in `POLICY_RESEARCH_FEEDER.md`; no KDI profile body,
  contact field, connector, crawler, schema or runtime dependency was added.
- Updated the active batch-ingestion plan and coverage priority after the KDI gate so the completed
  source-contract reviews and the single current external rights action are explicit; no new
  feeder implementation was selected from an unclosed contract.
- Re-ran `.venv\\Scripts\\python.exe -m pytest -o addopts='' tests/test_assembly_evidence_directory.py
  -q`: 6 passed; full `.venv\\Scripts\\python.exe -m pytest -o addopts='' -q`: 282 passed.
- Re-ran `.venv\\Scripts\\python.exe -m ruff check apps packages workers
  tests/test_assembly_evidence_directory.py`: passed, and `.venv\\Scripts\\python.exe -m mypy
  packages workers apps/api`: success for 51 source files.
- Re-ran `.venv\\Scripts\\python.exe -m packages.verification.quality`: `passed: true`; all
  Golden Set checks passed. Web lint, typecheck, UI tests (4 passed) and production build passed.
- Alembic upgrade/downgrade/upgrade round-trip passed on a temporary SQLite database. `make verify`
  remained runner-unavailable because GNU Make is not installed; constituent checks were run
  directly. GitHub Actions `Verify` run `34706189559` for commit
  `339804008bddb5891b6ad84dd894e289c1d32bf3` completed successfully; the `verify` job took 2m33s
  and passed canonical verification plus the Alembic round trip.
- GitHub Actions `Verify` run `34708727908` for commit
  `7fb747a3f6a8ef15903c91dfd721bca34c048198` completed successfully; the `verify` job took 1m16s
  and passed canonical verification plus the Alembic round trip. The only annotation was the
  existing Node.js 20 deprecation notice.
- Public default `create_app()` returns 404 for `/admin/review`; the test/internal opt-in path
  retains the read-only review regression coverage.
- Hardening Alembic `upgrade head -> downgrade -1 -> upgrade head` round-trip passed; no migration
  was needed because decision links remain in the existing JSON temporal payload.

## Not executed

No feeder implementation, labor federation/commission acquisition, MOJ/Supreme Court legal
personnel acquisition, KDI institute-profile acquisition, CleanEye acquisition, OpenWatch acquisition, asset/vote/ideology/graph/search feature, raw
provider payload browser, schema change, migration file, dependency install, admin write action,
authenticated operator system or production deployment was performed. No official labor or
legal attachment was downloaded or retained. The public review route remains intentionally
unavailable until an operator access boundary is designed.

## Blockers

Evidence Directory v0 has no implementation blocker. Source work remains bounded by rights and
contract gaps: MPM is L1 CONTRACT_STAGED with L3 blocked; National Assembly asset disclosure and
CleanEye remain L0 RESEARCHED; BLOCKED after the 2026-09-13 route/robots revalidation; and the labor federation/commission lanes lack a complete
universe, stable row identity, correction/version semantics and reuse contract. Those lanes can
reopen for a finite reviewed packet only when the playbook gates close. MOJ/Supreme Court legal
personnel likewise remain L1 with a conditional human-assisted packet path rather than a live
enumerator; the first MOJ packet is still pending packet-specific rights clearance. The
government-funded research-career lane remains L0 for the KDI candidate because the current
profile routes lack a complete declared universe, stable record/version contract and
profile-specific reuse permission; a finite rights-approved packet remains the only possible
human-assisted path.

## Modified files

- `AGENTS.md`
- `DESIGN.md`
- `docs/exec-plans/active/evidence-directory-site-v1.md`
- `ARCHITECTURE.md`
- `apps/api/main.py`
- `apps/web/app/admin/review/page.tsx`
- `apps/web/app/components/roster-grid.tsx`
- `apps/web/app/data.ts`
- `apps/web/app/layout.tsx`
- `apps/web/app/page.tsx`
- `apps/web/app/people/[id]/page.tsx`
- `apps/web/app/styles.css`
- `apps/web/app/types.ts`
- `apps/web/tests/ui.test.mjs`
- `packages/domain/contracts.py`
- `packages/connectors/legal_personnel_records.py`
- `packages/persistence/repository.py`
- `packages/rendering/profile_projection.py`
- `tests/test_api.py`
- `tests/golden/fixtures/profile_target_lee_wonjoo_001.json`
- `tests/test_profile_target_golden_lee_wonjoo.py`
- `docs/architecture/LABOR_LEADERSHIP_FEEDER.md`
- `docs/architecture/LEGAL_CAREER_FEEDER.md`
- `docs/architecture/POLICY_RESEARCH_FEEDER.md`
- `docs/architecture/CLEANEYE_LOCAL_PUBLIC_INSTITUTION_FEEDER.md`
- `docs/architecture/FEEDER_SOURCE_COVERAGE.md`
- `docs/exec-plans/active/batch-ingestion-l3.md`
- `docs/architecture/IDENTITY_RESOLUTION.md`
- `docs/INDEX.md`
- `docs/exec-plans/active/assembly-roster-evidence-directory.md`
- `workers/assembly_roster.py`
- `tests/test_assembly_evidence_directory.py`
- `docs/exec-plans/active/cleaneye-local-public-institution-executives-l3.md`
- `HANDOFF.md`

## Next concrete action

Obtain and record an official packet-specific rights/third-party-ownership decision for MOJ post
`602956` attachments before any body request or deterministic extraction.

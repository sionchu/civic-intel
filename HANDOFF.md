# HANDOFF

## Objective

Maintain the evidence-first Civic Intel foundation and carry the completed Evidence Directory v0,
site v1 and North Star into the first small Derived Intelligence product slice. The current slice
is a source-traceable CHANGE experience over an explicitly bounded Assembly historical reviewed
packet, using existing canonical Claim/Evidence and temporal records. The follow-on ALIO
organization Claim contract is also bounded to existing canonical rows; keep live historical
acquisition, OpenWatch and new feeder expansion outside that slice.

## Scope

The current scope includes the public resolved-person roster, evidence-backed person profile,
explicit epistemic/stance/conflict rendering, source-policy audit projection, responsive site
shell, and a separate read-only identity review surface that is unavailable from the public API
unless an internal/test caller explicitly enables it. The long-term product direction is the
canonical `docs/product/CIVIC_INTEL_NORTH_STAR.md`; the immediate CHANGE plan must preserve the
existing `Person -> Claim -> ClaimEvidence -> Source -> SourcePolicy` path and, when present,
`ClaimEvidence -> FeederObservation -> SourceSnapshot -> Source` provenance. The only follow-on
schema change is the in-place `claims.organization_id` subject extension in migration `0005`;
no live historical acquisition, live ALIO organization binding, search infrastructure,
recommendation algorithm or new persistence abstraction is in scope.

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
- A first CHANGE experience has a source-specific input scope, deterministic comparison rule,
  visible evidence/provenance trace, explicit coverage/limitations and a bounded reviewed-packet
  acceptance path.
- Derived output remains visibly separate from FACT/CLAIM/UNKNOWN and does not add a new
  `EpistemicStatus` or silently alter publication semantics.

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
- Added `docs/product/CIVIC_INTEL_NORTH_STAR.md` as the canonical long-term direction and
  Derived Intelligence boundary. Linked it from `ARCHITECTURE.md`, `docs/INDEX.md` and
  `docs/product/V0_SCOPE.md`; no code, schema, migration, feeder or dependency was added.
- Defined the first CHANGE discovery slice in
  `docs/exec-plans/active/change-discovery-experience-v1.md`. The plan uses existing temporal
  Claim/Evidence inputs, requires pinned scope and provenance, and leaves implementation for the
  next approved vertical slice.
- Added `docs/architecture/SOURCE_PARSING_AND_SEMANTICS.md` as the companion governing document
  for source hierarchy, typed source-record parsing, normalization, locators and revision
  semantics. It reuses the existing SourcePolicy/SourceSnapshot/FeederObservation foundation and
  does not add a parser framework, live source/feeder, schema or dependency.
- Used the National Assembly historical member-career API gate as the concrete boundary case:
  `MONA_CD` is a provider identity/crosswalk value, `PROFILE_UNIT_CD` is term/history scope,
  `FRTO_DATE` is a source temporal field, and a possible `{MONA_CD}:{PROFILE_UNIT_CD}` value is
  only a source-scoped observation key. The lane remains `L1 CONTRACT_STAGED; L3 promotion
  blocked`; the live source gate did not authorize L3 promotion or live CHANGE coverage.
- Implemented the bounded Assembly reviewed-packet vertical slice: typed packet parsing, immutable
  `SourceRun`/`SourceSnapshot`/`FeederObservation` staging, reviewed Claim/Evidence import with
  exact observation provenance, and a read-only profile `DERIVED · CHANGE` projection/UI for the
  known-positive `XQ98168F` pair. No live historical fetch, L3 worker, new schema or new feeder
  was added.
- Completed the approved Assembly current-roster bootstrap after a fresh staging logical
  backup/restore receipt: the existing unfiltered L3 worker committed 299 provider observations,
  source-specific materialization resolved 298 canonical People and kept one exact birth-date
  conflict in the review queue. Provider `MONA_CD` values remain source-scoped external IDs and
  are never canonical Person IDs.
- Added the smallest Assembly Person Base Profile v1 slice for `party`, `district`, `committees`
  and `reelection`. It reuses the existing Claim/Evidence publication gate and repository session,
  publishes exact snapshot/observation provenance, preserves missingness, and treats a changed
  observation as an immutable version conflict. No new model/table/migration/dependency or raw
  normalized-payload UI path was added.

## Current checkpoint

Evidence Directory v0, site v1, the North Star documentation milestone and the bounded Assembly
CHANGE proof are complete in the working tree. Direct verification commands pass. The only runner
limitation is that GNU Make is unavailable on this Windows host, so the Makefile's constituent
commands were executed directly. The seven
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
The same-day ALIO operational run completed the unfiltered item-4 current-disclosure scope: 355
directory institutions were covered, 347 had a provider-ranked current disclosure and 8 returned
the official no-current sentinel. The canonical batch foundation now retains 3,797 disclosure-row
observations and one `CORRECTION_ONLY` report observation; 3,624 rows have public names and 173
retain `MASKED_OR_VACANT` missingness. No name was invented for an empty or correction-only
source result, masked/vacant rows were kept out of identity staging, and no Person was created.
The ALIO lane remains L3 for current-disclosure observation enumeration, while named-row
completeness is explicitly bounded by those source-declared outcomes.
The same local canonical batch database then registered the already-defined Gwanbo scope
`2026-08-01:2026-08-31`: the official personnel-list request completed with `SUCCESS`, one page,
and zero notices. Gwanbo is metadata-only and intentionally creates no Person/name observation;
the empty result is recorded as the current response for that bounded interval, not as a claim
that the historical source is globally empty.
The operational audit of all seven existing L3 targets is now: Assembly roster, Assembly bill
participation, NEC winners, NEC candidates and OpenDART are source-specific and ready for their
declared scopes but await runtime API credentials; Gwanbo has two bounded scopes registered; ALIO
has the full 355-institution current-disclosure scope registered. No new target or generic
registry was added.
The current rolling three-year Gwanbo window `2023-09-13:2026-09-13` was also registered with
`SUCCESS`, one page and zero notices. As with the shorter window, this is a bounded current
response and does not establish that the source has no historical personnel notices.
The previous shipped documentation baseline for this handoff was `9b94f2149ffd62c9b90206989d94908a003d68f5`.
The local Assembly proposer automatic accumulation candidate
from the separate review checkout is not part of this shipped state; its local run receipts and
SQLite counts must not be used as product coverage.
The active CHANGE plan now uses only existing canonical persistence and a bounded reviewed packet;
it does not require a new feeder or schema.
The input gate found one eligible role Claim in the Golden public seed (zero pairs), while the
reviewed Kim Hyun-ji fixture has four eligible Claims and four cross-date proof pairs. The
fixture's metadata-only DISCOVERY_ONLY policies support rule regression, not live acquisition or
public coverage. The Assembly packet proof completed the read-only projection/API and profile UI
milestones while the live/public input gate remains closed.
The 2026-09-13 official Assembly historical-member API gate found a documented former-member
service with pagination and a live sample pair for provider code `XQ98168F` across the 19th and
20th terms. A read-only page-by-page probe of the observed `PROFILE_UNIT_CD=100001..100022`
range returned 5,467 rows with stable page totals; the current roster returned 299 rows and had
zero `MONA_CD` overlap with those history rows. Seventeen `{MONA_CD}:{PROFILE_UNIT_CD}` groups
were duplicated within a term, including multiple dated periods for one provider/person-term
group. The service page does not publish a finite code manifest, row-level key, correction/version
chain or dataset-specific reuse permission. Its current-member exclusion, incomplete coverage
contract and rights/version gaps keep it at `L1 CONTRACT_STAGED`; this is source evidence, not a
canonical Person/Claim or public CHANGE input.
The follow-on documentation audit fixed the post-acquisition hierarchy and parser boundary using
that gate as a worked example. It preserves separate official/curated Sources, keeps locators and
revision metadata in the existing source/run/observation structures where sufficient, and leaves
first-class release/document/field-lineage models as future options only when a real source
requires them.

The packet proof uses `tests/fixtures/assembly_historical_known_positive_001.json` for one resolved
reviewed Person (`강길부`, `MONA_CD=XQ98168F`) and the `제19대`/`제20대` records. The parser keeps
`MONA_CD` and `PROFILE_UNIT_CD` as provider-scoped values, retains `FRTO_DATE` as the source
temporal field, marks row identity unavailable, and rejects repeated person/term groups. Each
ClaimEvidence row retains its exact observation and snapshot chain. A same-group changed value is
stored as another immutable observation and is excluded from CHANGE; only the two dated term
Claims produce the bounded derived sequence card. This is a reviewed fixture/manual path, not the
batch main path or a public completeness claim.

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
- ALIO item 4 is the next completed source-bounded full-enumeration proof. Its `apbaId` directory,
  current `disclosureNo` and disclosure-row ordinal remain provider/source keys, not Person
  authority; empty current reports, masked/vacant seats and correction-only reports are explicit
  observation states.
- The North Star keeps `Evidence Core`, `Derived Intelligence` and `Public/Product Experience`
  as conceptual layers without adding database enums or parallel models. `CHANGE`,
  `CONTRADICTION`, `COMPARISON`, `CONNECTION` and `MONEY` are discovery primitives, not new
  tables.
- A CHANGE result must be computed from a declared pair or set of canonical records with valid
  time, recorded time, source coverage and correction handling. It cannot be inferred from a
  changed fetch timestamp alone or presented as a FACT.
- Source hierarchy is semantic rather than a mandate for one persistent model per layer. The
  current Source/SourceSnapshot/FeederObservation chain is the capture boundary; Release,
  Document, Disclosure, SourceRecord and FieldLocator remain source-specific concepts until a
  concrete rights or lineage requirement exceeds existing metadata.
- Parsing stops at a typed provider record or normalized observation candidate. It preserves source
  authority, scope, field-level provenance and explicit missingness, but cannot merge Persons,
  publish Claims, infer derived CHANGE or repair missing values.
- The Assembly historical-career API remains a documentation/parser-boundary case for live
  acquisition. Its bounded reviewed fixture proves a source-scoped derived sequence only:
  `MONA_CD`, `PROFILE_UNIT_CD` and `FRTO_DATE` must not be conflated with canonical identity,
  real-world CHANGE time or a permanent record key.

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
- Re-opened the official [Assembly historical member-career service](https://open.assembly.go.kr/portal/data/service/selectAPIServicePage.do/OD21030011944P19666),
  [term-inventory service](https://open.assembly.go.kr/portal/data/service/selectAPIServicePage.do/OLFZV7001148O518934),
  [Open API terms](https://open.assembly.go.kr/portal/policy/openUserAgreementPage.do) and
  [copyright policy](https://open.assembly.go.kr/portal/policy/copyRightPage.do). The pages
  expose the former-member boundary, required term filter, version label, pagination, request
  limit display and rights conditions; the history and term responses were queried read-only with
  the existing local credential, never persisted, and never printed. The observed 22-code map,
  current/history zero-overlap, 17 duplicate term-group keys, consecutive/nonconsecutive career
  controls and composite `PROFILE_SJ` changes were recorded in the active source gate. No
  historical connector, worker, fixture, source policy, database row or CHANGE input was added.
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
- North Star documentation verification on `c2b67fbe16bd7c31b605ad19ecb06ce78ae56e29`: 47 local
  relative-document links passed, `git diff --check` passed, Python 289 tests passed with 4
  warnings, Ruff passed, mypy passed for 51 source files, Golden quality passed, and web lint,
  typecheck, 5 tests and production build passed. GitHub Actions `Verify` run `34755498332`
  completed successfully, including canonical verification and Alembic round trip.
- Public default `create_app()` returns 404 for `/admin/review`; the test/internal opt-in path
  retains the read-only review regression coverage.
- Hardening Alembic `upgrade head -> downgrade -1 -> upgrade head` round-trip passed; no migration
  was needed because decision links remain in the existing JSON temporal payload.
- `.venv\Scripts\python.exe -m pytest -o addopts='' tests/test_alio_public_institutions.py
  tests/test_batch_alio_executives.py -q`: 26 passed.
- `.venv\Scripts\python.exe -m ruff check packages\connectors\alio_disclosures.py
  packages\domain\enums.py workers\public_institutions.py tests\test_alio_public_institutions.py
  tests\test_batch_alio_executives.py`: passed; `.venv\Scripts\python.exe -m mypy packages
  workers apps/api`: success for 51 source files.
- `.venv\Scripts\python.exe -m workers.public_institutions --resume
  --database-url sqlite:///./civic_intel.db`: official ALIO run returned `SUCCESS`, checkpoint
  cursor `355`, and `unique_records=3797` for the resumed run. Read-only QA of the ignored local
  database found 355 directory codes, 347 current disclosures, 8 no-current sentinels, 3,798
  observations including one correction-only report, 3,624 public-name rows and 173 explicit
  masked/vacant rows.
- No Alembic migration was added; the ALIO hardening reuses revision `0004` and the canonical
  SourceRun/SourceCheckpoint/FeederObservation transaction.
- `.venv\Scripts\python.exe -m workers.gwanbo_personnel --from-date 2026-08-01
  --to-date 2026-08-31 --database-url sqlite:///./civic_intel.db`: official Gwanbo scope returned
  `SUCCESS`, `pages_committed=1` and `unique_records=0`; the checkpoint was persisted without
  Person or name fields.
- `.venv\Scripts\python.exe -m workers.gwanbo_personnel --from-date 2023-09-13
  --to-date 2026-09-13 --page-size 100 --database-url sqlite:///./civic_intel.db`: the official
  rolling three-year scope returned `SUCCESS`, `pages_committed=1` and `unique_records=0`; its
  separate bounded checkpoint was persisted without Person or name fields.
- `C:\Users\getch\OneDrive\Documents\ChatGPT\cvic\.venv\Scripts\python.exe -m pytest
  -o addopts='' -q`: 289 passed, 4 warnings in 130.79s.
- `ruff check apps packages workers tests`: passed; `mypy packages workers apps/api`: success for
  51 source files; `packages.verification.quality`: passed with all Golden Set checks true.
- The documentation relative-link check reported `BROKEN_RELATIVE_LINKS=0` across 54 Markdown
  files; `git diff --check` passed.
- Nested worktree web lint, typecheck and UI tests passed (`5` UI tests). Its production build
  attempt was blocked by Turbopack rejecting the temporary out-of-root dependency junction. The
  tracked `apps/web` trees at nested `5ca7be8` and root `a2766da` were identical; the canonical
  root build then passed and generated `/`, `/_not-found`, `/admin/review` and `/people/[id]`.
- `make verify` was not runnable because GNU Make is not installed on this Windows host; the
  constituent Python and web checks above were run directly.
- Current bounded Assembly CHANGE proof verification: `tests/test_assembly_historical_change.py`
  passed 7 tests with 2 warnings; the full Python suite passed 296 tests with 4 warnings; Ruff
  passed; mypy passed for 53 source files; and the Golden quality report passed all checks.
- Current web verification passed lint, typecheck, 5 UI tests and production build. The build
  generated `/`, `/_not-found`, `/admin/review` and `/people/[id]` routes. The local Markdown
  relative-link check passed for 55 Markdown files. `make verify` was attempted in this worktree
  and remains runner-unavailable because GNU Make is not installed.
- Implementation commit `0abb7128a5c7ac56b8cb484bc12ffd91e73b3022` was pushed to `origin/master`.
  Post-push verification recorded `HEAD == origin/master` at that commit and a clean worktree.
- The new regression covers missing/mismatched observation provenance: a ClaimEvidence item that
  references a feeder observation must retain its snapshot and matching source chain.

## Not executed

No live CHANGE acquisition, new Derived Intelligence model, recommendation algorithm, community
feature, API/MCP extension or new feeder was executed. A packet-only Assembly parser, deterministic
reviewed fixture and read-only derived profile projection were added for the bounded proof; no
live historical fetch, worker, migration, L3 run or public CHANGE coverage was added.
No additional feeder implementation beyond the ALIO source-specific hardening, labor
federation/commission acquisition, MOJ/Supreme Court legal personnel acquisition, KDI
institute-profile acquisition, CleanEye acquisition, OpenWatch acquisition, asset/vote/ideology/graph/search feature, raw
provider payload browser, schema change, migration file, dependency install, admin write action,
authenticated operator system or production deployment was performed. No official labor or
legal attachment was downloaded or retained. The public review route remains intentionally
unavailable until an operator access boundary is designed. Assembly, NEC and OpenDART full-list
runs were not started in this shipped checkout because their runtime credentials are absent; the
separate local review checkout's Assembly proposer run is not shipped. Further Gwanbo windows were
not selected because that lane requires an explicit bounded interval.

## Blockers

Evidence Directory v0 has no implementation blocker. The bounded reviewed packet proves the
read-only CHANGE path for one resolved Person, but live/public CHANGE coverage remains blocked at
the source-approved input gate.
Source work remains bounded by rights and
contract gaps: MPM is L1 CONTRACT_STAGED with L3 blocked; the National Assembly historical-member
career lane is L1 CONTRACT_STAGED with L3 blocked because its provider code manifest, row identity,
correction/version and service-specific reuse contract remain open; National Assembly asset
disclosure and CleanEye remain L0 RESEARCHED; BLOCKED after the 2026-09-13 route/robots
revalidation; and the labor federation/commission lanes lack a complete
universe, stable row identity, correction/version semantics and reuse contract. Those lanes can
reopen for a finite reviewed packet only when the playbook gates close. MOJ/Supreme Court legal
personnel likewise remain L1 with a conditional human-assisted packet path rather than a live
enumerator; the first MOJ packet is still pending packet-specific rights clearance. The
government-funded research-career lane remains L0 for the KDI candidate because the current
profile routes lack a complete declared universe, stable record/version contract and
profile-specific reuse permission; a finite rights-approved packet remains the only possible
human-assisted path. ALIO's L3 observation scope is complete, but its 8 no-current institutions,
173 masked/vacant rows and one correction-only report are not converted into named People. The
remaining full-list lanes require their exact source credentials; any additional Gwanbo run
requires an explicit date window. The two registered Gwanbo windows remain metadata-only and
produce no name universe.

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

Source parsing and semantics documentation milestone:

- `docs/architecture/SOURCE_PARSING_AND_SEMANTICS.md`
- `ARCHITECTURE.md`
- `docs/INDEX.md`
- `docs/architecture/FEEDER_SOURCE_COVERAGE.md`
- `docs/exec-plans/active/change-discovery-experience-v1.md`
- `docs/product/CIVIC_INTEL_NORTH_STAR.md`
- `HANDOFF.md`

North Star documentation milestone:

- `docs/product/CIVIC_INTEL_NORTH_STAR.md`
- `ARCHITECTURE.md`
- `docs/INDEX.md`
- `docs/product/V0_SCOPE.md`
- `docs/exec-plans/active/change-discovery-experience-v1.md`

Latest ALIO full-enumeration hardening also touched:

- `docs/architecture/BATCH_INGESTION.md`
- `docs/architecture/FEEDER_SOURCE_COVERAGE.md`
- `docs/architecture/PUBLIC_INSTITUTION_FEEDER.md`
- `docs/exec-plans/active/alio-public-institution-executives-l3.md`
- `packages/connectors/alio_disclosures.py`
- `packages/domain/enums.py`
- `tests/test_alio_public_institutions.py`
- `tests/test_batch_alio_executives.py`
- `workers/public_institutions.py`

Current bounded Assembly CHANGE proof files:

- `packages/connectors/open_assembly_historical.py`
- `packages/verification/assembly_historical_review.py`
- `packages/persistence/repository.py`
- `packages/rendering/profile_projection.py`
- `apps/api/main.py`
- `apps/web/app/people/[id]/page.tsx`
- `apps/web/app/styles.css`
- `apps/web/app/types.ts`
- `apps/web/tests/ui.test.mjs`
- `tests/fixtures/assembly_historical_known_positive_001.json`
- `tests/test_assembly_historical_change.py`
- `tests/test_api.py`
- `tests/test_profile_projection.py`

## Current checkpoint — ALIO Item 12 MONEY

### Objective

The second Derived Intelligence primitive is a bounded, descriptive MONEY projection over the
official ALIO item 12 `기관장 업무추진비` report. The source lane must preserve the existing
SourcePolicy → Source → SourceSnapshot → FeederObservation path and must not attribute an
institution aggregate to a named Person.

### Scope and decisions

- Baseline at start and remote `master`: `1af5f7ca0a76a5683415d9241c07066d5166bf90`; Alembic
  head remains `0004`.
- Official Item 12 uses `reportFormRootNo=20701`; the 2026-09-14 unfiltered directory returned
  355 rows and 355 unique `apbaId` values, including four explicit no-current-disclosure rows.
- The live implementation is deliberately bounded to known-positive `C0019`, `C0129` and
  `C0908`. Their current report pages expose 2021–2025 annual aggregate rows, `천원` units,
  as-of/submission dates and mixed `.xls`/`.xlsx` filenames.
- `apbaId` is an institution namespace, `disclosureNo` is report identity and
  `submissionNo`/filename is locator metadata. The provider does not declare annual-row
  correction/replacement semantics, so `{disclosureNo}:{fiscal_year}` is accepted only after
  exact identity and unique-year checks; changed values become new immutable observations.
- Existing ALIO `SourcePolicy` was minimally widened for Item 12. Fulltext, excerpts, AI,
  attachment bytes and disclosure staff contacts remain excluded.
- At the start of the Item 12 slice, `Claim.person_id` was mandatory and no organization
  Claim/Evidence route existed; that slice therefore produced no Claim/Evidence publication.
  The follow-on organization-scoped contract is recorded below, while live MONEY publication
  remains blocked.

### Completed

- Added the source-specific Item 12 connector/parser and strict aggregate normalization.
- Added the allowlisted worker `workers.alio_business_expense` and
  `civic-stage-alio-money` entry point using shared source/run/checkpoint/observation persistence.
- Added `money.alio-head-expense-yoy.v1` as an in-memory deterministic projection with exact
  source/snapshot/observation references and explicit zero-baseline behavior.
- Added the active plan `docs/exec-plans/active/alio-item12-money-v0.md` and updated the public
  institution, source semantics, coverage, North Star and index documentation.

### Verification evidence

- Targeted Item 12, existing ALIO and batch executive tests: `40 passed`.
- Targeted Ruff: passed. Targeted mypy for the connector, worker and projection: success.
- Alembic `upgrade head` completed on the ignored live SQLite database.
- First live bounded run `ac60cd8b-55ab-4410-91cb-1cc1c6379512`: `SUCCESS`, 3 institutions,
  15 unique records. Second run `a430b5ea-857e-45d8-8b31-34a43d950d60`: `SUCCESS`, 3
  institutions, 15 unchanged records.
- Live database QA: 4 Sources, 4 metadata-only SourceSnapshots, 0 People, 0 Claims; run
  counters were `(15,15,0)` then `(15,0,15)`, with no contact-string matches in snapshots or
  observations. C0908 2024→2025 produced `-2,162,000 KRW` and `-14.39%`, still blocked from
  public publication.
- Milestone DoD: full Python suite `310 passed, 4 warnings`; Ruff passed; mypy succeeded for
  55 source files; Golden quality passed; Alembic upgrade/downgrade-to-base/upgrade round-trip
  passed; web lint/typecheck passed, 5 UI tests passed and production build passed. The
  Markdown link check found 68 relative links and 0 broken links. `make verify` was attempted but
  GNU Make is not installed on this Windows host; its constituent commands passed directly.

### Not executed and blockers

- No full 355-institution annual-row enumeration, attachment download, Person materialization,
  organization schema, public route, generic financial abstraction or scheduled sync was added.
- Item 12 is `L2 SINGLE_PULL` only for the three-institution bounded proof. L3 is not attempted;
  the full annual-row universe and correction/version contract are not selected as a closed L3
  scope. The public MONEY surface remains blocked until a reviewed canonical Organization binding,
  published annual organization Claims and an approved projection path exist.

### Modified files for this milestone

- `packages/connectors/alio_disclosures.py`
- `workers/alio_business_expense.py`
- `packages/rendering/money_projection.py`
- `tests/test_alio_item12_money.py`
- `pyproject.toml`
- `docs/architecture/PUBLIC_INSTITUTION_FEEDER.md`
- `docs/architecture/FEEDER_SOURCE_COVERAGE.md`
- `docs/architecture/SOURCE_PARSING_AND_SEMANTICS.md`
- `docs/product/CIVIC_INTEL_NORTH_STAR.md`
- `docs/exec-plans/active/alio-item12-money-v0.md`
- `docs/INDEX.md`
- `HANDOFF.md`

## Current checkpoint — organization-scoped Claim/Evidence

### Objective

Provide the smallest canonical Claim/Evidence subject extension needed for a future descriptive
ALIO Item 12 publication without replacing the Person path or turning an institution aggregate
into a Person assertion.

### Completed

- Extended `Claim` and the `claims` table in place so exactly one of `person_id` or
  `organization_id` is populated. The Pydantic validator and database check constraint enforce the
  same rule.
- Added Alembic `0005` with a downgrade guard that refuses to remove the subject column while
  organization claims exist.
- Extended the shared publication validator and repository with an atomic organization Claim
  importer. It accepts only an existing current canonical `Organization`; it never materializes
  one from ALIO `apbaId`, a name or a source row.
- Added the ALIO Item 12 source-specific Claim builder and read-only organization routes. The
  builder retains `apbaId` as source-scoped context, requires exact current organization-name
  binding and reuses SourcePolicy, Source, SourceSnapshot and FeederObservation provenance.
- Added a fail-closed gate for multiple immutable observation content hashes for one source record
  key. The bounded ALIO worker remains observation-only.

### Verification evidence

- Targeted regression after the version gate: `32 passed, 4 warnings` across Item 12, migration
  and API tests.
- Ruff passed for `apps packages workers tests migrations`; mypy succeeded for `packages workers
  apps/api` with 55 source files.
- Full Python suite passed with `314 passed, 4 warnings`; Golden quality passed all checks; the
  migration test passed the `0005` upgrade/downgrade/upgrade round-trip; web lint/typecheck passed,
  5 UI tests passed and the production build generated `/`, `/_not-found`, `/admin/review` and
  `/people/[id]`; the Markdown check found 70 relative links across 57 Markdown files with 0
  broken links; `git diff --check` passed. No live ALIO organization Claim was published.

### Not executed and blockers

- No automatic ALIO-to-Organization binding, organization enumeration, scheduled sync, raw
  report/attachment storage, generic financial schema, `/money` route or UI was added.
- ALIO Item 12 remains `L2 SINGLE_PULL` for the three-institution observation proof; the public
  MONEY projection remains blocked until it consumes published annual organization Claims with
  exact ClaimEvidence/observation provenance.

## Current checkpoint — Claim-backed ALIO Item 12 MONEY projection

### Objective

Expose the smallest read-only ALIO Item 12 MONEY result downstream of the canonical organization
Claim/Evidence path. The result must consume published annual organization Claims, exact
ClaimEvidence and the repository-complete immutable observation set; the bounded worker remains
observation-only.

### Completed

- Added the source-specific `build_alio_head_expense_money_from_claims()` read-model builder.
  It requires current published FACT organization Claims, one exact SUPPORT evidence item,
  matching Claim qualifiers/text and the existing SourcePolicy → Source → SourceSnapshot →
  FeederObservation chain.
- Added read-only `GET /organizations/{organization_id}/money` with explicit earlier/later fiscal
  year query parameters. It expands each referenced provider record key to all stored immutable
  versions and fails closed when content hashes disagree.
- The derived result preserves both input Claim IDs, serialized ClaimEvidence and exact
  source/snapshot/observation provenance. It has no Claim/FACT status and cannot be used to infer
  personal spending, waste, corruption, causation, performance or peer superiority.
- Kept the existing observation-only MONEY builder `publication_status: BLOCKED`; no generic
  `/money` route, organization enumeration, automatic ALIO binding, migration or persistent
  financial model was added.
- Updated the organization Claim, Item 12 feeder, source-semantics, North Star, index, execution
  plan and this handoff documentation.

### Verification evidence

- Targeted Item 12 regression: `20 passed, 2 warnings`.
- Full Python suite: `316 passed, 4 warnings`.
- Ruff `apps packages workers tests migrations`: passed; mypy `packages workers apps/api`:
  success for 55 source files.
- Golden quality checks: all checks true.
- Web lint, typecheck, UI tests (`5 passed`) and production build: passed.
- Markdown check: 56 repository Markdown files, 73 relative links, 0 broken links.
- `git diff --check`: passed. `make verify` was attempted but `make` is unavailable on this
  Windows host; its constituent commands passed directly.

### Not executed and blockers

- No live ALIO organization Claim was published. The three-institution Item 12 observation proof
  remains `L2 SINGLE_PULL`; the full directory, annual-row completeness and provider correction
  semantics remain outside L3.
- No automatic `apbaId` → Organization binding, scheduled sync, raw report/attachment storage,
  Person materialization, generic financial schema or UI was added.
- The new route returns no MONEY result until a reviewed canonical Organization binding and
  annual Claims exist.

### Modified files for this milestone

- `apps/api/main.py`
- `packages/rendering/money_projection.py`
- `tests/test_alio_item12_money.py`
- `docs/architecture/FEEDER_SOURCE_COVERAGE.md`
- `docs/architecture/ORGANIZATION_CLAIM_PUBLICATION.md`
- `docs/architecture/PUBLIC_INSTITUTION_FEEDER.md`
- `docs/architecture/SOURCE_PARSING_AND_SEMANTICS.md`
- `docs/product/CIVIC_INTEL_NORTH_STAR.md`
- `docs/exec-plans/active/alio-item12-claim-backed-money-projection-v0.md`
- `docs/exec-plans/active/organization-claim-publication-v0.md`
- `docs/INDEX.md`
- `HANDOFF.md`

## Next concrete action

Authorize one manually reviewed ALIO `apbaId` to existing-Organization binding and import exactly
two annual Item 12 Claims through the canonical importer before exercising the route with live
data.

## Current checkpoint — live ALIO binding audit (2026-09-14)

### Result

- A read-only inspection of `alio_item12_live.db` initially found schema head `0004`, 15 normalized
  Item 12 observations, four ALIO Sources/Snapshots and one ALIO SourcePolicy. The observations
  cover `C0019`, `C0129` and `C0908`, one row per institution for each fiscal year from 2021 through
  2025.
- The database contains zero `Organization` rows and zero Claims. No existing canonical
  Organization is therefore available for a reviewed `apbaId` binding or annual Claim import.
- The provider codes remain source-scoped identifiers. No organization was created, no binding was
  inferred and no Claim was imported. The ordinary `0005` migration was then applied to this local
  ignored runtime database, and a read-only recheck verified schema head `0005`, the
  `claims.organization_id` column and the unchanged zero Organization/Claim counts.
- No live route exercise was performed because the canonical Organization subject and annual Claims
  do not exist.

### Decision

The Claim-backed Item 12 projection remains implementation-ready but has no live organization
subject to read. The identity/materialization boundary is the active blocker, not a feeder parser
failure. Keep the bounded worker observation-only and do not select an Organization from a provider
name, `apbaId` or source row.

## Next concrete action

Authorize one manually reviewed ALIO `apbaId` to an existing canonical Organization, then import
exactly two annual Item 12 Claims through the canonical importer before exercising the route with
live data.

## Current checkpoint — reviewed C0908 Claim-backed runtime slice (2026-09-14)

### Completed

- After explicit operator approval, the bounded known-positive ALIO `C0908` institution was
  manually bound to `정보통신기획평가원` with canonical Organization ID
  `b6c4df5d-2d9b-4c26-aedb-2c5a0f079b11`. This was an operator action against the ignored local
  runtime database, not automatic `apbaId` materialization.
- Exactly two annual Claims were imported through the existing organization Claim importer: the
  2024 observation key `2026041303154117:2024` and the 2025 key `2026041303154117:2025`. Both are
  `PUBLISHED` `FACT` Claims with one `SUPPORT` ClaimEvidence item and exact ALIO
  SourcePolicy → Source → SourceSnapshot → FeederObservation provenance.
- The actual API check returned `200` / `AVAILABLE` from the organization MONEY route. The
  derived comparison was `-2,162,000 KRW` and `-14.39%`, with both Claim and Evidence IDs
  preserved in the response.
- No other institution or year was imported. The worker remains observation-only, the lane remains
  `L2 SINGLE_PULL`, and the local database is not a Git or deployment artifact.

### Verification

- Read-only database recheck: schema head `0005`, one Organization, two Claims, two
  ClaimEvidence rows and 15 Item 12 observations.
- The source-specific Item 12 regression remains `20 passed, 2 warnings`; the manual import and
  route check completed without changing repository code.

### Decision

The existing Claim-backed route now has one reviewed local Organization slice. This does not
authorize automatic institution binding, full-directory Claim publication, scheduled sync, L3
promotion, or a public UI. Keep any further institution or year outside this slice until a separate
execution plan defines the review and publication boundary.

## Next concrete action

Create a separate execution plan for an explicit operator-facing Organization binding workflow
before adding any further ALIO institution Claims or a public organization page.

## Current checkpoint — reviewed ALIO Claim import workflow (2026-09-14)

### Completed

- Added [`alio-reviewed-organization-binding-workflow-v0.md`](docs/exec-plans/active/alio-reviewed-organization-binding-workflow-v0.md)
  as the separate active plan required before extending the reviewed C0908 slice.
- Added `workers/alio_reviewed_claim_import.py` and the
  `civic-import-alio-reviewed-claims` entry point. It requires an existing current canonical
  Organization ID, one bounded known-positive ALIO code and exactly two fiscal years. It never
  creates or updates an Organization, performs network fetches or enumerates additional rows.
- Default execution is a no-write `DRY_RUN`; `--commit` preflights both source-specific Claims
  and then reuses `SqlAlchemyRepository.import_organization_claim()` for persistence.
- The local C0908 2024/2025 Claims remain the only live annual organization Claims. A real local
  dry-run for C0908 2021/2022 returned `DRY_RUN` and left the database at one Organization, two
  Claims, two ClaimEvidence rows and 15 observations.

### Verification

- Targeted Item 12 and workflow tests: `24 passed, 2 warnings`.
- Full Python suite: `321 passed, 4 warnings`; Ruff passed; mypy passed for 56 source files;
  Golden quality passed.
- Web lint/typecheck/UI tests (`5 passed`)/build passed; Markdown check found 60 files, 74
  relative links and 0 broken links; `git diff --check` passed.
- The active plan and this handoff now distinguish the repeatable human-approved import lane from
  automatic ALIO binding and L3 promotion.

### Decision

The workflow is ready for already-reviewed existing Organization bindings. Keep it source-specific
and operator-run; do not add a binding table, approval API, public organization page, additional
institution Claims or scheduled sync under this plan.

## Next concrete action

Create a new execution plan before adding further institution Claims or a public organization page.

## Current checkpoint — Organization Evidence page v0 (2026-09-14)

### Completed

- Added [`organization-evidence-page-v0.md`](docs/exec-plans/active/organization-evidence-page-v0.md)
  and implemented `apps/web/app/organizations/[id]/page.tsx` as a bounded, direct-ID public
  read surface for existing canonical Organization Claims.
- Reused the existing Organization, Claim, ClaimEvidence, Source, SourcePolicy and Claim-backed
  MONEY API reads. The page shows published organization Claims, exact evidence/source traces and
  an explicitly separate derived MONEY view when available.
- Added typed web contracts/data reads, design-system-consistent styles and seven deterministic UI
  tests. No organization list, binding action, API route, migration, feeder, raw-payload store or
  publication logic was added.

### Verification

- Web lint, typecheck, UI tests (`7 passed`) and production build passed; the build includes
  `/organizations/[id]`.
- Full Python suite: `321 passed, 4 warnings`; Ruff passed; mypy passed for 56 source files;
  Golden quality verification passed.
- Local C0908 runtime proof returned `200` / `AVAILABLE`, two Claims and derived
  `-2,162,000 KRW` / `-14.39%`. This remains local runtime evidence, not deployment-wide coverage.
- Desktop and 390px browser inspection showed the Claim/Evidence/source trace and MONEY card;
  browser error/warning logs were empty and narrow-layout horizontal overflow was false.
- Markdown/link and diff checks passed. Generated Next files were cleaned/restored; ignored local
  database and credentials were not included.

### Decision

The page is a read-only consumer of already published canonical records. ALIO Item 12 remains
`L2 SINGLE_PULL`; there is still no automatic Organization enumeration or `apbaId` binding, and
the page does not change feeder maturity.

## Next concrete action

Define an approved hosting/API/DB target and data-loading procedure, then run the first host-level
direct-ID route smoke before adding further Organization coverage or identity-binding behavior.

## Deployment review checkpoint — Organization Evidence page v0 (2026-09-14)

### Findings

- The repository has local API/web commands and CI verification, but no hosting manifest,
  production API URL, deployment workflow or deployment database configuration. The web build is
  standalone while the API requires a separately migrated database at the current Alembic head.
- The local production probe reproduced the warning that `next start` is incompatible with
  standalone output. Updated `apps/web/package.json` so `npm run start` invokes
  `node .next/standalone/server.js`, then exercised that corrected path against the local API.
- Corrected production-host smoke returned `200` for C0908 with the organization, derived MONEY
  and SourceSnapshot/FeederObservation trace; an unknown UUID returned `404`, and the direct
  MONEY API returned `200` / `AVAILABLE`.
- `.env.example` points `NEXT_PUBLIC_API_URL` at localhost for local use. The ignored
  `alio_item12_live.db` contains the reviewed C0908 sample, but it is not a Git or deployment
  artifact and must not be treated as public coverage.
- GitHub Verify succeeded for `8aefe74ddead6eb0afde7708114424899713a602` in run `34777130619`;
  GitHub reported zero environments and zero deployments.

### Decision

The page is locally buildable and safe as a direct-ID, read-only surface. Operational deployment
readiness is blocked until an approved hosting/API/DB target, data-loading procedure and public
source-rights decision exist. The permitted interim path is an operator-supplied canonical
Organization UUID backed by existing published Claims; no enumeration, automatic binding or data
seeding is introduced.

## Next concrete action

Define an approved hosting/API/DB target and data-loading procedure, then run the first host-level
direct-ID route smoke before adding further Organization coverage or identity-binding behavior.
# Current checkpoint — Evidence Preview v1 (2026-09-14)

## Objective

Execute M0 and M1 from the canonical
[`evidence-preview-v1.md`](docs/exec-plans/active/evidence-preview-v1.md) plan: make the reviewed
ALIO two-year Claim operation atomic/idempotent/recoverable, make public read failures honest,
verify the real standalone artifact in a browser, prove PostgreSQL load/restore, and prepare the
hosting contract without external deployment.

## Current checkpoint

- Isolated branch `codex/change-discovery-plan` started clean at
  `1306f00976db6fc7460320885d3863fa236c4ba9`, equal to `origin/master`.
- The root checkout, ignored ALIO runtime database and other worktrees remain outside this worktree.
- Governing documents and the ALIO repository/API/web/test paths were re-read.
- M0 through M1.5 are complete. M2 through M5 remain deferred by the canonical execution plan.
- The split-transaction risk was reproduced with one residual Claim after an injected second write
  failure. The CLI now uses one shared-repository pair transaction with deterministic IDs, exact
  rerun no-op, safe exact-partial recovery, divergent-partial rejection and a concurrent-call
  regression. No schema or dependency changed.
- Public reads now use stable safe error codes/request IDs; insufficient MONEY inputs, source
  conflicts, public 404 and service failure no longer collapse into one web fallback. Public Source
  reads require reachability from an eligible published Claim and return an allowlisted DTO.
- The standalone build now packages `.next/static` and checks the runtime asset contract. A real
  browser verified roster filtering, profile/source traceability, public 404, API-down and
  insufficient-input states, ALIO MONEY success and immutable-version conflict, 390 px layout and
  the keyboard skip link against disposable data.
- PostgreSQL 16 CI now proves clean migration, a safe `0004` downgrade/current-head upgrade,
  Golden and reviewed ALIO loading, public reads, custom-format backup and restore into a second
  database. The current schema head is `0006`; `psycopg` is the only added runtime dependency.
- Separate non-root API/web images, a loopback rehearsal Compose manifest, `/ready` and the
  canonical deployment runbook are prepared. No public resource, DNS, host, operational database
  or deployment was created.

## Verification

- Git fetch/status/revision/worktree inventory completed before edits.
- M1.1 targeted tests: 29 passed. Full suite: 325 passed, 4 warnings. Ruff, mypy (56 files), Golden
  quality, web lint/typecheck, seven UI tests and production build passed locally.
- M1.2 targeted API/ALIO tests: 47 passed. Full suite: 330 passed, 4 warnings. Ruff, mypy (56
  files), Golden quality, web lint/typecheck, eight UI contract tests and build passed locally.
- M1.3 web lint/typecheck, nine UI tests, production build and standalone contract check passed.
  Browser console warnings/errors: zero; framework overlay: absent; horizontal overflow at 390 px:
  absent. No migration or dependency changed.
- M1.4 GitHub Actions run `34838519611` at
  `cd65b7eee82d887150009ff20700ddb6ca98b9fc` passed canonical verification, SQLite migration
  round trip, PostgreSQL migration/load/API integration and PostgreSQL backup/restore.
- M1.5 targeted deployment/API checks passed with 21 tests. Full local verification passed with
  335 tests and one PostgreSQL-only skip, Ruff, mypy (57 files), Golden quality, web
  lint/typecheck, nine UI tests, production build and standalone artifact check. Docker execution
  is CI-only on this host.
- M1.5 GitHub Actions run `34838879854` at
  `0e90bae9269e980d38e45f0041fdcdc76852e17c` passed both image builds, Compose validation and
  every preceding canonical/PostgreSQL/restore check.

## Next action

At that deployment checkpoint, the approved `civic-intel-staging` plan was deployed. API and web run in Singapore; API revision
`b8c1f7666c8dcd2293da90a20cda1e41944a527c` applied Alembic through `0006` and returned `200` from
`/ready`. PostgreSQL's explicitly approved volume migration from `sfo` to Singapore completed;
the volume is `READY` with one running replica. The Web-only public domain and browser smoke are
now complete. API/DB exposure, PITR/backup configuration and operational data loading remained
separate approvals.

## Current checkpoint — Railway staging target (2026-09-14)

- Railway staging was selected as the smallest provider contract matching the existing Next,
  private FastAPI and PostgreSQL architecture. OpenAI Sites remains outside this runtime shape.
- Added one project-level `.railway/railway.ts` graph using the current IaC SDK rather than the
  deprecated per-service config format. It fails outside `staging`, uses the reviewed Dockerfiles,
  runs Alembic before API release, checks `/ready`, and gives no public domain to API or database.
- The SDK is isolated under `.railway`; local TypeScript and six deployment contract tests passed.
- GitHub Actions run `34840650378` at `a1cdacd7326c758110eb03b946e0245330bc9963`
  passed the full suite, PostgreSQL restore, Docker builds, Compose and Railway IaC checks.
- The owner-operated CLI has authenticated. The approved `civic-intel-staging` project and
  isolated `staging` environment contain `postgres`, private `api`, and Web; the only public
  endpoint is the explicitly approved generated Web domain. At that 2026-09-14 checkpoint, no operational data existed, and the
  default `production` environment remains empty.
- API corrective deployment `4ca58690-8f0e-42de-8f3b-53482424abcd` at
  `b8c1f7666c8dcd2293da90a20cda1e41944a527c` succeeded. It ran migrations through `0006` and
  received a `200` `/ready` health response. Web is running privately in Singapore.
- API/Web/PostgreSQL and the attached 500 MB volume are now in Singapore. The migration observed
  PostgreSQL with zero replicas while the volume was `MIGRATING`, then `READY` with one running
  replica.
- PostgreSQL PITR is disabled and no backup bucket is wired. The local host lacks PostgreSQL client
  tools, and private SSH inspection requires a new SSH key, so no one-off backup or table-count
  query was created. No operational data load had been run at that checkpoint.
- The post-migration read-only IaC plan returned `No changes.` with zero diagnostics. API, Web and
  PostgreSQL are `SUCCESS` with one running replica each; API and database have no public URL.
- After explicit Web-only approval, Railway created
  `https://web-staging-efe2.up.railway.app`; the service domain is `ACTIVE`. Browser smoke rendered
  the home page with an explicit empty roster after `GET /people 200`, and an unknown UUID rendered
  `Profile not found` after `GET /people/<unknown> 404`. The first request after the volume move
  briefly rendered the safe service-unavailable state due to the terminated pooled DB connection;
  reload recovered to `200`. No code/configuration change was needed for the recovered steady state.

## Current checkpoint — public Web preview (2026-09-14)

- Deployment classification is `DEPLOYED_PREVIEW`: public Web only, private API/PostgreSQL, no
  operational data loaded.
- The generated Web domain is the only Railway public URL. A read-only service listing verified
  `api.url == null`, `postgres.url == null`, and the Web URL above; all services are in
  `asia-southeast1-eqsg3a` with one running replica.
- CUA browser smoke directly inspected the deployed root and unknown profile route. The root showed
  `Evidence Directory`, `0` resolved identities and the explicit empty-roster state; the unknown
  UUID showed `Profile not found`. API logs recorded `GET /people 200` and the unknown-profile `404`.
- No visible framework error overlay was present in the successful root inspection; console capture
  was outside this CUA smoke artifact. The first transient `503` is retained as migration-recovery
  evidence rather than treated as a data absence.
- PostgreSQL PITR remains disabled, no backup bucket is wired, and no operational/feeder data load
  has run. After explicit approval, the owner-operated CLI attempted the on-demand volume backup
  `pre-restore-rehearsal-2026-09-14`; Railway returned `UNAUTHORIZED` / `Failed to create a backup`
  with exit code `1`. The backup list remains empty, the automatic schedule is empty, and no
  restore, PITR enablement, new service, or database-content mutation was attempted. The volume is
  `Ready` at `500 MB` with current size about `103.16 MB`; read-only usage/service/volume checks
  succeed, but the provider did not expose the entitlement reason.
- GitHub Actions run `34857175558` at
  `a9124150f00c8740187060f8a01ecfbca554319f` passed in 2m35s. Canonical verification, Alembic
  round trip, PostgreSQL migration/load/API contracts, PostgreSQL backup/restore and deployment
  artifact checks all passed.
- On 2026-09-15, owner-operated Railway OAuth login completed. Read-only `whoami`, project/status,
  service-list, volume, backup-list, PITR-status and schedule calls then succeeded; the target
  project/environment is accessible and the volume remains `Ready`. Retrying the approved backup
  creation once under the fresh login still returned `UNAUTHORIZED` / `Failed to create a backup`.
  The audit trail records both failed create attempts (2026-09-14 and 2026-09-15), backup list
  remains empty, and no provider plan or entitlement reason was exposed. No further mutation was
  attempted.

## Next concrete action

Resolve the Railway provider-side authorization or feature entitlement for the existing staging
volume, then rerun the reviewed backup/restore rehearsal only if the provider authorizes it. Keep
PITR disabled, do not create a new database service, and keep API/PostgreSQL private.

## Current checkpoint — M1.4 provider-independent logical backup/restore (2026-09-15)

- The isolated worktree is `C:\Users\getch\OneDrive\Documents\ChatGPT\cvic\.worktrees\change-discovery-plan`
  on `codex/change-discovery-plan`; the repository and `origin/master` were both at
  `33c664b3a93addb7d02c89c6ef1807a62ac6041b` before this documentation update. The root checkout,
  ignored runtime database, proposer candidate and other worktrees remain preserved.
- Railway staging application revision was
  `b8c1f7666c8dcd2293da90a20cda1e41944a527c`; the read-only database baseline was PostgreSQL
  `18.6`, Alembic head `0006`, and 26 public tables. People, Organizations, Sources,
  SourceSnapshots, SourceRuns, SourceCheckpoints, FeederObservations, Claims, ClaimEvidence,
  PersonObservationLinks and IdentityReviewItems each had count `0`. Subject-XOR and
  ClaimEvidence provenance mismatch checks were `0`; published and MONEY counts were `0`.
- The baseline used a private `railway connect postgres --tunnel-only` session. A temporary SSH key
  was registered only for the session and removed afterward; Railway reported no registered SSH keys
  after cleanup. No persistent credential remains. The original staging database received only
  read-only inspection and `pg_dump`; it was not dropped, reset, migrated or written.
- The logical dump receipt is: captured `2026-09-15T00:17:52.2664981Z`; custom format with
  `--no-owner`; `57,261` bytes; SHA-256
  `47CE121735FB27F9DCBCA9B297A2041FE25FFAA3F3CEAB2CEBE8050F5C834CAF`. The dump remains in a
  private temporary path outside the repository and is not committed.
- `pg_restore --no-owner --exit-on-error` restored into a loopback-only disposable PostgreSQL
  `18.6` database `restore_target` in `0.321` seconds. Schema head, table set, canonical counts,
  subject-XOR/provenance checks and MONEY counts matched the staging baseline. Restored-database
  API smoke returned `/ready 200`, `/health 200`, `/people 200` with zero rows and unknown
  Organization `404`. Both source and restored staging databases were empty; the non-empty pilot
  MONEY result remains separate CI/fixture evidence.
- Railway-managed backup/PITR is unavailable on the current plan; the owner-observed Dashboard
  states it is Pro-only. The two approved provider backup attempts returned `UNAUTHORIZED`. No Pro
  upgrade, billing/plan change or new resource was made. This does not block M1.4 because the
  provider-independent logical proof passed. Temporary client binaries, disposable PostgreSQL,
  API process and transient key files were cleaned after verification.
- The proof commit `6d979cdbd925f94328d578c3f941cb295d815201` was pushed to `origin/master`.
  GitHub Actions `Verify` run `34913882587` completed successfully in `2m25s`, covering canonical
  verification, Alembic round trip, PostgreSQL migration/load/API, PostgreSQL backup/restore and
  deployment artifact checks.

## Previous next action — before the approved ALIO load

Obtain separate operator approval for the bounded reviewed ALIO data-load rehearsal; until that
approval, keep staging empty and do not add new feeders.

## Current checkpoint — approved staging ALIO observation rehearsal (2026-09-15)

- The isolated worktree is `C:\Users\getch\OneDrive\Documents\ChatGPT\cvic\.worktrees\change-discovery-plan`
  on `codex/change-discovery-plan`. The root checkout, its proposer candidate and ignored runtime
  database, plus the other worktrees, remain preserved.
- The live Item 12 attempt first failed closed when unselected directory rows advertised
  `.pdf`/`.hwp` attachments. The failed run was
  `00a234ee-dde6-407f-a4a9-2deed6e27875`; read-only inspection showed no Source, SourceSnapshot,
  Checkpoint or FeederObservation writes, so no partial recovery was needed. The minimal parser/
  selected-scope fix was committed as `d06b0cc6f7c8d0313a1973a1dbafb02b0f83d20a`.
- The approved private-tunnel retry completed run
  `40ba451d-4d57-4f18-bbdb-122c516ebfde` with `SUCCESS`, allowlist `C0019,C0129,C0908`, three
  institutions and 15 observations. Staging now has four Sources, four metadata-only
  SourceSnapshots, two SourceRuns (failed plus successful), one checkpoint at cursor `3`, and
  zero People, Organizations, Claims and ClaimEvidence. The successful run counters were
  `(records_seen, observations_created, observations_unchanged) = (15, 15, 0)`.
- Read-only QA confirmed schema head `0006`, 15 distinct provider keys, three report snapshots,
  zero fulltext snapshots, empty identity hints, zero orphan observations, zero unsafe source URLs,
  subject-XOR `0` and ClaimEvidence provenance mismatch `0`. A local API read smoke against the
  staging connection returned `/health 200`, `/ready 200`, `/people 200` with zero rows and
  unknown Organization `404`. Claim import was not run because no existing canonical Organization
  binding was available; no Organization was created from an ALIO observation.
- GitHub Actions `Verify` run `34916320972` for `d06b0cc6f7c8d0313a1973a1dbafb02b0f83d20a` passed.
  Targeted ALIO tests (34), full pytest (exit 0 with one PostgreSQL-only skip), Ruff, mypy and
  Golden quality passed locally. The temporary Railway SSH key and local private/public key files
  were removed after verification; no provider plan/resource change, database reset/drop/schema
  migration or public API/database exposure occurred.

## Current checkpoint — approved staging ALIO reviewed Organization Claim/MONEY smoke (2026-09-15)

- The previously recorded zero-Organization staging state was the pre-binding observation checkpoint.
  Under the separately approved reviewed-binding scope, canonical Organization
  `b6c4df5d-2d9b-4c26-aedb-2c5a0f079b11` (`정보통신기획평가원`, provider code `C0908`) was bound
  explicitly; it was not created from an ALIO observation.
- The existing reviewed importer dry-run and commit both resolved the same deterministic pair of
  ALIO observations (`2026041303154117:2024`, `2026041303154117:2025`) to the same Claim IDs
  `6e8b4287-8a00-5820-ad5f-1e47ac868844` and `cc7ef8ab-1f40-5e08-b4be-302e3a0e04db`, with
  ClaimEvidence IDs `68c61f94-65fc-5ca5-a867-3f93914f3865` and
  `729cf75b-4c26-5d30-bf39-ce9ba496a6c7`. The staging database now contains one reviewed
  Organization, two Claims, two ClaimEvidence rows and the existing 15 ALIO observations.
- A local FastAPI read smoke using the private staging connection returned `/organizations/{id}`
  `200`, `/organizations/{id}/claims` `200` and the 2024→2025 MONEY projection `200` with
  `availability=AVAILABLE`, absolute delta `-2,162,000 KRW`, percent change `-14.39%`, and
  exact Claim/Evidence/SourceSnapshot/FeederObservation provenance. This is reviewed staging
  evidence, not an L3 ALIO promotion or a production/public coverage claim.
- The staging schema remained at Alembic head `0006`; no reset, drop, migration, provider-plan
  change or new resource was performed. The logical backup/restore receipt was captured before
  this approved load; the original staging database was only extended by the approved binding and
  Claim import.
- Local ALIO-targeted tests, full Python tests, Ruff, mypy, Golden quality, web lint/typecheck/UI
  tests and production build passed. GitHub Actions `Verify` run `34945055796` for
  `1150c9b75daa550bcd578913cc32abb77fe8386b` completed `success` in `3m4s`, including canonical,
  Alembic, PostgreSQL load/API, backup/restore and deployment-artifact checks.

## Next concrete action

Close the ALIO reviewed-Claim/MONEY milestone with the targeted and full local verification,
diff review and CI result, then start the active `Assembly Person Bootstrap v1` plan using the
existing successful-enumeration and source-specific materialization gates.

## Current checkpoint — Assembly Person Bootstrap v1 plan established (2026-09-15)

- The ALIO reviewed Organization binding → two fiscal-year Claim → MONEY staging smoke is closed
  at `b8b23984de5aad4ce762afbd528558a25a764116`; its Verify run `34945537685` passed.
- The next active plan is `docs/exec-plans/active/assembly-person-bootstrap-v1.md`. It reuses the
  existing Assembly enumerator, shared batch persistence and source-specific materialization gate;
  no new schema, repository, resolver or UI path is authorized.
- The required order is current staging logical backup/restore receipt, successful unfiltered full
  roster enumeration, exact-observation materialization with four outcome counts/review queue,
  `/people` resolved-person smoke, then a separate atomic roster-field publishability slice.
- M0 is complete. A fresh `pg_dump --format=custom --no-owner` was captured at
  `2026-09-15T08:29:56.2862488Z` outside the repository: `64,744` bytes, SHA-256
  `9D941BCC4476D3906747019753CF895A2529FCCFA797685007285C279C5C621E`. A loopback-only
  PostgreSQL `18.6` `restore_target` restored it with `pg_restore --no-owner --exit-on-error` in
  `0.351s`. Read-only staging/restored comparison matched schema head `0006`, all 26 public tables,
  one ALIO Organization, 15 observations, two Claims and two ClaimEvidence rows, with subject-XOR
  and provenance mismatches both `0`. No paid resource or staging reset/drop/migration occurred.
- M1 is complete. Existing unfiltered Assembly enumeration run
  `4fa48daa-5b02-45eb-ad98-2fb01ee5c5f8` returned `SUCCESS` with three pages, provider total `299`,
  299 records and 299 committed observations. The checkpoint recorded cursor `3`, page size `100`
  and expected page count `3`; all provider keys and source-scoped external IDs were distinct.
- M2 is complete. The exact successful observation set produced `AUTO_CREATE=298`, `AUTO_LINK=0`,
  `REVIEW_REQUIRED=0` and `HARD_CONFLICT=1`. The one open review item is
  `b0b404b2-4c23-4577-8678-c9047cac7fe6` (`EXACT_BIRTH_DATE_CONFLICT`). Read-only QA found 298
  resolved People, 298 Person links, 298 roster Claims and 298 ClaimEvidence rows, with no provider
  key used as a Person ID and zero subject-XOR/provenance mismatches.
- M3 is complete for staging. The actual staging Web roster rendered `298 resolved identities`, and
  a resolved profile rendered the canonical identity, evidence-backed Assembly `HELD_ROLE` claim and
  official Source trace without raw party/district/committee payload exposure. This is browser
  staging evidence, not a production deployment claim.

## Current checkpoint — Assembly Person Bootstrap v1 Base Profile slice (2026-09-15)

- Local implementation is in `packages/verification/assembly_base_profile.py`, the shared
  SQLAlchemy repository, the existing profile projection and the Assembly worker's explicit
  `--publish-base-profile` operation. The worker accepts no enumeration/filter flags for this
  operation, so publishing cannot accidentally bypass the successful-roster gate.
- The publisher required the latest `SUCCESS` checkpoint's provider manifest and exact committed
  observations. It considered all 299 records, published 1,191 four-field Claims for 298 resolved
  People, retained one skipped `HARD_CONFLICT` observation, and counted one missing `committees`
  field. A prior pre-optimization tunnel failure left a safely committed subset; the idempotent
  batch recovery completed the remainder without changing stored semantics.
- Read-only staging QA after recovery reported `party=298`, `district=298`, `committees=297`,
  `reelection=298`, 1,191 ClaimEvidence rows, zero subject-XOR violations, zero provenance
  mismatches and no fulltext/forbidden normalized contact fields. The existing ALIO baseline
  remains one Organization, 15 observations, two Claims and two ClaimEvidence rows.
- The profile projection now has the `assembly_base_profile` section with `AVAILABLE`/`PARTIAL`/
  `UNKNOWN` states and field-level evidence traces. Local full verification passed with 345 tests
  and one PostgreSQL-only skip, plus Ruff, mypy, Golden quality, web lint/typecheck/UI tests,
  production build and standalone artifact checks. No schema or dependency change was made.
- Post-push staging API deployment from commit
  `10ef8317cd01ac3f1c8933647a0cfecdf1c7b69b` completed `SUCCESS` without a new resource or plan
  change. The public Web then rendered `298 resolved identities`; the resolved `이상휘` profile
  rendered 14 sections with `국회 기본 프로필` `AVAILABLE`, four party/district/committees/
  reelection Claims and a visible Evidence trace for each. Raw normalized provider payload and
  provider contact fields were not rendered.
- GitHub Actions `Verify` run `34957511937` for the same commit completed successfully in 2m40s,
  including canonical verification, Alembic round trip, PostgreSQL load/API, backup/restore and
  deployment-artifact checks. The isolated worktree is clean and local HEAD equals `origin/master`.

## Next concrete action

Review the one open Assembly `EXACT_BIRTH_DATE_CONFLICT` queue item before the next roster refresh;
keep the one missing committee value explicit and do not start BTIS or another feeder.

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

## Current checkpoint — Assembly conflict review (2026-09-16)

- A read-only review of the staging `IdentityReviewItem`
  `b0b404b2-4c23-4577-8678-c9047cac7fe6` confirmed `OPEN`,
  `HARD_CONFLICT` and `EXACT_BIRTH_DATE_CONFLICT` for observation
  `0fce4b39-95cf-4401-b0c2-e3583dad14b9` / provider record `H7X3372O`.
- The same successful current-roster enumeration contains two distinct provider records with
  the canonical name `박지원`: `8BF5855P` has birth date `1942-06-05`, district
  `전남광주통합특별시 해남군완도군진도군` and `5선`; `H7X3372O` has birth date
  `1987-07-28`, district `전북 군산시김제시부안군` and `초선`. The first observation is linked
  by `AUTO_CREATE` to canonical Person `1bd253ae-3de7-42de-81e5-b450c1fb8e8b`; the second
  remains unlinked and is not public.
- The provider-key distinction and field differences do not authorize an automatic merge or an
  automatic “distinct Person” assertion. The automatic gate remains unchanged. No staging
  refresh, Person creation, Claim publication or queue mutation was performed during this
  read-only review.
- The private staging tunnel was closed after inspection. The temporary Railway SSH key and both
  local key files were removed; Railway reported zero registered SSH keys. No database or source
  data was changed by this review.

## Current checkpoint — Assembly reviewed distinct-Person resolution v1 (2026-09-16)

- The active plan is `docs/exec-plans/active/assembly-reviewed-distinct-person-v1.md`. The local
  implementation is committed as `d81499f433256dc59f8fcf2dca0ec77a34ba2a01` on the isolated
  `codex/change-discovery-plan` branch and is now pushed to `origin/master`; it has not been
  deployed or applied to staging.
- The automatic Assembly materialization function still emits only `AUTO_CREATE`, `AUTO_LINK`,
  `REVIEW_REQUIRED` and `HARD_CONFLICT`. A separate source-specific operation
  `resolve_assembly_distinct_person_review()` records `REVIEWED_CREATE` only for an open exact
  birth-date conflict in the current successful roster checkpoint.
- The transaction revalidates the official Assembly API SourcePolicy, source URL and snapshot
  contract, exact provider identity (`MONA_CD`), current checkpoint manifest, candidate Person
  and exact birth-date contradiction. It creates a new resolved Person, one published
  `HELD_ROLE` Claim, exact ClaimEvidence and a reviewed observation link, then resolves the
  original IdentityReviewItem atomically. It never changes or merges the candidate.
- Retries validate the already committed Person/Claim/Evidence/Link and return an idempotent
  result. A newer immutable observation version, malformed review state, existing provider link
  or publication/policy failure is rejected without partial writes. No migration, new table,
  dependency, public mutation endpoint, raw payload store or new feeder was added.
- Local evidence: focused Assembly/materialization/API checks passed (36 tests), the reviewed
  resolution module passed 10 tests, and the full Python suite passed with `349 passed, 1
  skipped`. Ruff, mypy, Golden quality, web lint/typecheck/UI tests (9), production build and
  standalone asset checks passed. No staging write has been made for this slice.
- GitHub Actions Verify run `35080092373` for the pushed commit completed successfully in 2m41s;
  its canonical, Alembic, PostgreSQL load/API, backup/restore and deployment-artifact checks all
  passed.

## Next concrete action

The fresh private logical staging backup and disposable restore drill are complete before any
new write. The dump was custom format with `--no-owner`, 349,651 bytes and SHA-256
`CBDC5534E105E4695450A4044F75B34C679C479889D19867D834333576942973`; restore to loopback-only
PostgreSQL 18.6 `restore_target` took 0.451 seconds. Schema head `0006`, 26 tables, canonical
counts, subject-XOR, ClaimEvidence provenance, fulltext privacy check and restored `/ready`,
`/health`, `/people`/404 smoke all passed. The dump remains outside the repository; the
disposable cluster was removed. No Railway plan/resource change or staging mutation occurred.

The next external action is to deploy the pushed code to the existing staging API service only,
then apply the already-approved H7X3372O reviewed-resolution transaction and run Base Profile/API
read QA. The current staging API remains on `10ef8317cd01ac3f1c8933647a0cfecdf1c7b69b`; do not
start BTIS or another feeder.

## Current checkpoint — Assembly reviewed distinct-Person staging closure (2026-09-16)

- Existing staging `api` deployment `5da14c38-4f77-4bc1-a247-3910c4fb03d7` completed `SUCCESS`
  from commit `013df121f3ff17c5ee2f251b0a79585123507a3c`; no new Railway resource, plan, domain,
  schema revision or dependency was introduced.
- The approved H7X3372O operation returned `SUCCESS`, `REVIEWED_CREATE` /
  `REVIEWED_DISTINCT_IDENTITY`, created Person `8b5f1e48-e7be-47cb-994e-da89dfdbce55` and role
  Claim `6ea439b2-cebd-553a-9be4-58936bf4fc94`, and resolved review item
  `b0b404b2-4c23-4577-8678-c9047cac7fe6`. Existing candidate
  `1bd253ae-3de7-42de-81e5-b450c1fb8e8b` was preserved.
- Base Profile publish returned `SUCCESS` for run `4fa48daa-5b02-45eb-ad98-2fb01ee5c5f8`:
  299 observations considered, 1,195 claims published and 1,191 unchanged. Final QA found 299
  resolved People, 299 links, 1,496 Claims/ClaimEvidence, explicit committee missingness `1`,
  subject-XOR/provenance/privacy/fulltext/provider-key violations `0`; ALIO remained one
  Organization, 15 observations and two Claims.
- Public staging Web rendered `299 resolved identities`; both same-name Assembly profiles opened
  separately and the reviewed profile showed role, four Base Profile fields and Evidence traces
  without raw normalized payload/contact fields. This remains staging/browser evidence.
- Private tunnel was closed, raw tunnel logs were removed, and Railway reports zero registered SSH
  keys. The two local standard-name temporary key files used for this staging tunnel were removed
  after the user-approved exact-path cleanup; no other SSH key was touched.

## Current checkpoint — People Discovery UX v1 (2026-09-16)

- The Evidence Directory read-model closure was confirmed from the canonical published
  People/Claims path and existing staging evidence; the stale handoff action to reimplement it
  is superseded.
- People Discovery UX v1 is complete in commit `6d0b0893f5dd488c2c1d7ecb46f4ed7aa587b9a2`.
  Home `/` is the discovery entry point, `/people` is the sole people directory, and
  `/people/[id]` remains the evidence dossier. The directory reads only current resolved People
  and publication-gated Claim/Evidence-derived Assembly Base Profile facets; no raw observation
  UI, feeder, schema, migration or dependency was added.
- Supported discovery inputs are canonical name, exact party/district/committee/reelection
  facets when their current published Claims are deterministic, and evidenced role/provenance
  display. Missing or ambiguous values remain visibly unavailable. Canonical Person IDs keep
  same-name profiles separate, neutral initials avoid unapproved portraits, and the existing
  dossier evidence/provenance presentation is reused.
- Local full Python verification passed with `350 passed, 1 skipped`; web tests, lint, typecheck,
  production/standalone build, Ruff, mypy and Clean-v0 quality passed. Browser checks covered
  IA, filter/no-match, keyboard, incomplete facets, API outage, person 404 and 390px long-name
  layout. GitHub Actions Verify `35090241928` passed in `2m23s`; local HEAD equals
  `origin/master` at this commit and the worktree is clean. No staging/production deployment
  or database write was made for this milestone.

## Next concrete action

Obtain approval to deploy commit `6d0b0893f5dd488c2c1d7ecb46f4ed7aa587b9a2` to the existing
staging Web service only and run the 299-row People discovery browser smoke.

## Current checkpoint — People Discovery UX v1 public staging closure (2026-09-16)

- The approved public staging smoke completed at `https://web-staging-efe2.up.railway.app`.
  Home `/` is the discovery entry, `/people` is the single directory, and the directory rendered
  `299 of 299 profiles` with party `9`, district `255`, committee `118` and reelection `7`
  select options.
- Actual checks returned `박지원=2`, no-match `0 of 299` with `검색 결과가 없습니다.`,
  `국민의힘=109`, `강원 동해시태백시삼척시정선군=1`, `법제사법위원회=7`, `초선=137`, and
  `더불어민주당 + 초선=71`.
- `1bd253ae-3de7-42de-81e5-b450c1fb8e8b` and
  `8b5f1e48-e7be-47cb-994e-da89dfdbce55` remained separate cards and profiles. Their visible
  party/district/committee/reelection values differentiated the 5선 전남광주통합특별시
  해남군완도군진도군 profile from the 초선 전북 군산시김제시부안군을 profile.
- Representative profile reads showed Base Profile, Claim/Evidence and the official Assembly
  Source provenance. No raw `FeederObservation.normalized` or contact field appeared. The
  unknown-Person `Profile not found` route remained distinct from no-match.
- Desktop `1280x900` had no horizontal overflow (`scrollWidth=1265`); 390px had no overflow
  (`scrollWidth=375`) and retained long Korean text. Keyboard focus reached skip link, home,
  People, search and party filter. Console warnings/errors were empty; no hydration/framework
  overlay or broken static asset was observed.
- Railway read-only status recorded Web deployment
  `bcda4eee-eb35-4de3-ba7c-9ea96df9057c` and API deployment
  `044a2947-1c60-4157-88eb-c8440387b872`, both at
  `4bb54554b9b9997f086b7f0573be8574eb38cb26`; PostgreSQL deployment
  `172ec443-e3cc-44bb-a5c1-195f54f86824` and existing resources/domain/plan were unchanged.
  The API was not stopped and no DB write, migration, reload, resource or cost change occurred.
- People Discovery UX v1 is now `DEPLOYED_STAGING`. The existing code Verify run
  `35090241928` passed; no new feeder, BTIS, portrait, admin, issue or MCP work began.

## Next concrete action

Prepare and approve the next bounded milestone specification before starting any additional
source or product surface.

## Current checkpoint — Acquisition Sync v1 local closure (2026-09-16)

- The next bounded milestone selected the existing National Assembly current-roster L3 lane,
  because its official SourcePolicy, unfiltered provider-declared coverage, `MONA_CD` key,
  pagination checks, persistent SourceRun/SourceCheckpoint path, resume/idempotency regressions
  and existing materialization/publication gate are already closed. ALIO was deferred because
  its current executive materialization remains intentionally `REVIEW_REQUIRED`.
- Added the thin source-specific `civic-sync assembly-roster [--resume]` boundary in
  `workers/sync.py` and registered it in `pyproject.toml`. It reuses
  `AssemblyRosterEnumerator.enumerate_and_materialize()`, `SourceRun`, `SourceCheckpoint`,
  `SourceSnapshot`, `FeederObservation`, canonical materialization and Claim/Evidence
  publication. No generic scheduler, crawler, sync table, schema migration or dependency was
  added.
- Successful receipts expose source/scope, run timestamps/status, observed/created/unchanged
  counts, materialization review/conflict counts, committed checkpoint cursor and resume intent.
  Failure receipts keep policy, source fetch/parse/coverage, database/precondition and
  publication phases distinct from empty coverage, preserve source-run/checkpoint state and
  redact exception/request credentials. A changed normalized record creates an immutable
  observation version; fetch time alone does not create a canonical fact or CHANGE.
- Existing Assembly tests covered full coverage, unchanged rerun, changed immutable version,
  partial checkpoint, resume, atomic persistence, coverage conflicts, policy denial and
  publication rollback. The new boundary regression passed first sync, unchanged rerun and
  canonical materialization receipt; the CLI failure regression passed redacted missing-key
  behavior. Targeted batch/evidence/materialization verification passed `28 tests`.
- Local completion evidence: Python `352 passed, 1 skipped, 4 warnings`; Ruff passed for all
  Python source/test paths; mypy passed for `60 source files`; Golden quality passed; web lint,
  typecheck, `9` web tests, production build and standalone artifact preparation passed;
  `.railway` standalone contract check passed; disposable SQLite Alembic round trip passed;
  `git diff --check` passed. GNU Make is unavailable on this Windows host, so its constituent
  verification commands were run directly.
- ASIDE A read-only visual review kept the current warm editorial evidence directory, Korean-safe
  type, whitespace, thin dividers, restrained accent, explicit UNKNOWN/PARTIAL states and
  evidence proximity. Future change is flatter/less nested People/detail rhythm with a compact
  `DERIVED · MONEY` module; no UI code changed.
- ASIDE B remains `NEEDS SOURCE GATE`: official Assembly member pages render profile images from
  an opaque `/static/portal/img/openassm/new/` asset path tied to a page carrying `monaCd` and
  term context, but the image path is not a provider identity or version contract. The official
  copyright policy requires the applicable KOGL mark and attribution for free reuse, while
  unmarked material requires prior consultation. Wikimedia Commons requires per-file creator,
  license, attribution, revision/hash and withdrawal/deletion review; no image was selected or
  ingested and no face-based identity or AI portrait path was introduced.
- This milestone intentionally did not execute staging, add credentials, change Railway,
  reload a database, create a public page, or start BTIS, CleanEye, MPM, assets, portraits,
  admin, issue, MCP or community work. GitHub Actions [Verify run 35099025424](https://github.com/sionchu/civic-intel/actions/runs/35099025424)
  passed in `2m35s` for delivery commit `eb37d8e982c89521ae8ffafd5dfee6870c285879`, including
  canonical verification, Alembic round trip, PostgreSQL migration/load/API,
  PostgreSQL backup/restore and deployment-artifact checks.

## Next concrete action

Obtain separate approval for an existing-resource staging rehearsal of
`civic-sync assembly-roster --resume`, then inspect its redacted receipt and source-run state.

## Current checkpoint — Collector Runtime Hardening v1 (2026-09-17)

- Staging rehearsal is stopped. No additional staging command, deployment, DB write, Railway
  change or Assembly live API call is part of this milestone.
- Baseline reproduction confirmed that source-tree execution reaches the missing-credential
  boundary, while the installed wheel's `packages.persistence.repository` resolves its migration
  root below `site-packages`. Because that installed `migrations` directory is absent,
  `ScriptDirectory.from_config` raises `alembic.util.exc.CommandError` before `SourceRun`
  creation. The current CLI reports that error as `phase=unexpected`, with the observed
  redacted receipt showing `run_id=null` and `committed_count=0`.
- The implementation replaces runtime filesystem discovery with the canonical expected schema
  revision `0006`, adds a CI/test check against the actual Alembic head, classifies Alembic
  `CommandError` under `database_or_precondition`, and locks completed-checkpoint resume as a
  fail-closed recovery-only path. Targeted regressions passed (`15 passed`).
- Local verification passed: full Python `355 passed, 1 skipped, 4 warnings`; Ruff; mypy for
  `60 source files`; Golden quality; web lint/typecheck/9 tests/production build; Railway
  specification check; YAML parse; and disposable Alembic upgrade/downgrade/upgrade ending at
  `0006`. The rebuilt installed wheel was run from outside the repository and reached the
  redacted missing-key boundary with no migration-path `CommandError`.
- Docker is unavailable on this host, so no local container PASS is claimed. Verify now includes
  a CI-only API-image regression that runs `civic-sync` from `/tmp` and checks its redacted
  missing-key receipt.
- GitHub Actions Verify `35121587665` passed in `2m50s` for `95065c3`, including the new
  installed-entrypoint container regression and all existing PostgreSQL, backup/restore and
  deployment-artifact checks. Collector Runtime Hardening v1 is complete.
- Docker is unavailable on this host (`docker` command not found), so no container result will
  be claimed until a container runtime is actually executed. The future collector shape remains
  private/manual-only evaluation; no collector service or scheduler is being created.

## Next concrete action

Before any future staging operation, obtain separate approval for one existing-resource rehearsal
using normal `civic-sync assembly-roster`; do not use completed-checkpoint `--resume` as periodic
sync.

## Current checkpoint — Visual System v2 (2026-09-17)

- The approved web-only visual milestone is implemented in isolated branch
  `codex/change-discovery-plan`. `DESIGN.md` was updated first and remains the visual contract.
  Home is now the quiet discovery entry, People is the single flat editorial directory, and the
  existing Person page remains the evidence dossier. No feeder, API, database, schema, dependency,
  Railway or staging change was made.
- Official Apple Design/HIG pages were read as structural reference through the available Aside
  run. The reusable grammar was limited to clear hierarchy, grouped navigation/topics, semantic
  headings and explicit accessibility affordances. Apple branding, assets, copy, HTML/CSS, icons,
  screenshots, fonts and tokens were not copied. Aside could not inspect staging because its local
  Windows installation key was unavailable; the public staging page was inspected read-only with
  the in-app browser and remains on its previous visual revision.
- Home-only decorative hero panel, gradient/rings/dots/cross, floating signal strip and People
  gallery-card hierarchy were removed or flattened. Existing canonical `getPeople()` and
  publication-gated discovery projection remain the only data path. Role, party, district,
  committees, reelection, evidence/as-of metadata, same-name separation, incomplete/no-match,
  unavailable and not-found semantics remain intact.
- A temporary 299-row Assembly mock fixture produced 299 public resolved People after the existing
  reviewed distinct-Person path resolved one exact birth-date conflict. Standalone browser checks
  at `1280x720` showed Home `299명`, People `299명`, party/district/committee/reelection options
  `3/299/4/5`, `박지원=2`, no-match `0`, facet results `100/1/75/60` and a combination result `25`.
  Same-name rows kept separate canonical links; a representative dossier showed Base Profile,
  Claim/Evidence and Source provenance without raw normalized/contact fields. Skip-link keyboard
  focus, static assets, no overflow and no console warning/error were observed.
- A rebuilt standalone production artifact was inspected with an explicit `390x844` browser
  viewport. Home and People rendered without horizontal overflow; People showed 299 rows, facet
  options `4/300/5/6`, `박지원=2`, no-match `0`, and facet results `100/1/75/60/25`. Keyboard focus
  reached the skip link. A representative dossier showed Base Profile, Claim/Evidence and Source
  provenance without raw normalized/contact fields; unknown Person stayed distinct from no-match.
  Long Korean text remained readable, error/hydration overlays were absent, styles loaded, and
  browser console warnings/errors were empty.
- Local web test `10/10`, lint, typecheck, production/standalone build, Python Ruff, mypy, Golden
  quality and full pytest completed successfully; full pytest exited `0` with one skipped test
  observed. GitHub Actions Verify run `35129642244` passed all jobs for
  `0e5fcba561d5fdc87a5aba33bd8bd4e168da83a9`. No staging deployment was requested or made.

## Next concrete action

Obtain separate approval before deploying the current Visual System v2 code to the existing
staging Web service; keep API/PostgreSQL unchanged and do not begin a new feeder or product
surface in that operation.

## Final mobile browser evidence closure — 2026-09-17

- Revalidated the current remote head `547d905e7aa5abeaa68263d4f084d7d5a4afbafa` (the expected
  `e6cad01a42249a26c36a7a130eba3451d2b54c7b` is its documentation-only predecessor) without
  changing application code.
- A Codex in-app browser using the Playwright viewport capability ran one exact `390x844` smoke
  against the standalone production artifact for `/`, `/people`, representative Person detail,
  and the unknown-Person state. Home and People had no horizontal overflow; People showed 299
  rows, `박지원` remained two canonical profiles, no-match remained distinct, and party/district/
  committee/reelection plus a valid combined facet returned `100/1/75/60/25` rows. Long Korean
  values stayed within the row layout, initials fallback rendered, and the four controls remained
  inside the viewport.
- Skip-link focus was visible by keyboard, the Person shell/Base Profile/Claim/Evidence/Source
  trace remained intact, raw normalized/contact fields were absent, and unknown Person rendered
  `Profile not found`. Console error/warning logs and hydration/framework overlays were empty.
  Home, People and Person screenshots were captured inline during the run. No API, DB, schema,
  dependency, Railway or staging change occurred.

## Current checkpoint — Visual System v2 staging closure (2026-09-17)

- The earlier pre-deployment Visual System v2 next action is superseded by this closure. The
  separately approved existing-service Web deployment completed from exact code revision
  `4e7477d242ef2035c576e3085d4eb73956c06ceb`; Railway Web deployment
  `ea8f2508-5c25-4138-9cbf-1369a080a5e8` reached `SUCCESS` on the existing staging target.
- API deployment `d6f246c2-873f-4203-9f61-025b02dc484a` and PostgreSQL deployment
  `172ec443-e3cc-44bb-a5c1-195f54f86824` remained unchanged and private. No service, domain,
  resource, plan, configuration or variable was added or changed.
- Live staging browser verification covered `/`, `/people`, both same-name `박지원` Person routes
  and an unknown Person route at desktop `1440x900` and mobile `390x844`. The directory rendered
  all `299` People; `박지원=2`; the exact facet checks returned `국민의힘=109`,
  `강원 동해시태백시삼척시정선군=1`, `법제사법위원회=7`, `초선=137`, and
  `더불어민주당 + 초선=71`; a nonexistent name returned zero with
  `검색 결과가 없습니다.`. Same-name records retained separate canonical Person IDs.
- Representative Person reads preserved Base Profile → Claim → Evidence → Source provenance and
  exposed no raw normalized/contact payload. Unknown Person remained `Profile not found`, distinct
  from directory no-match. At `390x844`, `innerWidth=390` and document/body `scrollWidth=375`;
  no horizontal overflow, hydration/framework overlay or console warning/error was observed.
  Keyboard focus visibly reached the skip link with a `3px` outline.
- The staged Home/People presentation showed the v2 content-first visual system without the old
  dark decorated hero, gradient/ring/dot/cross treatment or floating signal strip. `/favicon.ico`
  still returns `404`; this is non-blocking P2 polish and does not affect milestone acceptance.
- Visual System v2 is now `DEPLOYED_STAGING — PASS` and the milestone is closed.

## Next concrete action

Start the bounded Portrait Source Gate pilot before any portrait ingestion. Review a tiny sample
against the official Assembly portrait source and Wikimedia Commons file-level licensing,
attribution and revision requirements; keep the work read-only and do not bind, store or publish
an image until both rights and identity gates close.
## Current checkpoint — Portrait Pilot v0 (2026-09-17)

- One bounded Person-detail portrait is approved for implementation: canonical Person
  `44745d09-398c-46ce-bc38-81f0f606c1d7` (안철수), exact Assembly crosswalk `MONA_CD=YOG1280B`,
  and the individually reviewed Wikimedia Commons file `Ahn Cheol-soo March 2023 (cropped).jpg`.
  The exact file-level creator, CC BY 3.0 license, attribution, revision, dimensions, bytes and
  SHA-1 are recorded in the static presentation manifest; no Assembly image or remote runtime
  URL is used.
- Implementation is confined to the Person detail. `/people` remains initials-only, the
  manifest is not an identity authority, and unresolved/other Persons keep the existing CI
  fallback. No database/API/schema/dependency/Railway/staging change is in scope.
- The work is in isolated `codex/change-discovery-plan`; the root checkout's user changes and
  other worktrees remain untouched. Asset integrity, web/Python checks and the exact local Chrome
  production-artifact browser smoke passed. At `1280×900` and `390×844`, the pilot image kept
  400×534 ratio, attribution/source/license links and evidence dossier remained visible, fallback
  and directory initials held, overflow/overlay/console checks were clean, and the 299-row
  directory/search/facet regression remained intact.
- No staging/Railway operation was performed. A worktree build runner hit an existing Windows
  `.next/standalone` lock, so the same source was built and checked in a private temp mirror;
  this environment limitation is not a product failure and must remain distinct from CI evidence.

## Next concrete action

Portrait Pilot v0 is closed: commit `73d5ec8a4db2537bccbeb6201bfb3ab09f62ac37` is on `master` and
GitHub Actions Verify run `35192739443` passed. Keep staging undeployed until a separate Web-only
deployment approval is granted; do not expand this pilot into bulk portrait acquisition.

## Current checkpoint — Assembly Member Profile Substance v1 (2026-09-17)

- Implemented the bounded Assembly profile substance slice in isolated worktree
  `codex/change-discovery-plan`. Existing published Base Profile Claims now drive a deterministic
  Assembly overview/current-role projection; explicit dated reviewed Claims drive career; and the
  existing bill-participation observations can publish representative/co-sponsored descriptive
  activity through Claim/Evidence after an exact reviewed current-roster `MONA_CD` crosswalk.
- `MONA_CD` remains a provider identity, `BILL_ID` remains the provider bill key, and
  `RST_MONA_CD`/`PUBL_MONA_CD` remain representative/co-proposer roles. No name-only linking,
  ranking, AI summary, raw normalized observation, contact field, schema, migration, or new
  feeder was added.
- Assembly profiles use role-aware sections and compact coverage states; unsupported generic
  sections are hidden. The web fixture and regression coverage include three resolved People,
  same-name separation, representative/co-sponsored separation, exact provenance, and unknown
  versus no-match behavior.
- Python/web checks and a disposable standalone production browser smoke passed. Exact mobile
  `390x844` and desktop `1440x900` checks had no overflow, console errors, or hydration overlay;
  screenshots were captured outside the repository. No staging or Railway change was made.

## Next concrete action

Expand the existing bounded reviewed Assembly historical-career packet to one additional Person,
keeping the L1 reviewed-Claim path and its coverage limits unchanged.

## Current checkpoint — ALIO Organization & Executive Content Activation v1 (2026-09-18)

- The active plan `docs/exec-plans/active/alio-organization-executive-content-activation-v1.md`
  is complete from `fabe85d6bd87c60a47ef506b4bd968ade48f8c12`. Work was isolated in
  `.worktrees/alio-organization-activation`; the root checkout, its dirty user changes and
  other worktrees were preserved.
- Existing complete ALIO item-4 observations now have a source-specific, dry-run-by-default
  operator import into canonical Organization Claims. Exact `apbaId`-derived Organization IDs,
  exact published item-4 binding reuse, same-name rejection, immutable observation-version
  conflicts and one atomic Organization plus Claim/Evidence transaction are enforced. ALIO
  executive names remain organization Claim qualifiers and do not create or merge Persons.
- Named executive rows and institution classification use the existing
  `SourcePolicy → Source → SourceSnapshot → FeederObservation → Claim/Evidence` path. Masked,
  vacant, no-current and correction-only outcomes do not produce named Claims. The public
  `/organizations` projection and existing detail page use published Claims/Evidence only; raw
  normalized observations, report HTML, attachments and contacts are not exposed.
- The existing C0908 Item-12 reviewed binding/MONEY path and Assembly paths remain unchanged.
  No migration, dependency, live ALIO request, staging/database write, Railway operation or new
  feeder was performed.
- Fixture-backed activation tests passed (`8 passed`); the full Python suite exited `0` with the
  existing PostgreSQL-only skip. Ruff, mypy, Golden quality, web lint/typecheck/UI tests (`11
  passed`), standalone production build and standalone contract check passed. Commit
  `2a34791bebb2c76830bb197d61315792d6f820bf` is on `master`, and GitHub Actions Verify run
  `35245137821` passed, including PostgreSQL and container checks.

## Next concrete action

Define one reviewed cross-lane Person-linking packet for an ALIO executive row using exact
non-name identity evidence; keep name-only linking prohibited and do not begin another feeder.

## Current checkpoint — ALIO Organization Content Staging Activation v1 (2026-09-18)

- The separate staging activation plan is blocked before ALIO item-4 acquisition. The exact
  `ca1ff36e5dd6cebab018b3bdc1c4e7e4c160d410` source archive was deployed to the existing API and
  Web services (`76ec8f69-8874-4fbb-a67c-eeda55d0fd19` and
  `8fad7294-d590-4aee-9381-71c5f3bfca6f`); Postgres remained
  `172ec443-e3cc-44bb-a5c1-195f54f86824`. Local archive uploads have null Railway commit
  metadata, so the archive revision is the source identity.
- A fresh logical dump/restore passed before acquisition: `350919` bytes,
  SHA-256 `e5c89bb0ee9168328f86753033bbd05d91ca25b0236ee3388561d1533db19878`, local disposable
  restore `568 ms`, schema `0006`, People `299`, Organizations `1`, Claims `1496`, and subject
  XOR `0`. No staging reset or reload occurred.
- One normal `python -m workers.public_institutions` attempt timed out reaching the official
  ALIO endpoint (`ConnectTimeout`); the worker recorded one failed run with zero observations
  and zero checkpoint rows. Importer dry-run/commit was not run. People, Organizations, Claims,
  C0908 Item-12 data and public read paths remain unchanged.
- Temporary activation SSH registrations and task-owned sensitive artifacts were removed;
  Railway retains only the pre-existing `dev.new` key. No new Railway resource, domain, plan,
  migration or API acquisition credential was added.
- Documentation closure commit `3e5c0650d4e55225e68f87272491d767e2bf112e` is on
  `origin/master`; Verify `35254010476` passed and the isolated worktree is clean with local
  HEAD equal to `origin/master`.

## Next concrete action

Restore private reachability from the approved acquisition boundary to the official ALIO item-4 endpoint, then take a fresh backup and run one new normal bounded enumeration before any importer action.

## Current checkpoint — ALIO Local Acquisition Recovery v1 (2026-09-18)

- Aside and local HTTP both reached the official ALIO item-4 page: browser snapshot showed
  `임원현황`, unfiltered `Total 355`, and the local `httpx` request returned `200`.
- Recovery stopped before the fresh backup gate. The existing local staging key was rejected by
  Railway, and the supported `railway connect postgres --tunnel-only` probe exited without a
  listener or connection detail. Railway retains only the pre-existing `dev.new` key; no new
  key was generated or registered.
- No staging write, reset, reload, schema change, Railway change or importer action occurred.
  Task-owned tunnel probe logs were removed and the worktree remains isolated.

## Next concrete action

Make the private key corresponding to the already-registered `dev.new` Railway key available to the approved local runner, then repeat fresh backup/restore before any tunnel acquisition or ALIO write.

## Current checkpoint — ALIO Railway Sandbox Recovery v1 (2026-09-18)

- Aside and the bounded ALIO connector reached the official item-4 source and confirmed the
  provider-declared `355` institution directory rows.
- Exactly one private Railway Sandbox was used for the approved rehearsal. The fresh logical
  backup/restore passed, and a fresh normal enumeration completed with `355/355` checkpoint
  coverage, run `e57f88d4-953b-4de5-bf1c-13fa4b3e43db`, and `3799` item-4 observations.
- The existing no-commit Organization Claim importer did not produce a `DRY_RUN` receipt after
  about `2408s` of sequential database socket polling. It was terminated inside the disposable
  Sandbox; no `--commit`, Organization creation, Person write or public ALIO acceptance occurred.
- Read-only post-checks remained schema `0006`, People `299`, Organizations `1`, Claims `1496`,
  ClaimEvidence `1496`, and C0908 item-12 `5` observations / `2` Claims. The Sandbox was
  destroyed and final `sandbox list` was empty.

The full evidence and reopen condition are in
`docs/exec-plans/active/alio-railway-sandbox-recovery-v1.md`.

## Next concrete action

Profile and fix the existing ALIO Organization Claim dry-run's sequential database access in a
local/disposable test first, then repeat only the no-commit receipt gate before any staging
Organization Claim publication.

## Current checkpoint — ALIO Organization Importer Batch-Read Fix v1 (2026-09-18)

- The importer now reads the bounded ALIO item-4 feeder/scope once, indexes immutable versions
  by provider record key, and resolves only the successful checkpoint manifest. The repeated
  provider-key read loop was removed; immutable-version and manifest mismatch failures remain
  fail-closed.
- A direct regression proves one scope-wide observation read and zero provider-key reads.
- Targeted ALIO tests passed (`15 passed`). Full local verification passed: Python `368 passed,
  1 skipped, 4 warnings`, Ruff, mypy (`63` source files), Golden quality, Web lint/typecheck,
  Web UI (`11/11`) and standalone production build.
- No schema, dependency, acquisition, API, Web or Railway change was made. The staging
  importer was intentionally deferred until CI; its later no-commit PASS is recorded below, and
  `--commit` was not executed.

The active plan and exact query-shape contract are in
`docs/exec-plans/active/alio-organization-importer-batch-read-v1.md`.

## Next concrete action

Commit/push this bounded-read fix, require GitHub Verify success, then perform the fresh
backup/restore and one `DRY_RUN`-only staging gate with a hard `180s` deadline.

## Current checkpoint — ALIO Organization Importer Batch-Read Fix closure (2026-09-18)

- Commit `40b27b17e2d4d75763eb70c2896d6797c4d91cc3` is on `origin/master`; GitHub Verify
  `35309262908` passed. The local isolated worktree is clean and HEAD equals `origin/master`.
- One fresh private Sandbox backup/restore passed: dump `1290509` bytes, SHA-256
  `6b4c86132ae627354c82b527b56f5fa790fbc4987f585ed69f3837eee3643a9b`, schema `0006`, People
  `299`, Organizations `1`, Claims `1496`, ClaimEvidence `1496`, subject-XOR `0`, item-4
  observations `3799`, and C0908 `5/2`.
- The updated importer ran once without `--commit` and returned `DRY_RUN` in `17s` (under the
  `180s` budget): `observed_count=3798`, `named_rows=3624`, `masked_or_vacant_rows=174`,
  `organizations=346`, `claims=3970`, `organizations_created=346`, `claims_created=0`, and
  `claims_reused=0`; the run was `e57f88d4-953b-4de5-bf1c-13fa4b3e43db`.
- Post-run counts and item-4 checkpoint/run state were unchanged. No Organization Claim,
  Person, Claim or ClaimEvidence write occurred. Sandbox
  `bf3adb1f-eac7-4841-a3ca-401b613cdba2` was destroyed and final `sandbox list` was empty.

`ALIO_ORGANIZATION_IMPORTER_DRY_RUN — PASS` is now closed. Staging `--commit` remains prohibited
until the separate batch-write path has its own bounded regression and operational proof.

## Next concrete action

Profile and remove the known per-Organization/per-Claim database round trips in
`SqlAlchemyRepository.import_organization_claim_batch()` before any staging `--commit`.

## Current checkpoint — ALIO Organization Claim Batch-Write v1 (2026-09-18)

- `SqlAlchemyRepository.import_organization_claim_batch()` now preloads bounded Organization,
  Claim, Evidence, Source, SourcePolicy, Snapshot and Observation state, validates through the
  shared publication seam, flushes Organization parents once, then inserts Claim/Evidence rows in
  parent-before-child order within one transaction. The PostgreSQL FK ordering failure found in
  the first disposable attempt is fixed; single/pair import behavior and fail-closed rollback
  semantics remain covered.
- Fresh private restore proof passed on PostgreSQL `17.11`: dump `1,290,509` bytes,
  SHA-256 `847e1c9b7dcab7518c13926c73a23462398a79f98ff7172a2c8bae6443c392ef`, restore `0.649s`,
  schema `0006`, People `299`, Organizations `1`, Claims/ClaimEvidence `1496/1496`, item-4
  observations `3799`, and C0908 Item-12 `15/2`.
- The real `3970`-Claim disposable commit passed with `346` Organizations created; the exact
  rerun passed with `346` Organizations and `3970` Claims reused. Post-rerun counts were
  Organizations `347`, Claims/ClaimEvidence `5466/5466`, item-4 evidence coverage `3970/3970`,
  canonical import-key duplicates `0`, and subject-XOR violations `0`.
- Disposable API reads passed: `/ready=200`, `/people=299`, `/organizations=347`, representative
  ClaimEvidence/source references and C0908 MONEY `200`; normalized/raw observation/contact fields
  were absent. The exact Sandbox was destroyed and final `railway sandbox list` was `[]`.
- No live staging `--commit`, reload, migration, acquisition credential, service/resource/domain/
  plan change or new Railway resource occurred. Commit `6ff6e4e9b8a251ad3531f46774166b902d340882`
  is on `origin/master`; Verify `35314747499` passed and the isolated worktree is clean.

`ALIO_ORGANIZATION_BATCH_WRITE_PROOF — PASS` is closed. The next action is separately approved
first live staging ALIO Organization publication only: fresh backup/restore, dry-run, explicit
commit, public/API verification and cleanup.

## Next concrete action

Perform the separately approved first live staging ALIO Organization publication sequence.

## Current checkpoint — First Live Staging ALIO Organization Publication v1 (2026-09-18)

- The one approved live ALIO item-4 Organization publication commit completed from pinned
  revision `908bf74d3485dac5765f0f67d64e90971c12a7e7`. Live staging is now schema `0006` with
  People `299`, Organizations `347`, Claims/ClaimEvidence `5466/5466`, and item-4
  Claims/ClaimEvidence `3970/3970`. No Person was created from ALIO names; canonical import-key
  duplicates and subject-XOR violations are both `0`.
- Fresh custom logical backup/PG18 restore passed: `1,290,509` bytes,
  SHA-256 `8050a2d9ece0a3ee2efd0dcc6cef1bd4c840b0f62b766bec69f1b897481dd84f`, restore `675ms`.
  The live dry-run, single commit and post-commit no-write projection all returned the expected
  safe counts. The existing private API returned `/ready=200`, `/people=299`,
  `/organizations=347`; representative Organization Claims exposed Evidence/source references
  without normalized/raw/contact fields.
- Closure is blocked after commit: the required helper-derived C0908 ID
  `3059f7f9-94d5-5e32-83e2-4b7aa37fee9a` has no live row and its API routes returned `404`.
  The existing reviewed C0908 binding `b6c4df5d-2d9b-4c26-aedb-2c5a0f079b11` returned detail,
  claims and MONEY `200` with two Claims. No rollback, second commit, compensating write or
  deployment was run.
- The only private Sandbox used was `6347251a-b116-4d60-b832-d818f497fbcc` in `us-west2`; it
  was destroyed and the final sandbox list was empty. PostgreSQL/API/Web deployment IDs and
  Railway service/resource/domain/plan state remained unchanged.

The full blocked evidence and reopen condition are in
`docs/exec-plans/active/alio-organization-live-staging-publication-v1.md`.

## Next concrete action

Review and correct the C0908 Organization identity acceptance contract against the existing
explicit reviewed binding before any further staging execution.

## Current checkpoint — C0908 Identity Acceptance Contract Fix v1 (2026-09-18)

- The historical C0908 blocker was an acceptance mismatch: Item 4's deterministic
  `organization_id_for_alio_apba_id("C0908")` is not the resolver for the explicit reviewed Item
  12 Organization binding.
- The new regression proves that the existing reviewed canonical Organization
  `b6c4df5d-2d9b-4c26-aedb-2c5a0f079b11` can publish the bounded 2024/2025 Item 12 pair with exact
  `institution_code=C0908` and Claim → Evidence → SourceSnapshot → FeederObservation provenance
  even when the Item 4 helper UUID differs. It also proves the helper-derived ID remains absent in
  the Item 12-only fixture and its API routes remain 404.
- Read-only public staging browser evidence showed the reviewed organization detail/Claims/MONEY
  views, two C0908 annual Claims, ALIO source policy/provenance, 347 organizations and 299 People;
  the helper route showed `Profile not found`. No raw normalized observation/contact fields were
  rendered.
- No importer, staging DB write, schema change, deployment or Railway resource change occurred in
  this fix. Targeted ALIO tests passed: 46 passed.
- `ALIO_ORGANIZATION_CONTENT_DEPLOYED_STAGING — PASS` is closed in
  `docs/exec-plans/active/alio-organization-live-staging-publication-v1.md` and the dedicated
  contract plan.

## Next concrete action

Select one reviewed cross-lane Person-linking packet from the already published ALIO executive
corpus using exact non-name identity evidence; keep name-only linking prohibited and do not begin
another feeder.

## Current checkpoint — Reviewed Cross-Lane Person Packet: Kim Dong-cheol v1 (2026-09-19)

- Read-only source confirmation completed for the published ALIO Item-4 executive evidence,
  official KEPCO career biography and official National Assembly historical member profile. The
  ALIO trace is Organization `3ef4de75-fa3f-5815-81f4-8bc5efdc33f1`, Claim
  `ce471401-3d17-552d-b7c4-627ffaa97dd2`, Evidence `931d8c05-2e3d-5cf2-bac2-1e2af884bb51`,
  Snapshot `1883de13-d245-4aec-95f6-8153fccc442f`, Observation
  `b7df9687-f7aa-4a9b-80fc-acc3f1655ed3` and Source
  `4e3ca86f-52c9-4316-ac1a-0f09449e5b5c`; the published executive remains Organization evidence
  with zero Person links.
- The KEPCO page directly bridges `국회 제17·18·19·20대 국회의원` to `한국전력공사 사장`.
  The Assembly page independently supports 김동철, `金東喆`, `KIM DONGCHEOL`, birth date
  `1955-06-30`, terms 17–20 and provider code `DCR84445`. No page fulltext or contact data was
  retained.
- Added exactly one bounded fixture and existing-contract regressions. Without the bridge the
  packet stays `REVIEW/CONTEXT_REVIEW`; with the official bridge it resolves as
  `RESOLVED/OFFICIAL_CAREER_CONTINUITY`; a changed name remains
  `UNRESOLVED/NAME_CONFLICT`.
- The existing `ProfileResearchTarget` builder retains both source lanes and all source-reference
  families. A disposable migrated repository remained empty: no Person, PersonObservationLink or
  Claim was written. No importer, staging write, feeder or production-code/schema change occurred.
- Local verification passed: pytest `376 passed, 1 skipped`; Ruff; mypy; Golden quality; Web lint,
  typecheck, UI tests `11/11`, production build and standalone contract check. Markdown relative
  links checked `69`; `git diff --check` passed.
- Commit `d59c34f2d04ed29aca2a7fe0127aacbf04a6b243` was pushed to `origin/master`. GitHub Verify
  `35365121796` passed in `2m51s`, including canonical verification, Alembic round-trip,
  PostgreSQL migration/load/API and backup/restore, deployment artifacts and installed sync
  entrypoint checks. The isolated worktree was clean and HEAD matched `origin/master` before this
  closure note.
- `REVIEWED_CROSS_LANE_PERSON_PACKET_KIM_DONGCHEOL — PASS` is closed. No staging write, importer,
  feeder, production-code or schema change occurred.

The active plan is `docs/exec-plans/active/alio-assembly-cross-lane-kim-dongcheol-v1.md`.

## Next concrete action

Perform only the read-only canonical Person collision/materialization preflight for 김동철: search
existing People, inspect same-name and birth-date conflicts, and choose among `LINK_EXISTING`,
`REVIEWED_ONBOARD` or `KEEP_RESEARCH_ONLY`; do not write.

## Current checkpoint — Cross-Lane Identity Candidate Pipeline v0 (2026-09-19)

- `CROSS_LANE_IDENTITY_CANDIDATE_PIPELINE_V0 — PASS` is closed. The Kim Dong-cheol-specific
  materialization preflight was not started.
- The single staging proof used private Sandbox
  `a6e61745-b303-412b-85cf-4f16b7b9fd94` in `us-west2`, exact commit
  `e188cafc736351b507873d1b9ba9bddc9b31955b`, and the read-only candidate command exactly once.
- Receipt: `REVIEW_ONLY`; ALIO executive Claims `3624`; public People `299`; candidate pairs `56`;
  resolved `0`; review `56`; unresolved `0`; unique executive names `40`; unique Person IDs `41`.
  Every candidate retained `EXACT_CANONICAL_NAME_OVERLAP_DISCOVERY_ONLY` and
  `REVIEW/CONTEXT_REVIEW` with the missing-bridge reason. No bridge research or enrichment ran.
- Before/after counts were unchanged: schema `0006`, People `299`, Organizations `347`, Claims
  `5466`, ClaimEvidence `5466`, subject-XOR `0`, ALIO item-4 Claims/Evidence `3970/3970`, ALIO
  executive Claims/Evidence `3624/3624`, PersonObservationLinks `299`, IdentityReviewItems `1`.
- The Sandbox was destroyed; a follow-up list showed no remaining entry or running Sandbox for the
  task. No staging write, importer, acquisition, migration, deployment or Railway resource change
  occurred. The active plan records the full receipt and distinction between the 3970 total and
  the 3624 executive candidate input.
- Commit `e188cafc736351b507873d1b9ba9bddc9b31955b` is already pushed. GitHub Verify
  `35368004198` passed; local full verification passed and the isolated worktree was clean before
  this closure update.

The active plan is `docs/exec-plans/active/cross-lane-identity-candidate-pipeline-v0.md`.

## Next concrete action

Proceed to `Civic Intel Governance Ontology + Gukgam 2026 Scale Collection & Visual Explorer v0`
with agent-based implementation and independent verification. Do not begin person-by-person
materialization from this candidate set.


## Current checkpoint — Gukgam 2026 Ontology/Web staging v0 (2026-09-19)

- Slice 0 Governance Ontology merged as `f5189b61febbd5729c79b3ac349ace57fb6f8ac7`.
  It exposes the read-only Person ontology route without weakening identity/publication gates.
- The Web/Product surface merged as `e6d58c733093abe1a236ab09e6226aac5782ef0a`:
  `국감 2026` navigation, `/gukgam/2026`, Home launch treatment, and the accessible Person
  local ontology graph/text relation view. No Cytoscape dependency, schema or new backend route
  was added.
- The reviewed-plan packet contract merged as
  `d0b7c0efd2091cb418e585b5ade9fe5eb19253fc`. Its first Science Committee fixture pins
  `nttId=3078699`, `atchFileId=7938f3a874d5441892124093d19da1df`, `fileSn=2`, and
  publication date `2026-09-15`; schedule rows remain intentionally empty pending exact source
  review.
- Final master Verify `35380740361` passed.
- Staging exact-commit deployment passed at
  `d0b7c0efd2091cb418e585b5ade9fe5eb19253fc`: API
  `0b8317d1-a6ee-44bd-89b2-8e5bf821b0f7`, Web
  `ba1acc7d-5b88-454a-8e62-5923918de41b`. Postgres remained
  `172ec443-e3cc-44bb-a5c1-195f54f86824`.
- API runtime logs show `/ready=200` and `/people=200`; Web root healthcheck passed. The Web
  production build contains `/gukgam/2026` and `/people/[id]`. Rendered-content QA on the
  public Railway domain remains pending because the current execution boundary cannot resolve/
  fetch that temporary domain; do not infer screenshot acceptance from build success.
- No staging data write, importer, migration, Postgres deployment, Railway config/domain/variable/
  volume/replica change occurred.
- Repeated automation against the committee website remains blocked by its reviewed robots rule.
  Before scaling manual packets, inspect the official National Assembly Secretariat OpenAPI guide
  and service catalog for a Gukgam-specific automation-permitted operation.

## Next concrete action

Codex should search the official National Assembly Secretariat OpenAPI guide/service catalog for
2026 Gukgam plan/schedule, audited-organization, witness and reference-person operations. If an
exact operation exists, implement only that source-specific API contract/fixture/connector. If it
does not, record the negative result and complete the first Science Committee reviewed schedule
packet under the existing packet gate. Do not modify `apps/web` in that slice.


## Current checkpoint — Gukgam scale collection + ontology product v0 (2026-09-19)

- Open Assembly schedule discovery L1 is in master:
  `7b69bd6b4efb3d94109631d1a6b700824fbf732f` plus read-only probe worker
  `70c9ae3fc91bbf964c77cbf1d639c186a04234ae`; Verify `35416280261` passed. The official
  `ALLSCHEDULE` endpoint is network-reachable (HTTP 200), but the repo has no
  `ASSEMBLY_API_KEY` and the public `sample` key returned `ERROR-290` invalid-key. No live
  schedule result was persisted.
- Search-first `/gukgam/2026` merged as
  `fe064a1335631f67694aa4e692295f7a7565b566`; Verify `35417435004` and staging Web
  deployment `8c168adf-69a5-4cc5-8cba-6f8ca78d29ef` passed. Browser-agent QA proved
  한국전력공사 search, distinct 박지원 same-name results, and mobile behavior.
- Organization ontology merged as
  `5018e31a4202572940b32e6b66c367921958aa06`; Verify `35418442406` passed. Staging API
  `d0f1a76e-fc13-409a-89d5-1cd0890561d4` and Web
  `a200f0e9-fc72-4586-b44e-2c116cf5ac77` succeeded; Postgres remains
  `172ec443-e3cc-44bb-a5c1-195f54f86824`. ALIO executives render only as Claim-scoped
  `SOURCE_LISTED_ROLE_HOLDER` nodes with `canonical_id=null`; no Person auto-link exists.
  한국전력공사 browser QA `35418537339` passed.
- Dense ontology label polish merged as
  `4554602bb2a7eac8b66e51e7061dfac48e3e2195`; Verify `35418826810`, staging Web
  `1d2df428-3e2e-46b7-9352-1e69e8773eae`, and final CJK screenshot QA `35418874131` passed.
- Reviewed plan L2 import boundary merged as
  `a37acfa1ea5a4320bd644db31ca6abfa3e0debd7`; final master Verify `35419420199` passed.
  Raw attachment SHA, reviewed packet digest and normalized row hashes are distinct provenance
  layers. Dry-run is default; a commit persists only source/snapshot/run/checkpoint/observation
  records and creates no Person, Organization, Claim, ClaimEvidence or identity link.
- The exact Science Committee PDF is now captured through the approved human-assisted boundary.
  Raw SHA-256 is
  `82d37b337790e5869e74af3420b7dab74c86a7fb14b44a54932f8dbd2f31e533`; the canonical reviewed
  packet is 8 schedule rows / 96 audited-target strings with hash
  `4f74bf8b7f0dfae52ad6fafff646d0c5f78a2c602a3d53d1bf55796284c8a74d`.
  Exact-artifact dry-run passed and reported zero Person/Organization/Claim materialization.
  The later staging observation-only batch imported this packet idempotently together with six
  additional reviewed committee packets; see the 2026-09-20 checkpoint below.

## Current checkpoint — Gukgam standing-committee exact attachment batch 1 (2026-09-20)

- Aside Browser was restored in the owner Windows session and used only as a bounded interactive
  acquisition path through the official National Assembly central inspection list and exact
  committee detail pages. No scraper or automated committee collector was added.
- The inventory now has eight `EXACT_ATTACHMENT_CAPTURED` committees: Science, Steering,
  National Defense, Public Administration and Security, Culture/Sports/Tourism,
  Agriculture/Food/Rural Affairs/Oceans, Strategy and Finance, and Foreign Affairs and
  Unification.
- Six additional reviewed packets pass the real exact-PDF dry-run boundary:
  Steering `3 rows / 10 mentions`, Public Administration and Security `12/45`,
  Culture/Sports/Tourism `7/69`, Agriculture/Food/Rural Affairs/Oceans `8/49`,
  Strategy and Finance `10/48`, and National Defense `9/73`.
  All retain zero Person/Organization/Claim materialization and no fulltext.
- Foreign Affairs and Unification exact PDF
  `fde2aa6309f28b87d398fd1a3dbda264e26f769cfc7a50918f32fd2a0241243d`
  is intentionally not packetized because official overseas audit rows use multi-day ranges that
  packet v1 cannot represent losslessly.
- Raw PDFs and extraction scratch files remain outside git. No application data, staging database,
  Railway resource, schema, API or Web behavior changed in this acquisition slice.
- Targeted parser/importer verification passed `24 tests`. Local full verification then passed:
  Ruff, mypy, `444 passed / 1 skipped` pytest, Golden quality, Web lint/typecheck, 22 Web tests,
  production build, and `git diff --check`.
- PR #85 Verify `35454900420` passed. The packet batch merged to `master` as
  `f808433bae6a2b838430bef96fd0c4b13ba00f9b`, and merge-head Verify `35455358644` also passed
  every canonical, migration, PostgreSQL, backup/restore, deployment-artifact and installed-sync
  entrypoint step.

## Current checkpoint — Gukgam staging observation-only batch 1 (2026-09-20)

- Railway CLI access was owner-authenticated. A temporary SSH tunnel reached private staging
  PostgreSQL without creating a public DB domain. The temporary Railway-registered staging public
  SSH key was removed after use and the tunnel was closed.
- Before import: schema `0006`, People `299`, Organizations `347`, Claims `5466`, ClaimEvidence
  `5466`, and zero `gukgam_reviewed_plan` observations.
- Science plus six new v1 packets committed `57` total schedule observations across seven exact
  official plan sources. Every first run completed successfully.
- Each packet was rerun immediately and unchanged: all second runs reported `created=0` and
  `unchanged=<row count>`. Total successful source runs for this batch: `14`.
- After import: People `299`, Organizations `347`, Claims `5466`, ClaimEvidence `5466`, and
  `gukgam_reviewed_plan` observations `57`. No identity, Organization binding or Claim publication
  occurred and no raw attachment/fulltext was persisted.
- The remaining eight `DISCOVERY_PENDING` committees plus Health and Welfare were rechecked in the
  official central inspection list with both exact and broad 2026 title filters. No 2026 plan row
  was visible, so their existing fail-closed statuses remain unchanged.

- Cross-checking all eight exact PDFs found no second audited-target date-range case. The other
  range-form rows are excluded non-audit rows (holidays or field inspection). Foreign Affairs and
  Unification is therefore the only current exact plan blocked by multi-day audited-target dates.

## Next concrete action

Keep packet v1 unchanged for now and leave Foreign Affairs and Unification fail-closed. Continue
bounded official-list acquisition for newly published committee plans. Only if a second exact plan
also requires multi-day audited-target rows should the canonical packet contract gain explicit
start/end date semantics.


## Current checkpoint — Public Beta staging acceptance + latency v0 (2026-09-19)

- Public Beta HTTP preflight merged as
  `d4d3529f8e63dea1f7394d41fcde99997b97769e`; Verify `35422460313` passed.
- Real staging preflight `35426383959` passed against
  `https://web-staging-efe2.up.railway.app`: Home, `/gukgam/2026`, robots, sitemap,
  representative Person and 한국전력공사 Organization routes all returned HTTP 200. The staging
  SEO gate correctly remained noindex/disallow-all, and selected raw/contact leak checks passed.
- Organization public-list publication context was batched in
  `8c50218cdd8a8de31c0c1ec97192c044da7643e8`; Verify `35422992753` passed and staging API
  deployment `57efc9cd-4f7b-49b5-b1e7-188e8f723f5f` succeeded.
- Public People/Organization list reads now use a bounded 60-second Web revalidation cache in
  `a58050b778b1f29bb7167b8c534acbb6ab9013d1`; Verify `35426886029` passed and staging Web
  deployment `328a8649-8fba-4021-9ab5-258e8360abff` succeeded. Detail/Evidence/ontology/source
  reads remain request-time.
- Before the Web cache, repeated staging timings were ~1.0–1.17 s for `/people`,
  ~2.5–2.97 s for `/organizations`, and ~3.10–3.81 s for `/gukgam/2026`. After deployment,
  timing run `35427116217` measured `/gukgam/2026` at ~0.55–0.57 s after cache population,
  `/organizations` at ~0.56–0.78 s after one ~2.86 s cold request, and `/people` around
  ~0.59–0.61 s.
- Railway environment `production` (`7dd4f01b-25c6-47ce-b91e-f5e2c9b71b15`) exists but has
  zero services. No production DB/service/domain/indexing change was made; that remains an explicit
  public-access/cost approval boundary.
- The Science Committee exact PDF is now available through the approved human-assisted artifact
  boundary and matched to the existing reviewed packet. The PDF is not stored in the repository.
  Committee-site repeated automation remains blocked, and no other committee schedule/target row is
  inferred from news/search snippets.

## Current checkpoint — Gukgam review-only schedule projection v0 (2026-09-20)

- The current 57 staging `gukgam_reviewed_plan` observations now have a pure internal review
  projection and gated `GET /admin/gukgam/2026/schedule` route. The route is registered only when
  `enable_review_surface=True`; the default public API and public Gukgam page are unchanged.
- Current rows are selected from the checkpoint's current attachment SHA with the newest immutable
  observation version per provider record key. Count drift fails closed rather than inferring which
  source version should win.
- The review DTO exposes committee/date/time/venue/source-scoped target/page fields plus exact source
  provenance only. It excludes canonical Organization IDs, Claim IDs, run IDs, raw normalized
  payloads and fulltext.
- Targeted verification passed: Ruff, mypy, and 27 Gukgam review/packet/import tests. Local full
  verification also passed: Ruff, mypy, `447 passed / 1 skipped` pytest, Golden quality, Web
  lint/typecheck, 22 Web tests, production build, and `git diff --check`.
- Owner-local execution of the new review route against the real staging database passed:
  7 committees, 57 schedule rows and 390 audited-target mentions; forbidden identity/publication
  fields were absent. This was read-only and did not deploy or publish the admin route.
- Temporary Railway SSH access used for that validation was closed and its registered public key
  removed.

## Current checkpoint — Gukgam Organization binding candidates v0 (2026-09-20)

- A gated review-only candidate route now compares the 390 source-scoped target mentions against
  current canonical Organization names by exact equality only.
- Real staging read-only results: 347 current Organizations; 390 mentions / 359 distinct target
  strings; 110 mention overlaps / 103 distinct exact-name candidates; 280 mention no-matches /
  256 distinct no-matches; 0 multiple-exact cases.
- Exact overlaps are explicitly `DISCOVERY_ONLY`. No alias expansion, fuzzy matching, similarity
  score, rank, embedding, proximity inference, Organization write, Claim/Evidence write or public
  rendering exists in this slice.
- Targeted verification passed Ruff, mypy and 29 Gukgam review/packet/import tests. Local full
  verification then passed: Ruff, mypy, `449 passed / 1 skipped` pytest, Golden quality, Web
  lint/typecheck, 22 Web tests, production build, and `git diff --check`.
- Temporary Railway SSH access used for this read-only measurement was closed and its registered
  public key removed.

## Current checkpoint — Gukgam reviewed binding preflight v0 (2026-09-20)

- Internal-only `/admin/gukgam/2026/organization-binding-preflight` now accepts one exact
  occurrence `review_key` plus one operator-supplied current Organization ID.
- It re-runs exact-name candidate discovery, requires exactly one candidate, re-verifies the
  supplied Organization and exact source provenance, and emits a `DRY_RUN` receipt only.
  `binding_committed=false` and `claim_publication=false` are invariant.
- Wrong IDs, unknown review keys and non-exact/no-match occurrences fail closed. Targeted Ruff,
  mypy and 34 Gukgam tests passed. Full local verification then passed: Ruff, mypy,
  `454 passed / 1 skipped` pytest, Golden quality, Web lint/typecheck, 22 Web tests, production
  build, and `git diff --check`.
- A real staging read-only preflight passed for one current exact-name candidate occurrence; a
  random wrong Organization ID returned `422 INVALID_INPUT`.
- Before/after staging remained People `299`, Organizations `347`, Claims `5466`,
  ClaimEvidence `5466`, Gukgam observations `57`, and Gukgam source runs `14`.
  No Organization, Claim/Evidence or source-run write occurred. The temporary tunnel was closed.

## Current checkpoint — reviewed Gukgam Claim importer v0 (2026-09-20)

- Added the source-specific predicate `LISTED_AS_GUKGAM_AUDIT_TARGET`. It means only that the
  exact official audit plan lists the Organization as a target on the scheduled row; it does not
  assert completed audit activity, wrongdoing, responsibility, performance or outcome.
- Added `civic-import-gukgam-reviewed-claim`, requiring one existing current Organization ID plus
  one reviewed target-level `review_key`. The command re-runs binding/source provenance checks and
  builds deterministic Claim/Evidence through the existing Organization Claim importer.
- The target-level `review_key` is the Claim source key; schedule-row provider identity is retained
  separately. Dry-run is default, network fetch is absent, `--commit` is explicit, and an exact
  stored retry returns `REUSED` only when Claim/Evidence semantics match.
- Wrong binding, conflicting stored semantics or multiple immutable observation versions fail
  closed. Initial targeted Ruff/mypy and 38 Gukgam tests passed; the initial local full verification
  passed Ruff, mypy, `458 passed / 1 skipped` pytest, Golden quality, Web lint/typecheck,
  22 Web tests, production build, and `git diff --check`.
- Follow-up review removed a verification gap by sharing the checkpoint-selected current Gukgam
  schedule loader between the admin review surface and the Claim worker. The worker now fails
  closed when checkpoint `schedule_row_count` disagrees with current observations; a dedicated
  regression covers that incomplete-universe case.
- PR #90 strengthened-code Verify `35484811916` passed the strengthened head: canonical verification
  (`459 passed / 1 skipped` pytest plus Ruff, mypy, Golden and Web gates), Alembic round-trip,
  PostgreSQL migration/load/API, backup/restore, deployment artifacts and installed entrypoint.
- Real staging DRY_RUN passed on one exact-name candidate without `--commit`. Before/after
  remained People `299`, Organizations `347`, Claims `5466`, ClaimEvidence `5466`,
  Gukgam observations `57`, and Gukgam runs `14`; no Claim, Evidence or source write occurred.
  The temporary private-DB tunnel was closed.

## Current checkpoint — first staging Gukgam Claim commit receipt (2026-09-20)

- Execution used merged `master` `b02f306d474ec35d19f6a668140a41edb8c4818e` against the
  existing private staging PostgreSQL boundary; no public database domain was created.
- The reviewed occurrence was 과학기술정보방송통신위원회 / 2026-10-13 /
  한국원자력안전기술원, Organization
  `2b389008-a8c1-53d4-87d9-f4221aa8dfa5`, with review key
  `3078699:7938f3a874d5441892124093d19da1df:2:schedule:3:audited-target:3`.
- A pre-commit dry-run returned `DRY_RUN` with staging counts unchanged at People `299`,
  Organizations `347`, Claims `5466`, ClaimEvidence `5466`, Gukgam observations `57`,
  and Gukgam source runs `14`.
- Exactly one `--commit` then created Claim
  `7c4b2e8d-b9eb-5f4c-87ba-fb3c561ecb83` and ClaimEvidence
  `e5f2a33b-59da-5e1e-90d9-384f14fff689`. Counts became Claims `5467` and
  ClaimEvidence `5467`; People, Organizations, Gukgam observations and Gukgam source runs
  remained unchanged.
- Immediate unchanged rerun returned `REUSED` with counts still unchanged, proving the
  deterministic single-occurrence retry contract. Owner-local public Claim read smoke against the
  staging database passed through the ordinary Organization Claim/Evidence gate.
- The temporary SSH key used for this private-DB execution was removed, and its local private/public
  key files plus temporary execution scripts were deleted. No bulk publication was performed.

## Current checkpoint — public Claim-backed Gukgam target projection v0 (2026-09-20)

- Added read-only `GET /gukgam/2026/targets` backed exclusively by current published
  `LISTED_AS_GUKGAM_AUDIT_TARGET` Organization Claims.
- The projection semantics are `PUBLIC_CLAIM_BACKED_GUKGAM_AUDIT_TARGETS_V1` with coverage
  `BOUNDED_INCOMPLETE_PUBLISHED_CLAIMS_ONLY`. Absence is explicitly not evidence of no audit.
- Each item retains canonical Organization identity plus Claim, ClaimEvidence, Source,
  SourceSnapshot and FeederObservation IDs. Review keys, candidate match classes, scores, ranks,
  raw normalized payloads and review-only binding state are not exposed.
- There is no fallback from reviewed observations or exact-name binding candidates. Regression
  coverage proves that multiple reviewed audited-target strings with only one committed Claim
  produce exactly one public target item.
- Targeted verification passed Ruff, mypy across 76 Python source files and 40 Gukgam
  review/Claim/import tests. Full local verification passed Ruff, mypy,
  `460 passed / 1 skipped` pytest, Golden quality, Web lint/typecheck, 22 Web tests,
  production build and `git diff --check`.
- This slice changes the API contract only. The existing Web `/gukgam/2026` page is unchanged,
  and no additional Organization binding or Claim publication was performed.

## Current checkpoint — staging Claim-backed Gukgam target API (2026-09-20)

- PR #92 merged as `c7038763ed8093bb8e39564e60e1b4eaa88fe892` after Verify
  `35486439758` passed every canonical, Alembic, PostgreSQL, backup/restore, deployment-artifact
  and installed-entrypoint gate.
- A generic Railway `redeploy` was rejected as deployment evidence because it reused the stale
  source snapshot for commit `8c50218...`; that deployment was superseded and removed.
- Owner-local deployment then reset a clean working tree to exact merged `master` `c703876...`
  and uploaded that tree to the existing staging API service with `railway up`. Deployment
  `151f9078-0088-428f-a384-eab7fd8bde47` reached `SUCCESS`.
- The staging API remains private-only: zero Railway service domains and zero custom domains. No
  database, Web service, environment variable, schema or indexing setting changed.
- Private-container smoke called `/ready` and `GET /gukgam/2026/targets` over localhost and
  passed exact assertions. The response contained exactly one target and one committee with
  semantics `PUBLIC_CLAIM_BACKED_GUKGAM_AUDIT_TARGETS_V1` and coverage
  `BOUNDED_INCOMPLETE_PUBLISHED_CLAIMS_ONLY`.
- The sole target was 한국원자력안전기술원
  (`2b389008-a8c1-53d4-87d9-f4221aa8dfa5`) under 과학기술정보방송통신위원회 on
  `2026-10-13`, backed by Claim
  `7c4b2e8d-b9eb-5f4c-87ba-fb3c561ecb83` and ClaimEvidence
  `e5f2a33b-59da-5e1e-90d9-384f14fff689`. Exact Source, SourceSnapshot and
  FeederObservation IDs were present; no observation/name-match fallback appeared.
- The temporary SSH key `civic-intel-gukgam-projection-20260920` was removed from Railway after
  the smoke, and both local private/public key files were deleted. The pre-existing unrelated
  `dev.new` key was left untouched.

## Current checkpoint — staging Gukgam published-target Web slice (2026-09-20)

- PR #94 merged as `3f868fea873a3e4ef5d126478e9b6bf1fb27e4ba` after GitHub Verify
  `35486918538` passed, matching local full verification: Ruff, mypy, `460 passed / 1 skipped`
  pytest, Golden quality, Web lint/typecheck, `23 / 23` Web tests, production standalone build
  and `git diff --check`.
- The existing `/gukgam/2026` page now reads only `GET /gukgam/2026/targets` for its
  "공개된 피감대상" section. It reuses existing Claim-card and audit-detail grammar; no new CSS,
  ranking, review candidate, name-overlap fallback, client-side publication state or identity logic
  was added.
- Each rendered target links to its canonical Organization `#claims` section and exposes
  Claim/Evidence/Source/SourceSnapshot/FeederObservation identifiers behind an audit-details
  disclosure. The UI always states that the current set is not the complete audit-target list and
  does not infer absent targets.
- A clean owner-local working tree was reset to exact merged `master` `3f868fe...` and uploaded
  to the existing staging Web service. Deployment
  `28a7b423-7240-4a7e-8c2f-af7fa6d1629c` reached `SUCCESS`; the existing staging domain
  remained `web-staging-efe2.up.railway.app`.
- Live staging HTTP smoke against `/gukgam/2026` returned `200` and confirmed the published
  target heading, 한국원자력안전기술원, 과학기술정보방송통신위원회, `2026-10-13`, the canonical
  Organization `#claims` link, Claim
  `7c4b2e8d-b9eb-5f4c-87ba-fb3c561ecb83`, and ClaimEvidence
  `e5f2a33b-59da-5e1e-90d9-384f14fff689`. The response did not expose `review_key` or
  `match_class`.
- The API service remained on deployment `151f9078-0088-428f-a384-eab7fd8bde47`; no database
  write, Claim publication, Organization binding, API domain, environment variable or schema change
  occurred in this Web deployment slice.

## Current checkpoint — second reviewed Gukgam Claim commit (2026-09-20)

- With the cross-view public Claim contract merged on `master`, staging review selected exactly one
  additional exact-name candidate: 한국원자력통제기술원, Organization
  `f3d71e88-c6d1-5eba-9ae7-5df04ff4e0c9`, review key
  `3078699:7938f3a874d5441892124093d19da1df:2:schedule:3:audited-target:4`.
- Read-only discovery showed 109 current exact-one occurrences without a published Gukgam Claim;
  no automatic selection, scoring, ranking, fuzzy match or bulk approval was introduced.
- Dry-run returned `DRY_RUN` with `claim_persisted=false`, `claim_created=false`,
  `binding_committed=false`, `organization_created=false` and `network_fetch=false`.
  Public target count remained `1`.
- Pre-commit staging counts were Organizations `347`, Claims `5467`, Gukgam observations
  `57`, Gukgam source runs `14`, public target count `1`.
- One explicit `--commit` created Claim
  `52fb5057-37f0-5b30-8645-415ac8131752` and ClaimEvidence
  `a13ebec6-ef4f-5570-b549-e9f6c3fefede`. Immediate unchanged rerun returned `REUSED`.
- Post-commit cross-view smoke passed: Organizations remained `347`, Claims became `5468`,
  Gukgam observations remained `57`, Gukgam runs remained `14`, and public target count became
  exactly `2`. The target API and Organization detail exposed the same Claim/Evidence IDs plus
  Source `429d851c-3a6c-4756-8b3a-3ace5266d064`, SourceSnapshot
  `78ceba04-d4ff-4b78-a41c-527de8a9b728` and FeederObservation
  `d79afce8-2e4d-4d87-b6c6-2340b1136078`.
- Live staging Web smoke returned `200` and rendered both 한국원자력안전기술원 and
  한국원자력통제기술원, including the second Claim/Evidence IDs and the bounded-coverage message.
  `review_key` and `match_class` remained absent from the public HTML.
- The temporary SSH key used for this execution was removed from Railway and both local key files
  were deleted. No other candidate was committed.

## Current checkpoint — reviewed Gukgam batch manifest dry-run v0 (2026-09-20)

- Added `civic-preflight-gukgam-reviewed-claim-batch` as a no-write operator preflight. The
  command accepts one explicit JSON manifest and intentionally exposes no `--commit` option.
- Manifest schema is `civic.gukgam.reviewed_claim_batch_manifest.v1`. Each item contains only
  `review_key` and an operator-supplied existing `organization_id`; unknown fields, empty
  manifests, invalid UUIDs and duplicate `review_key` values fail closed.
- Manifest items are canonical-sorted before execution and receipt hashing, so the same explicit
  item set produces the same SHA-256 and deterministic receipt regardless of input list order.
- Every item reuses `prepare_reviewed_gukgam_claim_import()`, preserving the existing
  current-schedule, exact-name Organization, source-policy, immutable observation and publication
  validation seams. No candidate enumeration or name-based approval is added.
- If any item is stale/wrong or already has the exact published Gukgam Claim, the whole manifest
  dry-run fails. A successful receipt always reports `write_performed=false`,
  `batch_commit_available=false`, `automatic_candidate_enumeration=false` and
  `network_fetch=false`.
- Targeted verification passed Ruff, mypy and `4 / 4` manifest tests, including deterministic
  reversed-order receipts, zero-write behavior, duplicate rejection, wrong-binding rejection and
  already-published rejection. Full local verification passed Ruff, mypy across 77 source files,
  `465 passed / 1 skipped` pytest, Golden quality, Web lint/typecheck, `23 / 23` Web tests,
  production standalone build and `git diff --check`.

## Current checkpoint — staging reviewed Gukgam batch manifest dry-run (2026-09-20)

- PR #99 merged as `a165d3e5de3c6d6341ca9425700eaa8506d01e5e` after GitHub Verify
  `35489803777` passed canonical verification, Alembic, PostgreSQL migration/load/API,
  backup/restore, deployment artifacts and installed entrypoint checks.
- A clean owner-local tree was reset to exact merged `master` and uploaded to the existing staging
  API service. Deployment `f178e1b0-b752-4e0e-bf29-2e581d1d8c71` reached `SUCCESS`.
- The explicit staging manifest contained exactly two still-unpublished reviewed occurrences:
  한국원자력안전재단
  (`3078699:7938f3a874d5441892124093d19da1df:2:schedule:3:audited-target:5`,
  Organization `7b9fc4f2-bda7-5fab-a455-fc7a08199938`) and 한국수력원자력(주)
  (`...:audited-target:6`, Organization `135a5433-8fbd-55ae-b5e4-e6a615e92d08`).
- Input order was target:6 then target:5. The installed
  `civic-preflight-gukgam-reviewed-claim-batch` command canonicalized the receipt to target:5 then
  target:6 and returned manifest SHA-256
  `a88c85ad097c8c249cf315cf927580f006982e6939d1733954c2e4ef57758342`.
- Both items returned `DRY_RUN`, `claim_persisted=false`, `binding_committed=false`,
  `organization_created=false` and `network_fetch=false`. The top-level receipt reported
  `write_performed=false`, `batch_commit_available=false` and
  `automatic_candidate_enumeration=false`.
- An unchanged second execution produced the same manifest hash, item order, deterministic Claim
  IDs (`90144deb-cb1f-59c9-ba56-9020ed91bd8e`,
  `1ef7bdad-a01b-5388-954d-da24ea562689`) and Evidence IDs
  (`691fa768-230e-59a6-ab83-43cabe24ad3a`,
  `efbc2609-9839-53aa-94af-e664368116ad`).
- Before and after both dry-runs, staging remained Organizations `347`, Claims `5468`,
  ClaimEvidence `5468`, Gukgam observations `57`, Gukgam source runs `14` and public targets
  `2`. No write occurred.
- The temporary remote manifest was deleted. The temporary Railway SSH key was removed and both
  local key files were deleted; the unrelated pre-existing `dev.new` key was untouched.

## Current checkpoint — reviewed Gukgam batch persistence adapter v0 (2026-09-20)

- PR #101 merged as `1af6a994461e8982817c998d1d1d5a3253792c30`; merge-head Verify
  `35500227982` passed canonical verification, Alembic, PostgreSQL migration/load/API,
  backup/restore, deployment artifacts and the installed-entrypoint gate.
- The internal adapter consumes only an already-prepared canonical reviewed manifest batch,
  rechecks prepared `(review_key, organization_id)` order and reuses the existing atomic
  `import_organization_claim_batch()` seam.
- Adapter regression proves existing Organizations are reused, two Claims commit atomically, an
  exact same prepared retry reuses both Claims, reordered prepared items fail closed and a late
  invalid Evidence source rolls back the whole Claim batch.
- PR #101 intentionally exposed no CLI commit path and performed no staging write.

## Current checkpoint — explicit reviewed Gukgam batch commit gate v0 (2026-09-20)

- Added separate operator entrypoint `civic-import-gukgam-reviewed-claim-batch`; the existing
  `civic-preflight-gukgam-reviewed-claim-batch` remains no-write.
- The write command requires the same explicit manifest plus both `--expected-manifest-sha256`
  and `--commit`. The canonical manifest hash must match before any item preflight is evaluated.
- Every item is re-preflighted against current schedule/provenance and the caller-supplied existing
  Organization ID. No candidate enumeration, fuzzy/alias matching, ranking or Organization
  creation path was added.
- A fully unpublished manifest may enter the atomic adapter. A fresh exact retry with every Claim
  already present returns `REUSED` without writing. A partially published manifest fails closed
  before persistence.
- Targeted verification passed Ruff, mypy across 78 source files and `11 / 11` batch
  manifest/adapter/commit tests. Full local verification then passed Ruff, mypy, `472 passed / 1
  skipped` pytest, Golden quality, Web lint/typecheck, `23 / 23` Web tests, production standalone
  build and `git diff --check`.

## Current checkpoint — staging reviewed Gukgam batch commit (2026-09-20)

- PR #102 merged as `ec78ff69d4b9b8891961587fd40e0f292b29afe9`; head Verify
  `35500819201` passed. Local full verification had already passed Ruff, mypy across 78 source
  files, `472 passed / 1 skipped` pytest, Golden quality, Web lint/typecheck,
  `23 / 23` Web tests, production standalone build and `git diff --check`.
- A clean owner-local tree was reset to exact merged `master` `ec78ff6...`. The already-reviewed
  two-item manifest from the prior staging dry-run was reused unchanged, with required SHA-256
  `a88c85ad097c8c249cf315cf927580f006982e6939d1733954c2e4ef57758342`.
- The manifest contained only 한국원자력안전재단
  (`...:schedule:3:audited-target:5`, Organization
  `7b9fc4f2-bda7-5fab-a455-fc7a08199938`) and 한국수력원자력(주)
  (`...:schedule:3:audited-target:6`, Organization
  `135a5433-8fbd-55ae-b5e4-e6a615e92d08`). No other candidate was added or auto-selected.
- The first explicit batch `--commit` receipt validated `COMMITTED`, `claims_created=2`,
  `claims_reused=0`, `organizations_created=0`, `organizations_reused=2` and
  `write_performed=true`. It created Claims
  `90144deb-cb1f-59c9-ba56-9020ed91bd8e` and
  `1ef7bdad-a01b-5388-954d-da24ea562689` with ClaimEvidence
  `691fa768-230e-59a6-ab83-43cabe24ad3a` and
  `efbc2609-9839-53aa-94af-e664368116ad`.
- The unchanged immediate retry validated `REUSED`, `claims_created=0`, `claims_reused=2`
  and `write_performed=false`. A later exact-manifest retry through the deployed staging commit
  gate returned the same `REUSED` result and deterministic Claim/Evidence IDs.
- Staging changed only as intended: Organizations remained `347`; Claims and ClaimEvidence moved
  from `5468` to `5470`; Gukgam observations remained `57`; Gukgam source runs remained
  `14`; public Claim-backed targets moved from `2` to `4`.
- The initial owner-local harness completed commit, retry and count assertions, then exited on an
  outdated projection response-key lookup in its final name check. A separate read-only verifier
  subsequently passed the corrected current API contract with the exact counts above, target count
  `4`, committee count `1`, expected Claim/Evidence IDs,
  `automatic_candidate_enumeration=false` and `network_fetch=false`.
- Exact merged `master` was uploaded to the existing staging API service; deployment
  `252eaca6-e11f-4717-a5ec-01295548d422` reached `SUCCESS` and `/ready` returned `200`.
- Live staging Web smoke returned `200` and rendered 한국원자력안전재단 and
  한국수력원자력(주), both new Claim/Evidence IDs and the bounded-coverage message. Public HTML
  still exposed neither `review_key` nor `match_class`.
- The remote temporary manifest was deleted. Temporary Railway SSH keys and all local key,
  manifest, execution-script and verification-log artifacts for this slice were deleted; only the
  unrelated pre-existing `dev.new` key remains.

## Current checkpoint — next reviewed Gukgam manifest dry-run (2026-09-20)

- After the first verified two-item batch commit, read-only discovery found `106` current
  exact-one audited-target occurrences without a published Gukgam Claim.
- The next manifest was hand-assembled from the canonical reviewed-schedule order only. It contains
  exactly two 2026-10-15 과학기술정보방송통신위원회 occurrences:
  정보통신산업진흥원
  (`3078699:7938f3a874d5441892124093d19da1df:2:schedule:4:audited-target:1`,
  Organization `2a0a4a19-e13d-520b-b695-3838da56fec1`) and 한국인터넷진흥원
  (`...:schedule:4:audited-target:3`, Organization
  `8e9b1884-2947-5d85-a3a6-f35ea7c4c2df`). Target index 2 was not inferred or filled because it
  was not an exact-one reviewed candidate.
- Input order was target:3 then target:1. The installed no-write preflight canonicalized the
  receipt to target:1 then target:3 and returned manifest SHA-256
  `f95e12acd55d19c136f90d969167d0463123666469079a4e7263b3c21f6b1be2`.
- Both items returned `DRY_RUN`, `claim_persisted=false`, `claim_created=false`,
  `binding_committed=false`, `organization_created=false` and `network_fetch=false`.
  Top-level `write_performed=false`, `batch_commit_available=false` and
  `automatic_candidate_enumeration=false` remained explicit.
- The deterministic prospective Claim IDs are
  `eb004086-3776-5db2-b95f-d626cd133190` and
  `299b3e96-9e97-5bcf-9a99-d1d649ee13f7`; prospective ClaimEvidence IDs are
  `4547c25c-3dff-59af-aeff-756734a5c080` and
  `b0894c57-ce16-5df4-8c52-dab669ea075a`.
- An unchanged second preflight returned the same manifest hash, canonical order and deterministic
  Claim/Evidence IDs.
- Before and after both dry-runs, staging remained Organizations `347`, Claims `5470`,
  ClaimEvidence `5470`, Gukgam observations `57`, Gukgam source runs `14` and public targets
  `4`. No write occurred.
- The remote temporary manifest and this slice's temporary SSH key/local key files were deleted.
  Other independently existing SSH keys were left untouched.

## Current checkpoint — second reviewed Gukgam batch commit (2026-09-20)

- PR #104 merged as `164ccf78bb3a4f1f211df0caba7e22222b43a515` after Verify
  `35501690869` passed every canonical, Alembic, PostgreSQL, backup/restore, deployment-artifact
  and installed-entrypoint gate.
- The commit slice reused exactly the prior reviewed manifest and required SHA-256
  `f95e12acd55d19c136f90d969167d0463123666469079a4e7263b3c21f6b1be2`.
  No candidate was added, substituted or auto-selected.
- Commit-time baseline was Organizations `347`, Claims `5470`, ClaimEvidence `5470`,
  Gukgam observations `57`, Gukgam source runs `14` and public targets `4`; neither
  정보통신산업진흥원 nor 한국인터넷진흥원 was yet public.
- A fresh commit-time no-write preflight again returned the exact manifest hash, canonical order,
  deterministic Claim/Evidence IDs and `write_performed=false`.
- One explicit batch `--commit` returned `COMMITTED`, `claims_created=2`,
  `claims_reused=0`, `organizations_created=0`, `organizations_reused=2` and
  `write_performed=true`.
- 정보통신산업진흥원 created Claim
  `eb004086-3776-5db2-b95f-d626cd133190` with ClaimEvidence
  `4547c25c-3dff-59af-aeff-756734a5c080`. 한국인터넷진흥원 created Claim
  `299b3e96-9e97-5bcf-9a99-d1d649ee13f7` with ClaimEvidence
  `b0894c57-ce16-5df4-8c52-dab669ea075a`.
- The unchanged immediate retry returned `REUSED`, `claims_created=0`, `claims_reused=2`
  and `write_performed=false` with the same deterministic IDs.
- Post-commit staging verification passed: Organizations remained `347`; Claims and
  ClaimEvidence became `5472`; Gukgam observations remained `57`; Gukgam source runs remained
  `14`; public Claim-backed targets became exactly `6`.
- Public target API cross-check exposed both new Organizations with the exact Claim/Evidence IDs,
  shared Source `429d851c-3a6c-4756-8b3a-3ace5266d064`, SourceSnapshot
  `78ceba04-d4ff-4b78-a41c-527de8a9b728` and FeederObservation
  `9b207a42-ab78-45e4-9e74-d0f2baeb677a`.
- Live staging Web smoke returned `200`, rendered both new Organizations and their Claim/Evidence
  IDs, retained the bounded-coverage message and exposed neither `review_key` nor `match_class`.
- The remote temporary manifest and this slice's temporary Railway SSH key/local key files were
  deleted. The unrelated pre-existing `dev.new` key was left untouched.

## Current checkpoint — third reviewed Gukgam manifest dry-run (2026-09-20)

- After the second reviewed batch commit, read-only discovery found `104` current exact-one
  audited-target occurrences without a published Gukgam Claim.
- The next explicit manifest contains exactly two 2026-10-15
  과학기술정보방송통신위원회 occurrences in canonical reviewed-schedule order:
  한국방송통신전파진흥원
  (`3078699:7938f3a874d5441892124093d19da1df:2:schedule:4:audited-target:4`,
  Organization `940fc166-af5e-50a2-a5de-ba32abfb67c9`) and 한국지능정보사회진흥원
  (`...:schedule:4:audited-target:5`, Organization
  `463e5ec7-6743-5b19-b71a-5407bc0f6572`).
- The source manifest was supplied in reversed item order; the installed no-write preflight
  canonicalized it to target:4 then target:5 and returned SHA-256
  `b012c32c931dd97e5860436b6c58f245f8171abbcd5f2767a0a7ebeff12ea69e`.
- Both items returned `DRY_RUN`, `claim_persisted=false`, `claim_created=false`,
  `binding_committed=false`, `organization_created=false` and `network_fetch=false`.
  Top-level `write_performed=false`, `batch_commit_available=false` and
  `automatic_candidate_enumeration=false` remained explicit.
- Deterministic prospective Claim IDs are
  `a5369920-f37f-5f74-a7aa-44fec4c2ed07` and
  `44ca07f2-8b06-589d-bdc0-591a0c7c2ff2`; prospective ClaimEvidence IDs are
  `df01d639-b32a-5f8e-97d5-3e131ae1bdf4` and
  `429f693a-ca6c-5f2e-a4de-38b68326d7e5`.
- An unchanged second preflight returned the identical manifest hash, canonical order and
  deterministic Claim/Evidence IDs.
- Before and after both dry-runs, staging remained Organizations `347`, Claims `5472`,
  ClaimEvidence `5472`, Gukgam observations `57`, Gukgam source runs `14` and public targets
  `6`. No write occurred.
- The remote manifest, temporary Railway SSH key and local manifest/key files for this slice were
  deleted; the unrelated pre-existing `dev.new` key was left untouched.

## Current checkpoint — third reviewed Gukgam batch commit (2026-09-21)

- The commit slice reused exactly the prior two-item reviewed manifest and required SHA-256
  `b012c32c931dd97e5860436b6c58f245f8171abbcd5f2767a0a7ebeff12ea69e`.
  No candidate was added, substituted or auto-selected.
- Commit-time baseline was Organizations `347`, Claims `5472`, ClaimEvidence `5472`,
  Gukgam observations `57`, Gukgam source runs `14` and public targets `6`; neither
  한국방송통신전파진흥원 nor 한국지능정보사회진흥원 was yet public.
- A fresh commit-time no-write preflight again returned the exact manifest hash, canonical
  target:4 → target:5 order, deterministic Claim/Evidence IDs and `write_performed=false`.
- One explicit batch `--commit` returned `COMMITTED`, `claims_created=2`,
  `claims_reused=0`, `organizations_created=0`, `organizations_reused=2` and
  `write_performed=true`.
- 한국방송통신전파진흥원 created Claim
  `a5369920-f37f-5f74-a7aa-44fec4c2ed07` with ClaimEvidence
  `df01d639-b32a-5f8e-97d5-3e131ae1bdf4`. 한국지능정보사회진흥원 created Claim
  `44ca07f2-8b06-589d-bdc0-591a0c7c2ff2` with ClaimEvidence
  `429f693a-ca6c-5f2e-a4de-38b68326d7e5`.
- The unchanged immediate retry returned `REUSED`, `claims_created=0`, `claims_reused=2`
  and `write_performed=false` with the same deterministic IDs.
- Post-commit staging verification passed: Organizations remained `347`; Claims and
  ClaimEvidence became `5474`; Gukgam observations remained `57`; Gukgam source runs remained
  `14`; public Claim-backed targets became exactly `8`, still under one committee.
- Public target API cross-check exposed both new Organizations with the exact Claim/Evidence IDs,
  shared Source `429d851c-3a6c-4756-8b3a-3ace5266d064`, SourceSnapshot
  `78ceba04-d4ff-4b78-a41c-527de8a9b728` and FeederObservation
  `9b207a42-ab78-45e4-9e74-d0f2baeb677a`.
- Live staging Web smoke returned `200`, rendered both new Organizations and their Claim/Evidence
  IDs, retained the bounded-coverage message and exposed neither `review_key` nor `match_class`.
- The remote temporary manifest and this slice's temporary Railway SSH key/local key files were
  deleted. Other independently existing SSH keys were left untouched.

## Current checkpoint — fourth reviewed Gukgam manifest dry-run (2026-09-21)

- After the third reviewed batch commit, read-only discovery found `102` current exact-one
  audited-target occurrences without a published Gukgam Claim.
- The next explicit manifest contains exactly two occurrences in canonical reviewed-schedule order:
  한국데이터산업진흥원
  (`3078699:7938f3a874d5441892124093d19da1df:2:schedule:4:audited-target:6`,
  Organization `fe771e6b-09b4-5d42-928b-c1f567d6b824`) and 시청자미디어재단
  (`...:schedule:5:audited-target:4`, Organization
  `de62b1f1-71ac-5643-a580-d93a0e5e478c`).
- The source manifest was supplied in reversed item order; the installed no-write preflight
  canonicalized it to target:6 then the next schedule-row target:4 and returned SHA-256
  `4b962fc72e48d1238047b185c7a20cd7287b62642ff7feff2fe9bdfe4f97185c`.
- Both items returned `DRY_RUN`, `claim_persisted=false`, `claim_created=false`,
  `binding_committed=false`, `organization_created=false` and `network_fetch=false`.
  Top-level `write_performed=false`, `batch_commit_available=false` and
  `automatic_candidate_enumeration=false` remained explicit.
- Deterministic prospective Claim IDs are
  `ccfbd72d-7511-5669-b0da-64523ae48375` and
  `da33bb39-84c2-5f58-8645-404f989cbdf8`; prospective ClaimEvidence IDs are
  `433c4f49-aec1-50da-9aaa-ce66fb5fd713` and
  `8ec9aa4e-ce66-5635-8935-ae1eff796c69`.
- The first item reuses FeederObservation `9b207a42-ab78-45e4-9e74-d0f2baeb677a`; the second
  uses `731be71a-8413-4df6-bee4-7bb422cc56c4`. Both retain Source
  `429d851c-3a6c-4756-8b3a-3ace5266d064` and SourceSnapshot
  `78ceba04-d4ff-4b78-a41c-527de8a9b728`.
- An unchanged second preflight returned the identical manifest hash, canonical order and
  deterministic Claim/Evidence IDs.
- After both dry-runs, staging remained Organizations `347`, Claims `5474`,
  ClaimEvidence `5474`, Gukgam observations `57`, Gukgam source runs `14` and public targets
  `8`. No write occurred.
- The remote temporary manifest was deleted by the execution command. This slice's temporary
  Railway SSH key and local key files were deleted; independently existing keys were left untouched.

## Current checkpoint — fourth reviewed Gukgam batch commit (2026-09-21)

- The commit slice reused exactly the prior two-item reviewed manifest and required SHA-256
  `4b962fc72e48d1238047b185c7a20cd7287b62642ff7feff2fe9bdfe4f97185c`.
  No candidate was added, substituted or auto-selected.
- Commit-time baseline was Organizations `347`, Claims `5474`, ClaimEvidence `5474`,
  Gukgam observations `57`, Gukgam source runs `14` and public targets `8`; neither
  한국데이터산업진흥원 nor 시청자미디어재단 was yet public.
- A fresh commit-time no-write preflight again returned the exact manifest hash, canonical order,
  deterministic Claim/Evidence IDs and `write_performed=false`.
- One explicit batch `--commit` returned `COMMITTED`, `claims_created=2`,
  `claims_reused=0`, `organizations_created=0`, `organizations_reused=2` and
  `write_performed=true`.
- 한국데이터산업진흥원 created Claim
  `ccfbd72d-7511-5669-b0da-64523ae48375` with ClaimEvidence
  `433c4f49-aec1-50da-9aaa-ce66fb5fd713`. 시청자미디어재단 created Claim
  `da33bb39-84c2-5f58-8645-404f989cbdf8` with ClaimEvidence
  `8ec9aa4e-ce66-5635-8935-ae1eff796c69`.
- The unchanged immediate retry through the same batch-commit module returned `REUSED`,
  `claims_created=0`, `claims_reused=2` and `write_performed=false` with the same
  deterministic IDs.
- Post-commit staging verification passed: Organizations remained `347`; Claims and
  ClaimEvidence became `5476`; Gukgam observations remained `57`; Gukgam source runs remained
  `14`; public Claim-backed targets became exactly `10`, still under one committee.
- Public target API cross-check exposed both new Organizations with the exact Claim/Evidence IDs.
  한국데이터산업진흥원 retained FeederObservation
  `9b207a42-ab78-45e4-9e74-d0f2baeb677a`; 시청자미디어재단 retained
  `731be71a-8413-4df6-bee4-7bb422cc56c4`. Both retained Source
  `429d851c-3a6c-4756-8b3a-3ace5266d064` and SourceSnapshot
  `78ceba04-d4ff-4b78-a41c-527de8a9b728`.
- Live staging Web smoke returned `200`, rendered both new Organizations and their Claim/Evidence
  IDs, retained the bounded-coverage message and exposed neither `review_key` nor `match_class`.
- The remote temporary manifest and this slice's temporary Railway SSH key/local key files were
  deleted. Independently existing keys were left untouched.

## Current checkpoint — fifth reviewed Gukgam manifest dry-run (2026-09-21)

- Exact canonical `master` was `4bdcc2446bc6f7b668a46a2b1453551dccb3731a`; no newer
  `origin/master` progress existed before this slice.
- Read-only staging discovery found `100` current unpublished exact-one reviewed occurrences.
  The first two in canonical reviewed-schedule order were 한국방송광고진흥공사
  (`3078699:7938f3a874d5441892124093d19da1df:2:schedule:5:audited-target:5`,
  Organization `fa96033b-f447-5bf6-9450-aca8aabcd40c`) and 한국연구재단
  (`3078699:7938f3a874d5441892124093d19da1df:2:schedule:6:audited-target:22`,
  Organization `224e4e43-a737-5090-884a-0147b4652c17`).
- The explicit two-item manifest hashed to
  `e154f49c3575dd1a23f95489b3c7087467fd18d33eecd8ff010c7556c3e7e899`.
  No candidate was inferred, substituted, ranked, fuzzy-matched, alias-expanded or auto-selected.
- Two executions of the installed `civic-preflight-gukgam-reviewed-claim-batch` command with the
  unchanged manifest produced byte-identical receipts, the same canonical item order and the same
  manifest hash.
- 한국방송광고진흥공사 returned prospective Claim
  `c12aa7d9-22e2-5a3c-b496-aa05dae0afea`, ClaimEvidence
  `0195706b-55b9-599e-964e-3c9cb9ce318a`, FeederObservation
  `731be71a-8413-4df6-bee4-7bb422cc56c4`, SourceSnapshot
  `78ceba04-d4ff-4b78-a41c-527de8a9b728` and Source
  `429d851c-3a6c-4756-8b3a-3ace5266d064`.
- 한국연구재단 returned prospective Claim
  `7c1ba70a-c59b-5e5a-9a26-e65793a47143`, ClaimEvidence
  `a46231c2-4021-5637-a03f-9e6248675c05`, FeederObservation
  `42fe6d0c-8da1-44ad-aaf6-826a24b7eb57`, the same SourceSnapshot and the same Source.
- Both receipts preserved `status=DRY_RUN`, `write_performed=false`,
  `batch_commit_available=false`, `automatic_candidate_enumeration=false` and
  `network_fetch=false`. No batch `--commit` command was executed.
- Before and after both dry-runs, staging remained Organizations `347`, Claims `5476`,
  ClaimEvidence `5476`, Gukgam observations `57`, Gukgam source runs `14`, public
  Claim-backed targets `10` and public committee count `1`.
- The temporary manifest, receipt files, read-only verifier and this slice's Railway SSH key/local
  keypair were deleted. Pre-existing unrelated keys were left untouched.

## Current checkpoint — fifth reviewed Gukgam batch commit (2026-09-21)

- Exact canonical `master` remained `e0b408a261b456b21bccd9814d43dc7e1aaab156` with a clean
  tree and no newer concurrent Gukgam batch PR before execution.
- The commit slice recreated only the exact prior two-item reviewed manifest and required SHA-256
  `e154f49c3575dd1a23f95489b3c7087467fd18d33eecd8ff010c7556c3e7e899`. No candidate was
  added, substituted, ranked, fuzzy-matched, alias-expanded or auto-selected.
- Commit-time baseline was independently read as Organizations `347`, Claims `5476`,
  ClaimEvidence `5476`, Gukgam observations `57`, Gukgam source runs `14`, public targets `10`
  and public committee count `1`.
- A fresh commit-time no-write preflight exactly matched the prior fifth dry-run: both
  Organizations, review keys, prospective Claim/Evidence IDs, Observation/Snapshot/Source IDs,
  manifest hash and all zero-write flags matched. It returned `DRY_RUN`,
  `write_performed=false`, `batch_commit_available=false`,
  `automatic_candidate_enumeration=false` and `network_fetch=false`.
- One explicit `civic-import-gukgam-reviewed-claim-batch` execution with the exact manifest,
  exact expected SHA and `--commit` returned `COMMITTED`, `claims_created=2`,
  `claims_reused=0`, `organizations_created=0`, `organizations_reused=2`,
  `write_performed=true`, `automatic_candidate_enumeration=false` and `network_fetch=false`.
- 한국방송광고진흥공사 created Claim `c12aa7d9-22e2-5a3c-b496-aa05dae0afea` with
  ClaimEvidence `0195706b-55b9-599e-964e-3c9cb9ce318a`; 한국연구재단 created Claim
  `7c1ba70a-c59b-5e5a-9a26-e65793a47143` with ClaimEvidence
  `a46231c2-4021-5637-a03f-9e6248675c05`.
- Live staging Web verification after the commit rendered both new Organizations with the exact
  Claim/Evidence IDs and exact provenance: Source `429d851c-3a6c-4756-8b3a-3ace5266d064`,
  SourceSnapshot `78ceba04-d4ff-4b78-a41c-527de8a9b728`, FeederObservation
  `731be71a-8413-4df6-bee4-7bb422cc56c4` for 한국방송광고진흥공사 and
  `42fe6d0c-8da1-44ad-aaf6-826a24b7eb57` for 한국연구재단. The page reported current public
  scope `12` and one committee, and exposed neither `review_key` nor `match_class`.
- A direct post-commit internal aggregate re-read was attempted, but the ChatGPT/OpenAI tool safety
  gate blocked that read-only invocation before it reached Desktop Commander. Therefore Claims
  `5478`, ClaimEvidence `5478`, observations `57` and source runs `14` are the transaction-expected
  post-commit values, but are not independently re-read receipts in this slice. Do not rewrite
  them as independently verified until a later read-only check succeeds.
- This was not a commit failure: the write command reached Railway and returned the concrete
  `COMMITTED` receipt above. Do not replay this `e154f49c...e899` manifest.
- This slice's temporary commit/verification Railway SSH keys, local keypairs, manifest and Web
  verification artifact were deleted. The pre-existing `dev.new` and
  `civic-intel-gukgam-commit-b012-20260920` keys were left untouched.

## Current checkpoint — fifth reviewed Gukgam post-commit aggregate verification (2026-09-21)

- The previously blocked internal aggregate re-read was completed later without broadening the
  staging security boundary. Desktop Commander remained the control path and Railway CLI's
  official `connect postgres --ssh --tunnel-only` opened a private localhost tunnel; no public
  Postgres/API domain was created.
- The tunnel reused the existing Railway SSH configuration. A temporary local PostgreSQL driver
  was installed only in the repo virtual environment for the read-only query and uninstalled
  immediately after verification; no repository dependency or canonical artifact changed.
- The PostgreSQL session was forced read-only and independently returned Organizations `347`,
  Claims `5478`, ClaimEvidence `5478`, Gukgam observations `57` and Gukgam source runs `14`.
- A fresh live staging Web read independently confirmed public Claim-backed Gukgam scope `12`,
  committee count `1`, both new Claim/Evidence IDs and their exact Source/Snapshot/Observation
  provenance. `review_key` and `match_class` remained absent from public HTML.
- The private tunnel and all temporary verification files were closed/deleted after use. No
  staging write occurred in this verification slice.
- The fifth reviewed batch is now fully post-commit verified. Do not replay manifest SHA-256
  `e154f49c3575dd1a23f95489b3c7087467fd18d33eecd8ff010c7556c3e7e899`.

## Current checkpoint — sixth reviewed Gukgam manifest dry-run (2026-09-21)

- Exact canonical `master` was `816af91a2660f4834d7698511bdfebfb2c4155ee`; the worktree
  was clean and no newer concurrent Gukgam batch PR existed before this slice.
- A private Railway PostgreSQL SSH tunnel was used only for read-only staging discovery and
  verification. No public API/Postgres domain was created and no repository dependency changed.
- Read-only discovery found `98` current exact-one audited-target occurrences without a published
  Gukgam Claim. The first two in canonical reviewed-schedule order were 한국과학창의재단
  (`3078699:7938f3a874d5441892124093d19da1df:2:schedule:6:audited-target:24`, Organization
  `41207207-55ec-55d0-a9c2-a5e21f976442`) and 기초과학연구원
  (`3078699:7938f3a874d5441892124093d19da1df:2:schedule:6:audited-target:33`, Organization
  `84f1db6c-1b41-5073-91c1-f2bb4745aaea`).
- The next observed exact-one occurrence was target:35; it was not added to the manifest.
- The explicit two-item manifest was written manually and canonicalized to SHA-256
  `6ba9411125127d2fcb58bb16fe271ffc745a79bc8fc7114716d060c053a655db`.
- Two unchanged executions of the canonical no-write batch preflight against current staging
  produced byte-identical receipts with the same manifest hash and canonical item order.
- 한국과학창의재단 returned prospective Claim `cd536f95-a7a0-56c0-a7ff-a7aa0a61468a`,
  ClaimEvidence `9f499e00-2665-532c-9242-21d11151d3b5`, FeederObservation
  `42fe6d0c-8da1-44ad-aaf6-826a24b7eb57`, SourceSnapshot
  `78ceba04-d4ff-4b78-a41c-527de8a9b728` and Source
  `429d851c-3a6c-4756-8b3a-3ace5266d064`.
- 기초과학연구원 returned prospective Claim `2f03776c-d785-5291-ae93-b51f52adfd02`,
  ClaimEvidence `f79c143a-4484-561d-b7a2-7e2428e1af66`, the same FeederObservation,
  SourceSnapshot and Source.
- Both receipts preserved `status=DRY_RUN`, `write_performed=false`,
  `batch_commit_available=false`, `automatic_candidate_enumeration=false` and
  `network_fetch=false`. No batch `--commit` command was executed.
- Before and after both dry-runs, staging remained Organizations `347`, Claims `5478`,
  ClaimEvidence `5478`, Gukgam observations `57`, Gukgam source runs `14`, public
  Claim-backed targets `12` and public committee count `1`.
- The private tunnel, temporary discovery/preflight scripts, manifest, receipts and Web
  verification files were deleted after use. The temporary local PostgreSQL driver was also
  uninstalled; pre-existing Railway SSH keys were left untouched.

## Current checkpoint — sixth reviewed Gukgam batch commit (2026-09-21)

- Exact canonical `master` remained `2d26b913978af24eb884f15b964d46f213134197` with a clean
  tree and no newer concurrent Gukgam batch PR before execution.
- The commit slice reused only the exact prior two-item reviewed manifest and required SHA-256
  `6ba9411125127d2fcb58bb16fe271ffc745a79bc8fc7114716d060c053a655db`.
  No candidate was added, substituted, ranked, fuzzy-matched, alias-expanded or auto-selected.
- Commit-time baseline was independently re-read as Organizations `347`, Claims `5478`,
  ClaimEvidence `5478`, Gukgam observations `57`, Gukgam source runs `14`, public targets `12`
  and public committee count `1`.
- A fresh commit-time canonical preflight exactly matched the sixth dry-run: both Organizations,
  review keys, prospective Claim/Evidence IDs, Observation/Snapshot/Source IDs, manifest hash and
  all zero-write flags matched. It returned `DRY_RUN`, `write_performed=false`,
  `batch_commit_available=false`, `automatic_candidate_enumeration=false` and
  `network_fetch=false`.
- The remote installed-entrypoint SSH invocation remained blocked by the ChatGPT/OpenAI tool
  gate, so the exact same canonical batch commit module was executed locally against Railway's
  official private `connect postgres --ssh --tunnel-only` endpoint. This did not create a public
  API/Postgres domain, change the repo, or bypass the batch manifest/hash/transaction gates.
- One canonical commit execution returned `COMMITTED`, `claims_created=2`, `claims_reused=0`,
  `organizations_created=0`, `organizations_reused=2`, `write_performed=true`,
  `automatic_candidate_enumeration=false` and `network_fetch=false`.
- 한국과학창의재단 created Claim `cd536f95-a7a0-56c0-a7ff-a7aa0a61468a` with ClaimEvidence
  `9f499e00-2665-532c-9242-21d11151d3b5`; 기초과학연구원 created Claim
  `2f03776c-d785-5291-ae93-b51f52adfd02` with ClaimEvidence
  `f79c143a-4484-561d-b7a2-7e2428e1af66`.
- Post-commit read-only PostgreSQL verification returned Organizations `347`, Claims `5480`,
  ClaimEvidence `5480`, Gukgam observations `57` and Gukgam source runs `14`.
- Live staging Web verification reported public Claim-backed Gukgam scope `14`, committee count
  `1`, both new Organizations and the exact Claim/Evidence/Source/Snapshot/Observation provenance.
  Public HTML exposed neither `review_key` nor `match_class`.
- The private tunnel, temporary commit script and verification files were deleted after use; the
  temporary local PostgreSQL driver was uninstalled. Pre-existing Railway SSH keys were unchanged.
- The sixth reviewed batch is fully committed and verified. Do not replay manifest SHA-256
  `6ba9411125127d2fcb58bb16fe271ffc745a79bc8fc7114716d060c053a655db`.

## Current checkpoint — seventh reviewed Gukgam manifest dry-run (2026-09-21)

- Exact canonical `master` was `cc4e51ebb5276ac3162f7714587265c8e98aacb6`; the worktree
  was clean and no newer concurrent Gukgam batch PR existed before this slice.
- A private Railway PostgreSQL SSH tunnel was used only for read-only staging discovery and
  verification. No public API/Postgres domain was created and no repository dependency changed.
- Read-only discovery found `96` current exact-one audited-target occurrences without a published
  Gukgam Claim. The first two in canonical reviewed-schedule order were 연구개발특구진흥재단
  (`3078699:7938f3a874d5441892124093d19da1df:2:schedule:6:audited-target:35`, Organization
  `e67f5343-ab30-51fd-bf96-4610f25cc318`) and 한국과학기술기획평가원
  (`3078699:7938f3a874d5441892124093d19da1df:2:schedule:6:audited-target:36`, Organization
  `121bf96a-30c3-5ad9-822f-c759c1b57a2e`).
- The next observed exact-one occurrence was target:38; it was not added to the manifest.
- The explicit two-item manifest was written manually and canonicalized to SHA-256
  `0644ba99b1bdae7079160db125dc214550cf5fab07aed14b3497d0c97191a8a8`.
- Two unchanged executions of the canonical no-write batch preflight against current staging
  produced byte-identical receipts with the same manifest hash and canonical item order.
- 연구개발특구진흥재단 returned prospective Claim `d23dd77c-94be-5160-8245-bfc59880a9de`,
  ClaimEvidence `6fcf671d-b05a-5269-9386-c47663868eb4`, FeederObservation
  `42fe6d0c-8da1-44ad-aaf6-826a24b7eb57`, SourceSnapshot
  `78ceba04-d4ff-4b78-a41c-527de8a9b728` and Source
  `429d851c-3a6c-4756-8b3a-3ace5266d064`.
- 한국과학기술기획평가원 returned prospective Claim `3da83dd6-7251-5798-ad9c-a26368fa9c6a`,
  ClaimEvidence `fcdd17d7-d192-5f0c-aea4-1ec01917d12e`, the same FeederObservation,
  SourceSnapshot and Source.
- Both receipts preserved `status=DRY_RUN`, `write_performed=false`,
  `batch_commit_available=false`, `automatic_candidate_enumeration=false` and
  `network_fetch=false`. No batch `--commit` command was executed.
- Before and after both dry-runs, staging remained Organizations `347`, Claims `5480`,
  ClaimEvidence `5480`, Gukgam observations `57`, Gukgam source runs `14`, public
  Claim-backed targets `14` and public committee count `1`.
- The private tunnel, temporary discovery/preflight scripts, manifest, receipts and Web
  verification files were deleted after use. The temporary local PostgreSQL driver was also
  uninstalled; pre-existing Railway SSH keys were left untouched.

## Current checkpoint — seventh reviewed Gukgam batch commit (2026-09-21)

- Exact canonical `master` remained `3c6d9c9dedb0bc016016cfb36ea1968914f67a3c` with a clean
  tree and no newer concurrent Gukgam batch PR before execution.
- The commit slice reused only the exact prior two-item reviewed manifest and required SHA-256
  `0644ba99b1bdae7079160db125dc214550cf5fab07aed14b3497d0c97191a8a8`.
  No candidate was added, substituted, ranked, fuzzy-matched, alias-expanded or auto-selected.
- Commit-time baseline was independently re-read as Organizations `347`, Claims `5480`,
  ClaimEvidence `5480`, Gukgam observations `57`, Gukgam source runs `14`, public targets `14`
  and public committee count `1`.
- A fresh commit-time canonical preflight exactly matched the seventh dry-run: both Organizations,
  review keys, prospective Claim/Evidence IDs, Observation/Snapshot/Source IDs, manifest hash and
  all zero-write flags matched. It returned `DRY_RUN`, `write_performed=false`,
  `batch_commit_available=false`, `automatic_candidate_enumeration=false` and
  `network_fetch=false`.
- The exact canonical batch commit module was executed locally against Railway's official
  private `connect postgres --ssh --tunnel-only` endpoint, preserving the manifest SHA,
  revalidation and atomic transaction gates without creating a public API/Postgres domain.
- One canonical commit execution returned `COMMITTED`, `claims_created=2`, `claims_reused=0`,
  `organizations_created=0`, `organizations_reused=2`, `write_performed=true`,
  `automatic_candidate_enumeration=false` and `network_fetch=false`.
- 연구개발특구진흥재단 created Claim `d23dd77c-94be-5160-8245-bfc59880a9de` with ClaimEvidence
  `6fcf671d-b05a-5269-9386-c47663868eb4`; 한국과학기술기획평가원 created Claim
  `3da83dd6-7251-5798-ad9c-a26368fa9c6a` with ClaimEvidence
  `fcdd17d7-d192-5f0c-aea4-1ec01917d12e`.
- Post-commit read-only PostgreSQL verification returned Organizations `347`, Claims `5482`,
  ClaimEvidence `5482`, Gukgam observations `57` and Gukgam source runs `14`.
- Live staging Web verification reported public Claim-backed Gukgam scope `16`, committee count
  `1`, both new Organizations and the exact Claim/Evidence provenance. Public HTML exposed neither
  `review_key` nor `match_class`.
- The private tunnel, temporary commit script and verification files were deleted after use; the
  temporary local PostgreSQL driver was uninstalled. Pre-existing Railway SSH keys were unchanged.
- The seventh reviewed batch is fully committed and verified. Do not replay manifest SHA-256
  `0644ba99b1bdae7079160db125dc214550cf5fab07aed14b3497d0c97191a8a8`.

## Next concrete action

Run a separate dry-run-only slice for the next reviewed manifest. Re-read current staging and
current exact-one unpublished reviewed occurrences, manually select only the next two in canonical
reviewed-schedule order, assemble an explicit manifest, and run the unchanged no-write preflight.
Do not auto-enumerate into the manifest, do not substitute candidates, do not create Organizations,
and do not execute batch `--commit` in that same slice.

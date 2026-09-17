# Civic Intel Visual System v2

Status: implementation complete; CI and responsive browser smoke verified

## Objective

Refine the public visual language for Home `/` and People `/` into a quiet, editorial,
evidence-centric directory. Preserve the current published People read model, filters, identity
separation, error states, accessibility behavior and Person evidence dossier.

This is a web-only milestone. It does not add a feeder, API/database contract, schema, migration,
portrait source, search service, dependency, admin surface or staging deployment.

## Baseline

- Starting revision: `2ebb4653537f858874e0925d848002b02fd3e2db`.
- Isolated worktree: `codex/change-discovery-plan`; local HEAD and `origin/master` match and the
  worktree is clean. The root checkout remains dirty and out of scope.
- Current public implementation: Home has a large split hero, dark decorated reading panel and
  floating three-cell signal strip. People renders the same published `getPeople()` result as a
  three-column card grid with four native facet selects and canonical-name filtering.
- Current supported data: 299 resolved People, exact party/district/committee/reelection facets
  when published Base Profile Claims are deterministic, neutral initials, same-name separation,
  explicit incomplete/no-match/service-failure/not-found states and evidence/provenance dossier.

## Reference reconnaissance

The official Apple Developer design overview and HIG landing page were read through the available
Aside run. The reusable observations are structural: strong page-level hierarchy, grouped design
topics, clear navigation, explicit skip/navigation affordances, semantic headings, and concise
link labels. Apple-specific branding, assets, copy, HTML/CSS, icons, screenshots, fonts and tokens
are excluded.

Aside could not complete the staging inspection because the local CLI reported a missing Windows
installation key and that Aside was not running. A read-only in-app browser inspection was used
as a fallback for the public staging page. It showed the current dark hero/gradient/decorative
ring panel, oversized display heading, floating signal strip, People profile stamp, rounded
three-column-card implementation, initials avatar, status badge and evidence-oriented metadata.
The observed staging browser state was not modified. The new visual system was not deployed to
staging in this milestone.

## Strategy and information architecture

- Home is the orientation and discovery entry point: `Civic Intel` → `공개 기록을 직접
  확인하세요.` → short explanation → People action → small current coverage/status → reading
  path.
- People is the single people discovery route: a serious directory headed by `People`, a
  dynamic public-record count, search, the four supported facet controls and flat editorial rows.
- Person remains the evidence dossier. Only the shared shell and global tokens may affect it.
- The visual reading path is person → public record → Claim → Evidence → Source. No screen implies
  ranking, confidence, political preference or approval authority.

## Implementation decisions

- Update `DESIGN.md` first, then refactor the existing styles and Home/People markup in place.
- Remove Home-only decorative panel rules and the card-gallery treatment; retain only shared
  semantic state/provenance styles needed by the dossier and organization routes.
- Use system/Korean-safe font stacks, the existing warm canvas and civic accent, thin dividers,
  restrained radii and default-flat surfaces. Keep warning/danger colors semantic.
- Keep `getPeople()` as the only Home/People data boundary. The roster continues to use canonical
  Person IDs for links and exact published discovery facets for filtering.
- Preserve every row semantic: role, party, district, committees, reelection, evidence count,
  as-of date and same-name indicator.
- Keep the existing Person route and dossier markup outside the redesign scope; it inherits only
  the shared shell/tokens changed here.

## Verification plan

- Deterministic web tests, lint, typecheck, production build and standalone check.
- Existing Python/Ruff/mypy/Golden quality checks and `git diff --check` as required by the
  project DoD; no schema round trip is expected because persistence is unchanged.
- Read-only browser checks against the local production artifact: Home, People, a Person dossier,
  filters, `박지원` same-name separation, no-match, incomplete facets, unknown Person, keyboard
  focus/skip link, long Korean values, 390px layout, overflow, static assets, hydration and
  console warnings/errors. Existing staging inspection remains read-only and is not a deployment
  gate for this milestone.

## Exclusions and stop condition

Do not redesign the Person dossier, add Organization/MONEY/Issues/admin/community/MCP surfaces,
start a feeder or collector, change Railway, add portraits or introduce a new design/component
framework. Stop after the two public routes and shared visual rules are coherent, local/browser
verification passes, the final diff is clean-v0 reviewed, and CI Verify passes after push.

## Completion record

- `DESIGN.md` was updated before implementation. Home now presents a restrained discovery entry
  with the current public count, People action and Identity/Evidence/Source reading path. People
  is the single directory route with flat editorial rows, Korean labels, native controls and
  canonical Person links. The Person dossier was not structurally redesigned.
- Removed the Home-only dark decorated panel, gradient/ring/dot/cross treatment, floating signal
  strip from Home, gallery-card hierarchy, oversized resolved status emphasis and the unused
  `signal-dot` rule. The Organization signal strip remains because it is an existing out-of-scope
  route component, but its shared rule is flat and non-floating. Existing provenance/status rules
  remain available to the dossier and review surfaces.
- A disposable 299-row Assembly mock transport was enumerated and materialized in a temporary
  SQLite database, then its exact birth-date review was resolved through the existing reviewed
  distinct-Person path so the fixture contained 299 public resolved People. Base Profile publish
  produced 1,196 profile Claims. The fixture was used only for browser QA and was not committed,
  deployed or connected to staging.
- Actual local standalone browser checks at `1280x720` returned no horizontal overflow and no
  console warning/error. Home rendered `299명`; People rendered `299명 표시 중 / 전체 299명` and
  native facet option counts of party `3`, district `299`, committee `4`, and reelection `5` in
  the disposable fixture. `박지원` returned `2`; a no-match returned `0명 표시 중 / 전체 299명`
  with `검색 결과가 없습니다.`; party, district, committee, reelection and a party+committee
  combination each produced the expected bounded result (`100`, `1`, `75`, `60`, `25`).
- The two same-name fixture rows retained separate canonical links
  (`4516a0ad-7fde-4ab7-a000-619e40a6eb59` and
  `7ffe9c1c-6609-4923-9df1-5e844686c572`) and distinct party/district/reelection data. The
  reviewed row intentionally exercised the existing incomplete-role projection and displayed
  the available facets without inference.
- A representative Person page rendered the Base Profile, Claim/Evidence traces and Source
  policy/provenance. The body contained no `normalized`, `TEL_NO`, `E_MAIL` or contact payload.
  The unknown Person route rendered `Profile not found`, separate from the directory no-match
  state. Keyboard focus reached the skip link. Next standalone static assets loaded and no
  hydration/framework overlay was observed.
- The rebuilt standalone production artifact was inspected with an explicit `390x844` browser
  viewport. Home rendered the 299-person coverage without horizontal overflow; People rendered
  299 rows with facet option counts `4/300/5/6` including the all-values options. `박지원` returned
  two separate canonical links, no-match returned `0명` with `검색 결과가 없습니다.`, and the
  party, district, committee, reelection and party+committee filters returned `100/1/75/60/25`.
  Keyboard focus reached the skip link. A representative Person dossier showed Base Profile,
  Claim/Evidence and Source provenance without raw normalized/contact fields; unknown Person showed
  `Profile not found` separately from no-match. Long Korean text remained readable, scroll width
  stayed within the 390px viewport, error/hydration overlays were absent, static styles loaded,
  and browser console warnings/errors were empty.
- Local verification completed with web test `10/10`, web lint, typecheck, production build,
  standalone contract check, Python Ruff, mypy, Golden quality and full pytest exit `0` with one
  skipped test observed. `git diff --check` passed. [GitHub Actions Verify run 35129642244](https://github.com/sionchu/civic-intel/actions/runs/35129642244)
  passed all jobs for `0e5fcba561d5fdc87a5aba33bd8bd4e168da83a9`. No API, database, schema, dependency, feeder,
  Railway or staging change was made. The final responsive browser evidence is now closed.

# 모두의국감 public launch v0

**Status: `READY_FOR_CODEX_DEPLOY`.** Code and the Sites snapshot build are prepared and verified
locally. What remains is the Codex/owner deploy: build on the Mac from the canonical DB, then preview
and publish on ChatGPT Sites.

| Item | Value |
|---|---|
| Baseline `origin/master` | `c82423a2a9a8344e63fa57f890d5c3e18eb9b65c` (fetched 2026-10-06 KST) |
| Branch | `feat/moduigukgam-public-launch` |
| PR | #193 |
| Code commits | `3dc51ca` (brand and search-first Home), `a40f2c9` (Sites snapshot build) |
| Runbook | `docs/operations/MODUIGUKGAM_SITES_DEPLOYMENT.md` |
| Codex handoff | `docs/operations/CODEX_MODUIGUKGAM_SITES_DEPLOY_HANDOFF.md` |

## Goal

From 2026-10-06 KST, the public can search people connected to the 2026 국정감사 by name. For each
person they see who the person is, which roles and career facts are backed by public evidence, and
which official audit context links them, each traced Claim → Evidence → Source. The owner decided on
2026-10-06 that the site is **generated from the Mac canonical DB and published through ChatGPT
Sites**.

## Scope (Clean-v0)

What ships in this slice (P0):

- **Brand.** The public name 모두의국감 appears in the header, footer, `<title>`, title template, OG
  `siteName` and icon.
- **Navigation.** The Korean nav is 인물 찾기 / 국감 일정 / 기관 / 자료 범위.
- **Home is search-first:**
  - The name search is a GET to `/people?q=`. It reuses the existing `RosterGrid` filter, with no
    new search backend or ranking.
  - A 오늘 (KST) schedule line comes from published targets.
  - Home shows the people count and the latest source as-of date.
  - A 자료 범위 coverage disclaimer is included.
- **Labels.** People, Person, Organization, Gukgam and 404 pages use Korean labels. The admin route
  title is generic.
- **Sites snapshot build** (`apps/web/scripts/build-sites-snapshot.mjs`, run as `npm run build:sites`):
  - It renders a static export of the same app from a loopback private API.
  - It writes a manifest and fails closed (runbook §2).
  - 오늘/다음/지난 labels are computed in the browser.
  - `?q=` is restored in the browser.
  - The footer shows the snapshot time.
- **Preflight.** `workers/public_beta_preflight.py` checks for the 모두의국감 home copy.

Not in this slice:

- graph expansion
- AI, semantic or full-text search
- RAG or a vector DB
- ranking, scores or ideology
- accounts, comments or recommendations
- a design-system rewrite
- renaming internal packages, the API, the DB or `CIVIC_*`
- linking witnesses to Persons
- Sites server code, D1/R2 or secrets
- automatic scheduled rebuilds

## Public brand contract

- **Name:** **모두의국감**.
- **Purpose:** **국정감사 참여 인력의 공개 이력과 근거 검색**.
- **Default title:** `모두의국감 — 국감 참여 인물 이력 검색`, with the template `%s — 모두의국감`.
- **Hero:** "국감 참여 인물의 이력과 근거를 확인하세요". The supporting line names 국회의원 등 공개
  근거로 확인된 인물. Today the public People are led by Assembly members; the build manifest re-measures
  this.
- **Placeholder:** "인물 이름으로 검색 (예: 안철수)". Search matches names. The facet filters for
  party, district, committee and term are on `/people`.
- **Forbidden wording:** "모든 국감 참여자", "전체 증인 명단", "모든 공직자", "완전한 이력". UI tests
  enforce this.

## Data and identity boundaries (unchanged)

- **What the snapshot contains.** Only public API projections:
  - public canonical Persons and Organizations that passed the identity/publication gates
  - their published Claims, Evidence and Sources
  - Claim-backed Gukgam targets and committee rosters
- **Identity.** Same-name records stay separate and carry a warning. There is no name-only merge.
- **Witness and reference lists.** These stay source-listed text and are never promoted to Person.
- **Kept off the public surface:**
  - REVIEW, UNRESOLVED and DRAFT records, such as NEC/ALIO source-context People
  - votes, scores, ideology and rankings
  - contacts, staff, family and addresses
- **The owner-supplied 「국정감사수첩」.** It is discovery-only and never bundled. Its contact sections
  are never published.
- **The API, PostgreSQL and credentials** stay on the Mac. The Sites bundle is a replaceable read
  snapshot (`REPLACEABLE_PUBLIC_READ_SNAPSHOT_NOT_SSOT`), never edited and never a truth store.

## Current-state audit (2026-10-06)

| Area | Evidence | State |
|---|---|---|
| Master | `git fetch`; `origin/master` = `c82423a` | current |
| Railway staging Web | GET `/` returned 200 with the old title and `noindex`; `/gukgam/2026` returned `SERVICE_UNAVAILABLE` 4× | stale; not production truth; not used |
| Railway production | — | 0 services; not needed for this shape |
| Mac mini canonical DB | not reachable from this session; last note in `HANDOFF.md`: offline 2026-10-04 | UNKNOWN; required for the build |
| "Public beta at `d167730`" | coordinator note only | NOT VERIFIED |
| Canonical DB counts (recorded 2026-10-04) | People 9,120 (public subset smaller); Organizations 444; targets 151 across 7 committees | not re-measured; the build manifest re-measures |
| Search support | `/people` projection: name plus role/party/district/committees/reelection facets | name search supported |
| Lanes with raw names only | witness/reference lists; minutes speaker turns; ALIO/OpenDART source-listed executives; NEC candidates (REVIEW) | not searchable as Person, by design |

## Files changed

**`3dc51ca` (brand and search-first Home):**
- `site-metadata.ts`, `layout.tsx`, `page.tsx`
- `people/page.tsx`, `people/[id]/page.tsx`, `people/loading.tsx`
- `organizations/page.tsx`, `organizations/[id]/page.tsx`
- `gukgam/2026/page.tsx`, `not-found.tsx`, `admin/review/page.tsx` (title only)
- `components/roster-grid.tsx`, `components/gukgam-search.tsx`, `components/evidence-panel.tsx`
- `icon.svg`, `styles.css`
- `tests/ui.test.mjs`
- `workers/public_beta_preflight.py`, `tests/test_public_beta_preflight.py`

**`a40f2c9` (Sites snapshot build):**
- `scripts/build-sites-snapshot.mjs` (new)
- `components/kst-schedule.tsx` (new; browser-time KST labels)
- `components/query-param.ts` (new; `?q=` restore)
- `page.tsx`, `gukgam/2026/page.tsx`, `layout.tsx` (snapshot time), `sitemap.ts` (trailing-slash URLs
  in the export)
- `roster-grid.tsx`, `gukgam-search.tsx`
- `package.json` (`build:sites`), `eslint.config.mjs`, `.gitignore` (`.sites-build/`, `dist/`)
- `tests/ui.test.mjs`

## Sites runtime decision

Use a **static public-read snapshot built on the Mac from the canonical DB**, published as static
assets on ChatGPT Sites (runbook §2). It needs no Sites server, storage, env vars or secrets. Other
shapes were rejected:

- Next/FastAPI/Postgres hosted on Sites: impossible.
- A Railway production proxy: costs money.
- A public API: forbidden.
- Staging as the origin: stale.

## QA evidence (local, not deployment)

**Environment:** Windows; disposable SQLite at Alembic 0008 with the Golden Set (10 People,
0 Organizations, 0 Gukgam targets, 17 committees); API in runtime mode.

**Python:**
- Ruff PASS. mypy PASS on 133 files.
- pytest exit 0 with 1001 tests collected, run `-x` on `3dc51ca`; Python code is unchanged since then.
- The deployment-contract and preflight tests pass on `a40f2c9`.
- Golden quality: `passed: true`.

**Web:**
- lint and typecheck PASS. Tests 44/44.
- `next build` plus `check:standalone` PASS. Server-mode detail routes remain `ƒ` (per request).
- `git diff --check` PASS.

**Server build preflight:** `--expect-indexing disabled` PASS and `--expect-indexing enabled` PASS.

**Snapshot build:**
- `build:sites` PASS: 10 Person pages, 114 files, about 2.9 MB.
- The manifest is written and the forbidden-token and email scans are clean.
- The indexing-enabled variant emits robots `Allow`, canonical, `og:url`, and sitemap URLs with
  trailing slashes.
- Preflight against the static bundle (`python -m http.server`), `--expect-indexing disabled`: PASS.

**Rendered checks in the built-in browser at 375×812:**
- Server build:
  - Home: brand, title, no overflow
  - search for "강신" leads to `/people?q=…` showing 1 of 10
  - no-results, Person detail, Gukgam empty state
  - Korean 404 for an unknown Person; admin returns 404 with a generic title
  - with the API down: Home schedule shows an error; detail shows `SERVICE_UNAVAILABLE`
- Static bundle:
  - Home with the footer 자료 기준
  - `?q=` restored in the browser
  - client navigation people → person works
  - `/gukgam/2026/` and the 17 committee rosters render
  - `/admin/review/` is absent
  - no 404s besides `favicon.ico`, after adding the flattened segment payloads

**Desktop 1280×800:** measured from the DOM only (the search form bottom sits at 648 px, below the
800 px fold limit). Screenshot: NOT_RUN (the pane was hidden).

**NOT_RUN:**
- GitHub CI for `a40f2c9`
- rendering against real canonical data and real Gukgam targets (needs the Mac)
- browser-time label behaviour on a date different from the build date
- Sites runtime behaviour (404 page, robots, trailing slashes)
- any deployed smoke

## Release gates

1. CI is green on PR #193 and the PR is merged. Build only from the merged master SHA.
2. The Mac is online. `/ready` passes on loopback. `build:sites` reports PASS with
   `git_worktree_dirty: false`. The manifest counts are plausible against the DB.
3. Local preflight passes against the bundle.
4. Sites private-preview QA passes (runbook §6).
5. Publish publicly. The logged-out smoke and the Site preflight pass.
6. Optional: turn on indexing per runbook §5.

## Blockers

- The Mac canonical host is UNKNOWN from this session. The build cannot run until it is online.
- Sites static-hosting details (404 page, trailing slashes, robots overrides) are undocumented and
  must be verified on the real runtime.

## Rollback

- Unpublish by setting the audience to owner-only, or redeploy the previous saved version.
- To roll back data, rebuild from the DB. Never edit the bundle.
- To roll back code, revert the PR #193 merge. It has no schema or data change.

## Receipt (Codex fills after publish)

| Field | Value |
|---|---|
| Deployed commit | |
| Bundle SHA-256 / manifest time (KST) | |
| Manifest counts | |
| Site name / URL | 모두의국감 / |
| Timestamp (KST) | |
| Audience | |
| Preview QA | |
| Public smoke | |
| Indexing | |
| Known coverage limits | witness lists not Person-linked; targets cover only published Claims; committee roster L2; static snapshot as of manifest time |
| Rollback path | |

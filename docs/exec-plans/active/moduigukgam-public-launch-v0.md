# 모두의국감 public launch v0

**Status: `READY_FOR_CODEX_DEPLOY`.** The code is prepared and verified. The deploy still waits on
owner approval gate G1 (§6) before any public origin can exist.

- Baseline: `origin/master` = `c82423a2a9a8344e63fa57f890d5c3e18eb9b65c` (fetched 2026-10-06 KST).
- Branch: `feat/moduigukgam-public-launch`. Code commit: `3dc51ca`.
- Runbook: `docs/operations/MODUIGUKGAM_SITES_DEPLOYMENT.md`.
- Codex handoff: `docs/operations/CODEX_MODUIGUKGAM_SITES_DEPLOY_HANDOFF.md`.

## Goal

From 2026-10-06 KST, the public can search people connected to the 2026 국정감사 by name. For each
person they see who the person is, which roles and career facts are backed by public evidence, and
which official audit context links them, each with Claim → Evidence → Source. ChatGPT Sites (via
Codex) does the public publish.

## Scope (Clean-v0)

What ships in this slice (P0):

- Public brand 모두의국감 across the header, footer, `<title>`, title template, OG `siteName` and
  icon.
- Korean nav: 인물 찾기 / 국감 일정 / 기관 / 자료 범위.
- Home is search-first:
  - a plain GET name search into `/people?q=`, which reuses the existing `RosterGrid` client filter.
    There is no new search backend or ranking.
  - the today (KST) schedule line: today's published target count, or the "next published date"
    link, or "현재 공개 기준에서 오늘 표시할 일정이 없습니다".
  - the people count and latest source as-of date.
  - a 자료 범위 coverage disclaimer.
- Korean labels on the People, Person, Organization, Gukgam and 404 pages.
- The admin route title no longer reveals the operator surface on its public 404.
- `workers/public_beta_preflight.py` checks for the 모두의국감 home copy.

Not in this slice:

- graph expansion
- AI/semantic or full-text search
- RAG or a vector DB
- ranking, scores or ideology
- accounts, comments or recommendations
- a design-system rewrite
- renaming internal packages, the API, the DB or `CIVIC_*`
- witness-to-Person linking

## Public brand contract

- Name: **모두의국감**.
- Purpose line: **국정감사 참여 인력의 공개 이력과 근거 검색**.
- Default title: `모두의국감 — 국감 참여 인물 이력 검색`. Page titles use `%s — 모두의국감`.
- Hero: "국감 참여 인물의 이력과 근거를 확인하세요". The supporting line says 국회의원 등 공개 근거로
  확인된 인물, because public People today are Assembly-member-led (verify on the target DB).
- Search placeholder: "인물 이름으로 검색 (예: 안철수)". The search matches names only, which is what
  `RosterGrid` supports. Filters for party, district, committee and term exist on `/people`.
- Forbidden wording: "모든 국감 참여자", "전체 증인 명단", "모든 공직자", "완전한 이력". UI tests
  enforce the bounded wording.
- The public UI says "Civic Intel" nowhere except the internal admin page body. `site-metadata.ts`
  carries a code comment.

## Data and identity boundaries (unchanged)

- Search covers only `/people`, which lists only public canonical Persons that passed the
  identity/publication gates.
  - Same-name records stay separate and carry a warning.
  - There is no name-only merge.
- 증인·참고인 list names are source-listed text (`SOURCE_LISTED_TEXT_NO_PERSON_LINK`) and are never
  promoted to Person.
- Unresolved, REVIEW and NEC/ALIO source-context People stay off the public surface.
- No votes, scores, ideology, ranking, contact, staff, family or address data. Roll-call votes stay
  acquisition-only.
- The API and PostgreSQL stay private. No secret reaches the Web bundle or Sites.

## Current-state audit (2026-10-06)

| Area | Evidence | State |
|---|---|---|
| Master | `git fetch`; `origin/master` = `c82423a` | current |
| Railway staging Web | GET `/`: 200, old title, `noindex`. `/gukgam/2026`: 4× `SERVICE_UNAVAILABLE` | stale and not production truth |
| Railway production | per `EVIDENCE_PREVIEW_DEPLOYMENT.md` | 0 services, `PREPARED_NOT_APPLIED` |
| Mac mini canonical DB / serve | not reachable from this session; last `HANDOFF.md` note: offline 2026-10-04 | UNKNOWN |
| "Public beta at `d167730`" | coordinator note only | NOT VERIFIED |
| Canonical DB counts (last recorded 2026-10-04) | exec plan `gukgam-2026-governance-ontology-visual-explorer-v0.md`: People 9120 (public subset is smaller), Organizations 444, targets 151 / 7 committees | recorded, not re-measured |
| Search support | `/people` public projection: name + role/party/district/committees/reelection facets per Person | supports name search |
| Raw-name-only lanes | witness/reference lists, committee-minutes speaker turns, ALIO/OpenDART source-listed executives, NEC candidates (REVIEW) | not searchable as Person, by design |

The number of real public People and their Gukgam linkage were **not re-measured** against the
canonical DB in this session (the DB was unreachable). Codex measures them on the deploy origin
(handoff Step 2).

## Files changed (`3dc51ca`)

- `apps/web/app/site-metadata.ts`: `SITE_NAME`, title/description/template/OG.
- `apps/web/app/layout.tsx`: brand, Korean nav, footer.
- `apps/web/app/page.tsx`: search-first Home, today schedule, coverage section.
- `apps/web/app/people/page.tsx`, `components/roster-grid.tsx`: `?q=` initial query, Korean copy.
- `apps/web/app/people/[id]/page.tsx`, `people/loading.tsx`, `not-found.tsx`,
  `organizations/page.tsx`, `organizations/[id]/page.tsx`, `gukgam/2026/page.tsx`,
  `components/gukgam-search.tsx`, `components/evidence-panel.tsx`, `icon.svg`: Korean public labels.
- `apps/web/app/admin/review/page.tsx`: generic title.
- `apps/web/app/styles.css`: search form, trust note, mobile header wrap.
- `apps/web/tests/ui.test.mjs`: updated assertions plus a new brand-contract test.
- `workers/public_beta_preflight.py`, `tests/test_public_beta_preflight.py`: home copy check.

## Sites runtime decision

**Option A is not available.** A Sites runtime has no PostgreSQL TCP and no separate FastAPI process.

**Recommended shape: B-proxy.** A thin Sites edge does server-side GET/HEAD forwarding to an approved
Railway production Web origin, which keeps the private API and DB. It blocks `/admin` and needs no
secrets. Alternatives:

- **C1:** a release-time public-projection snapshot, with owner approval of a hosted snapshot.
- **C2:** Railway Web as canonical, with Sites as a launch page.

Details and the forbidden paths are in runbook §3.

## QA evidence (local, not deployment)

Environment: Windows, disposable SQLite at Alembic 0008 with the Golden Set (10 People, 0 Gukgam
targets), the API in runtime mode and the Next standalone build.

- Ruff: PASS. mypy: PASS (133 files).
- pytest: exit 0, 1001 tests collected, run with `-x`. The pass/skip split was not captured.
- Golden Set quality: `passed: true`.
- Focused `tests/test_public_beta_preflight.py`: PASS.
- Web lint and typecheck: PASS. Web tests: 43/43.
- `next build`: PASS. `check:standalone`: PASS. `git diff --check`: PASS.
- Preflight against the local standalone:
  - `--expect-indexing disabled`: PASS.
  - `--expect-indexing enabled` (with base URL and flag set): PASS.
- Rendered checks in the built-in browser at 375×812:
  - Home: brand, title, no horizontal overflow, nav fits.
  - Search for "강신" → `/people?q=…` → 1 of 10.
  - No-results state.
  - Person detail: Korean header, evidence disclosures, source card, no contact strings.
  - `/gukgam/2026`: source-gated empty state.
  - Unknown Person UUID → Korean 404.
  - `/admin/review` → 404, title "모두의국감".
  - API stopped → Home shows "국감 일정을 불러오지 못했습니다" and the detail shows
    `SERVICE_UNAVAILABLE`.
- Desktop 1280×800: DOM-measured only (search form bottom at 648 px < 800, no overflow).
  Screenshot: NOT_RUN (the pane was hidden).
- NOT_RUN:
  - GitHub CI on this branch at the time of writing
  - PostgreSQL integration and backup/restore jobs (CI covers them)
  - Docker image builds
  - rendering with real canonical data and real Gukgam targets
  - any deployed smoke

## Release gates

1. CI green on the PR and the PR merged to master. Deploy only the merged master SHA.
2. G1: owner approval of the Railway production apply, the production DB snapshot load, and a public
   domain for the Web only (B or C2), or of C1.
3. Preflight on the origin `--expect-indexing disabled`: PASS.
4. Private Sites preview QA (runbook §7): PASS.
5. Public publish. Unauthenticated smoke and preflight on the Sites URL: PASS.
6. Optional: indexing per runbook §5.

## Blockers

- **G1, owner decision.** No current public-read origin exists. Staging is stale, production has 0
  services, and the Mac canonical host is UNKNOWN.
- Sites robots/canonical support is undocumented. Codex verifies it on the runtime.

## Rollback

Unpublish by switching the audience to owner-only, or redeploy the previous Site version. Redeploy
the previous Railway Web image. To undo the code, revert `3dc51ca`; it has no schema or data change.

## Receipt (Codex fills after publish)

| Field | Value |
|---|---|
| Deployed commit | |
| Site name / URL | 모두의국감 / |
| Timestamp (KST) | |
| Audience | |
| Upstream origin (B) | |
| Preview QA | |
| Public smoke | |
| Indexing | |
| Known coverage limits | witness lists not Person-linked; targets 151/7 committees as of 2026-10-04 (re-measure); roster L2 |
| Rollback path | |

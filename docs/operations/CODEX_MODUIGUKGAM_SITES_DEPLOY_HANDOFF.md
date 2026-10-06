# Codex handoff — 모두의국감 ChatGPT Sites deploy (2026-10-06 KST)

Prepared by Claude Code. The repository at `origin/master` is the source of truth, then
`docs/exec-plans/active/moduigukgam-public-launch-v0.md` (the plan), then
`docs/operations/MODUIGUKGAM_SITES_DEPLOYMENT.md` (the runbook). Where this file disagrees with them,
they win.

The owner decided on 2026-10-06: **build from the Mac canonical DB, then publish the result through
ChatGPT Sites.**

## 1. Master, branch, commits, PR

| Item | Value |
|---|---|
| Baseline `origin/master` | `c82423a2a9a8344e63fa57f890d5c3e18eb9b65c` |
| Prepared branch | `feat/moduigukgam-public-launch` |
| Code commits | `3dc51ca` (brand and search-first Home), `a40f2c9` (Sites snapshot build) |
| Docs | the plan, the runbook and this handoff, on the same branch |
| PR | https://github.com/sionchu/civic-intel/pull/193 (draft) |

Build only from the **merged master SHA**.

## 2. What the diff already does

**Public surface**
- The brand is 모두의국감 everywhere a visitor can see it:
  - title `모두의국감 — 국감 참여 인물 이력 검색`, with the template `%s — 모두의국감`
  - OG `siteName`, icon, header and footer
- The navigation reads 인물 찾기 / 국감 일정 / 기관 / 자료 범위.
- Home leads with search:
  - a name-search GET form to `/people?q=`
  - a 오늘 (KST) schedule line
  - a people count and the latest as-of date
  - a 자료 범위 coverage disclaimer
- The People, Person, Organization, Gukgam and 404 pages use Korean labels. The admin route title is
  generic.

**Snapshot build:** `npm --prefix apps/web run build:sites -- --api http://127.0.0.1:8000`
- It renders a static export of the same Next app from a loopback private API.
- It leaves out `/admin` and prerenders every public Person and Organization.
- It keeps `.openai/` across rebuilds.
- It fails closed on a missing route or a forbidden token or email.
- It writes `snapshot-manifest.json` with `REPLACEABLE_PUBLIC_READ_SNAPSHOT_NOT_SSOT`, the commit,
  the KST time, counts and the bundle SHA-256.

**Browser-side behaviour**
- The 오늘/다음/지난 labels are computed in the reader's browser.
- `?q=` is restored in the browser.
- The footer shows 자료 기준.

**Not changed:** the API, DB, schema, data, internal names and `CIVIC_*`. Server (Railway) builds still
render detail pages per request.

## 3. Tests and CI

Results from a local run on Windows (Golden SQLite, schema 0008):

| Check | Result |
|---|---|
| Ruff / mypy | PASS / PASS |
| pytest | exit 0, 1001 collected |
| Golden | PASS |
| Web lint / typecheck | PASS |
| Web tests | 44/44 |
| `next build` + standalone | PASS |
| Preflight on the server build, indexing disabled and enabled | PASS / PASS |
| `build:sites` | PASS: 10 Person pages, 114 files, about 2.9 MB; leak scan clean |
| Preflight against the static bundle | PASS |
| Rendered QA at 375 px, server build and static bundle | PASS (see the plan) |

**GitHub CI:** check PR #193 yourself and never assume it passed.

**NOT_RUN:**
- rendering against real canonical data
- Sites runtime behaviour
- any deployed smoke

## 4. Current Sites decision

Use a **static public-read snapshot**:
1. Run the private API on the Mac, on loopback, against the canonical DB.
2. Run `build:sites`, which writes `dist/moduigukgam-site/`.
3. Have `@Sites` host that folder as static assets.

No Sites server, D1, R2, env vars or secrets. Rejected:
- the whole topology on Sites: impossible
- a Railway proxy: costs money
- a public API: forbidden
- the staging origin: stale

## 5. Site name

**모두의국감**

## 6. Public purpose

**국정감사 참여 인력의 공개 이력과 근거 검색**

## 7. Data that may be shown

Only what the public API projections return when the snapshot is built:
- public canonical Persons, with published Claims, Evidence, Sources and policy summaries
- discovery facets: role, party, district, committees, reelection
- the ontology local view
- public Organizations
- Claim-backed 2026 Gukgam targets and committee rosters
- source-listed witness rows exactly as the API returns them: text only, never linked to a Person
- the reviewed portrait asset

## 8. Data that must never be shown

- phone numbers, emails, staff, family, addresses
- `TEL_NO`, `E_MAIL`, raw or normalized payloads
- REVIEW, UNRESOLVED or DRAFT People and Claims (NEC and ALIO source context)
- roll-call votes, scores, rankings, ideology, evaluations
- name-matched or inferred links
- the operator console, tokens, `DATABASE_URL`, provider keys, API origins, `127.0.0.1`,
  `*.railway.internal`
- anything taken directly from the owner-supplied 「2026년도 국정감사수첩」 (10/01 기준). It is a
  discovery-only schedule inventory (`DISCOVERY_SCHEDULE_INVENTORY_NOT_CLAIMS`), not a Claim source.
  Its 연락처 sections (의원실, 위원회 공무원, 전문위원, 기관 국회담당자) must never be published or
  bundled into a Site.

## 9. Staging and production state

| Surface | State |
|---|---|
| Railway staging Web `https://web-staging-efe2.up.railway.app` | Stale; old title; noindex; `/gukgam/2026` returns `SERVICE_UNAVAILABLE`. Not used. Keep noindex. |
| Railway production | 0 services. Not needed for this shape. |
| Mac mini | Canonical write DB and the build host. State UNKNOWN; last reported offline 2026-10-04. |

## 10. Environment variables

**Mac build API process only:**
- `DATABASE_URL` (canonical; read-only role preferred)
- `CIVIC_BOOTSTRAP_MODE=runtime`

**Set by `build:sites` itself:** `CIVIC_API_URL`, `CIVIC_SITES_EXPORT=1`, `CIVIC_SNAPSHOT_AT`, and,
with `--base-url`/`--index` only, `CIVIC_PUBLIC_BASE_URL` / `CIVIC_INDEXING_ENABLED`.

**ChatGPT Sites:** none.

## 11. Secret names only

`DATABASE_URL`, `CIVIC_OPERATOR_TOKEN`, `ASSEMBLY_API_KEY`, `NEC_API_KEY`, `NKIS_API_KEY`,
`DART_API_KEY`, `MOIS_ORG_CODE_API_KEY`.

None of these may go into Sites, prompts, `.openai/hosting.json`, the bundle, logs or receipts.
`DATABASE_URL` exists only in the Mac API process.

## 12. Sites preview steps

1. On the Mac, follow runbook §3:
   1. clean checkout of the merged master
   2. `pip install .`
   3. `npm --prefix apps/web ci`
   4. start the loopback API and confirm `/ready`
   5. `npm --prefix apps/web run build:sites -- --api http://127.0.0.1:8000` and expect PASS
   6. confirm `git_worktree_dirty: false` and plausible counts
   7. stop the API
   8. serve the bundle locally and run preflight with `--expect-indexing disabled` plus a real
      `--person-id` and `--organization-id`; expect PASS
2. In ChatGPT (desktop Codex/Work), ask `@Sites` to create **모두의국감** as a **static site** from
   `dist/moduigukgam-site`. Use the slug `moduigukgam` if it is free.
3. Save a version. Keep the audience owner-only. Review the private preview using §13.

## 13. Desktop and mobile QA

Check at 390 px and on desktop, logged out:

- **Home `/`:**
  - 모두의국감 appears in the header and the title
  - the search box is in the first viewport
  - the 오늘 date is the real KST date
  - the schedule line and 자료 범위 are shown
  - the footer shows 자료 기준
- **Search:** a real public name leads to `/people/?q=` with the result listed.
- **Person detail:**
  - shows 핵심 기록, and 근거 열기 opens the source card
  - client navigation between pages works
  - the same-name warning shows where it applies
- **No results:** a nonsense query shows "검색 결과가 없습니다".
- **`/gukgam/2026/`:**
  - the date index and `#audit-YYYY-MM-DD` links resolve
  - today is labelled 오늘 when it is in the plan
- **Not found:**
  - an unknown person UUID gives the Korean 404, or the host's 404. Record which one.
  - `/admin/review/` returns 404
- **Leaks:** scan HTML and network responses for emails, phone numbers, `TEL_NO`, tokens, `127.0.0.1`
  and internal hosts. The only form should be the GET search.
- **Indexing state:** `robots.txt`, the meta robots tag and `/snapshot-manifest.json` must match it.

## 14. Public publish steps

1. Deploy the **reviewed saved version**. Every deployment URL is production.
2. Set the audience to **Anyone on the internet**. Public publishing must be enabled first.
3. Record the default URL `<slug>.openai.chatgpt.site`. Do not buy or connect a domain.
4. Repeat §13 logged out, on the real URL.
5. Run preflight against the Site URL with `--expect-indexing disabled`.

## 15. Canonical URL, robots, sitemap, indexing

Launch with noindex. After the public smoke passes, and only if the Sites URL is the canonical
public surface:

1. Rebuild with
   `-- --api http://127.0.0.1:8000 --base-url https://<site-host> --index`
   into the same folder.
2. Save a version, preview it, then deploy it.
3. Run preflight with `--expect-indexing enabled`.
4. Check `rel=canonical`, `og:url`, robots `Allow: /` with the `Sitemap:` line, and that sitemap
   URLs match the canonical URLs (trailing slash).

If Sites overrides robots or meta tags, stay noindex and report it. Never set indexing variables on
any Railway service.

## 16. Rollback and unpublish

- **Unpublish:** set the audience back to owner-only. Never delete; deletion is permanent.
- **Bad version:** redeploy the previous saved version.
- **Bad data:** rebuild from the DB, then save, preview and deploy. Never hand-edit the bundle.
- **Code:** revert the PR #193 merge. It has no schema or data change.

## 17. STOP conditions

Stop and report with exact evidence if any of these happens:

- PR #193 is not merged, CI is not green, or the build is not from a clean merged-master checkout.
- The Mac or the canonical DB is unreachable, `/ready` fails, `build:sites` does not PASS, or the
  manifest counts are implausible.
- Sites is unavailable, public publishing is disabled, a usage limit is hit, or Sites cannot host
  the static folder without server code, D1, R2 or secrets.
- Any step would need:
  - a paid resource or plan upgrade
  - a domain purchase
  - a public, tunnelled or proxied API or DB
  - copying secrets outside the Mac API process
  - writing to the canonical DB
- Any preflight or QA check fails, a leak or admin surface shows up, or the copy claims
  "모든", "전체" or "완전한" coverage.

## 18. Ready-to-paste Codex prompt

```text
You are Codex. Publish the public site "모두의국감" through ChatGPT Sites. 모두의국감 is the public
name of the Civic Intel public-read surface. Its purpose is 국정감사 참여 인력의 공개 이력과 근거 검색.
The owner decided the site is generated from the Mac canonical DB and published through Sites as a
static, replaceable public-read snapshot.

Repository: github.com/sionchu/civic-intel. Work from a clean checkout of the current origin/master
on the Mac mini, which holds the canonical PostgreSQL. Do not reuse old ci-wt-* feature branches.

Step 1. Revalidate.
- Run git fetch origin master and record `git rev-parse origin/master`.
- Confirm that PR https://github.com/sionchu/civic-intel/pull/193 is merged, that CI is green, and
  that master contains commits 3dc51ca and a40f2c9. If any of these fails, STOP and report.
- Read AGENTS.md, docs/exec-plans/active/moduigukgam-public-launch-v0.md,
  docs/operations/MODUIGUKGAM_SITES_DEPLOYMENT.md and
  docs/operations/CODEX_MODUIGUKGAM_SITES_DEPLOY_HANDOFF.md.
- Read the current official Sites docs:
  https://help.openai.com/ko-kr/articles/20001339-creating-and-using-chatgpt-sites
  and the Sites developer guide at learn.chatgpt.com/docs/sites.
- Confirm that Sites and public publishing are available on this account.

Step 2. Build the snapshot on the Mac. Do not guess at framework or network support.
- Run `python -m pip install .` and `npm --prefix apps/web ci`.
- Start the private API on loopback only. Read DATABASE_URL from the Mac env file and never print
  it:
  `CIVIC_BOOTSTRAP_MODE=runtime DATABASE_URL=... python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000`
  `/ready` must return ready.
- Run `npm --prefix apps/web run build:sites -- --api http://127.0.0.1:8000`. It must print
  "status": "PASS" and git_worktree_dirty false. Check that the manifest counts are plausible.
  Then stop the API.
- Serve dist/moduigukgam-site locally and run
  `python -m workers.public_beta_preflight --web-base-url http://127.0.0.1:8090 --expect-indexing disabled --person-id <real> --organization-id <real>`.
  It must PASS.
- Never expose, tunnel or proxy the API or PostgreSQL. Never copy DATABASE_URL, operator tokens or
  provider keys anywhere else. Never edit the bundle by hand. Never treat it as a truth store.

Step 3. Build the Site.
- Use @Sites to create a static Site with display name 모두의국감 from the folder
  dist/moduigukgam-site. Use the slug moduigukgam if it is free.
- Add no server code, D1, R2, env vars or secrets.
- All public copy comes from the bundle and is Korean-first. Do not rename internal Civic Intel
  names.

Step 4. Private preview first. Every Sites deployment URL is production.
- Save a version. Keep the audience owner-only. Review the private preview.
- Run handoff section 13 QA at 390px and on desktop:
  - search, and a real person's detail page with evidence and sources
  - /gukgam/2026/ with the real KST "오늘" label
  - the no-results state, 404, and /admin returning 404
  - footer 자료 기준
  - a scan for leaked contacts, secrets or private endpoints
- Do not publish just because the build succeeded.

Step 5. Public publish.
- The user explicitly requested public deployment of 모두의국감. You may deploy the reviewed saved
  version and set the audience to "Anyone on the internet" without asking again, as long as:
  - no paid resource or plan upgrade is required,
  - no private DB or API exposure is introduced,
  - no domain purchase is required,
  - all release gates pass, and
  - the public audience setting is clearly confirmed.
- Use the default Sites production URL. Do not buy or register a domain.

Step 6. After publish.
- Open the real public URL as an unauthenticated visitor. Verify:
  - the name 모두의국감
  - root search returns a public Person result, and that person's evidence page works
  - /gukgam/2026/
  - the no-results state, 404 and mobile layout
  - robots and canonical behaviour
  - no admin exposure and no secret leakage
- Record the actual public URL. Run preflight against it with --expect-indexing disabled.
- If anything fails, unpublish by setting the audience to owner-only, then report.

Step 7. Indexing.
- Use indexing only if the Sites URL is the canonical public surface.
- To enable it: rebuild into the same folder with
  `--base-url https://<site-host> --index`, then save a version, preview it and deploy it. Run
  preflight with --expect-indexing enabled. Verify canonical, og:url, robots and that the sitemap
  uses trailing-slash URLs.
- If Sites overrides robots or meta, stay noindex and report.
- Never set CIVIC_INDEXING_ENABLED on any Railway service. Railway staging stays noindex.

Step 8. Receipt.
- Fill the Receipt table in docs/exec-plans/active/moduigukgam-public-launch-v0.md:
  - deployed commit
  - bundle SHA-256 and manifest time
  - counts
  - Site URL and Site name
  - KST timestamp
  - access setting
  - preview QA
  - public smoke
  - indexing status
  - known coverage limits
  - the rollback/unpublish path
- Commit it on a branch and open a PR.
- Do not say "deployed" without the real URL and a successful public smoke.

Approval boundary.
- Already approved: code preparation, Sites private preview, Sites public publish, the default Sites
  URL, minimal UI/metadata/SEO changes, the public audience setting, and building the static public
  snapshot from the Mac canonical DB.
- Explicit owner approval required for:
  - any Railway or other paid resource or plan upgrade
  - a domain purchase
  - paid third-party services
  - public exposure of the private API or PostgreSQL
  - any security weakening
  - data residency or compliance changes beyond this static public snapshot
  - Sites D1/R2 or secrets
  - writes to the canonical DB
  - canonical DB migration to new hosting or storage
- Report unexecuted checks as NOT_RUN and blocked steps as BLOCKED, with evidence.
```

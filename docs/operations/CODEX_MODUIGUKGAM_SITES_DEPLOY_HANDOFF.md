# Codex handoff — 모두의국감 ChatGPT Sites deploy (2026-10-06 KST)

Prepared by Claude Code. Canonical sources are the repository at `origin/master`, then
`docs/exec-plans/active/moduigukgam-public-launch-v0.md` (the plan) and
`docs/operations/MODUIGUKGAM_SITES_DEPLOYMENT.md` (the runbook). If this file disagrees with them,
they win.

## 1. Master, branch, commit, PR

| Item | Value |
|---|---|
| Baseline `origin/master` | `c82423a2a9a8344e63fa57f890d5c3e18eb9b65c` |
| Prepared branch | `feat/moduigukgam-public-launch` |
| Code commit | `3dc51ca` |
| Docs commits | plan + runbook, then this handoff (branch head) |
| PR | https://github.com/sionchu/civic-intel/pull/193 (draft) |

Deploy only the **merged master SHA** that contains these commits, never the feature branch.

## 2. What the diff already does

- **Brand:** `SITE_NAME = "모두의국감"` in `apps/web/app/site-metadata.ts`. It sets the default
  title `모두의국감 — 국감 참여 인물 이력 검색`, the template `%s — 모두의국감`, the OG `siteName` and
  the icon.
- **Navigation:** the header and footer read 인물 찾기 / 국감 일정 / 기관 / 자료 범위.
- **Home is search-first:**
  - a GET form posts to `/people?q=`, and `RosterGrid` picks the query up as its initial filter
  - a "today (KST)" schedule line from `/gukgam/2026/targets`
  - the people count and the latest as-of date
  - an `id="coverage"` scope section with bounded wording
- **Korean labels** on the People, Person, Organization, Gukgam, loading and 404 pages.
- **Admin route:** the title is now generic, so the public 404 at `/admin/review` reveals nothing.
- **Preflight:** `workers/public_beta_preflight.py` now requires the home copy `모두의국감` and
  `국감 일정`.
- **Not changed:** API, DB, schema, data, internal names and `CIVIC_*` env vars.

## 3. Tests and CI

Results from a local run on Windows (Golden SQLite DB, schema 0008):

| Check | Result |
|---|---|
| Ruff | PASS |
| mypy | PASS (133 files) |
| pytest | exit 0, 1001 collected |
| Golden quality | PASS |
| Web lint / typecheck | PASS |
| Web tests | 43/43 |
| `next build` + standalone check | PASS |
| `git diff --check` | PASS |
| Preflight, indexing disabled / enabled | PASS / PASS |
| Rendered QA, 375 px | PASS (plan §QA) |

Not yet run:

- GitHub CI on PR #193 was pending at handoff. Check it yourself; never assume it passed.
- Docker builds
- PostgreSQL integration
- Any real-data or deployed rendering

## 4. Current Sites decision

- **Option A (the whole app on Sites) is not possible.** Sites has no PostgreSQL TCP and no separate
  FastAPI process.
- **Recommended: B-proxy.** A thin Sites server forwards GET/HEAD requests to one approved
  public-read Next Web origin: Railway `production` Web, which runs the merged master with a private
  API and private DB.
  - `/admin*` returns 404.
  - The proxy holds no secrets and writes nothing.
- **Blocked on owner gate G1.** No current public-read origin exists:
  - staging is stale and not production truth
  - Railway production has 0 services
  - the state of the Mac canonical host is UNKNOWN
- **Alternatives:**
  - C1: a release-time public-projection snapshot. Needs owner approval of a hosted snapshot.
  - C2: Railway Web is canonical and the Site is only a launch page.
- See runbook §3.

## 5. Site name

**모두의국감**

## 6. Public purpose

**국정감사 참여 인력의 공개 이력과 근거 검색**

## 7. Data that may be shown

Only what the existing public API projections return:

- public canonical Persons (`/people`, `/people/{id}`) with their published Claims, Evidence, Sources
  and policy summaries
- discovery facets: role, party, district, committees, reelection
- the ontology local view
- public Organizations
- the Claim-backed 2026 Gukgam targets and committee rosters
- source-listed witness and reference rows exactly as the API returns them: text only, never linked
  to a Person
- the reviewed portrait asset

## 8. Data that must never be shown

Do not show:

- phone numbers, emails, staff, family or addresses
- `TEL_NO`, `E_MAIL`, raw or normalized payloads
- REVIEW, UNRESOLVED or DRAFT People and Claims (NEC/ALIO source-context)
- roll-call votes, scores, rankings, ideology or evaluations
- name-matched or inferred links
- the operator console, tokens, `DATABASE_URL`, provider keys, private API origins or
  `*.railway.internal`
- anything taken directly from the owner-supplied 「2026년도 국정감사수첩」(10/01 기준). It is a
  discovery-only schedule inventory (`DISCOVERY_SCHEDULE_INVENTORY_NOT_CLAIMS`), not a Claim
  source. Its 연락처 sections (의원실·위원회 공무원·전문위원·기관 국회담당자) must never be published
  or bundled into a Site.

## 9. Staging and production state

| Surface | State |
|---|---|
| Staging Web `https://web-staging-efe2.up.railway.app` | 200, old "Civic Intel" title, noindex, `/gukgam/2026` returns `SERVICE_UNAVAILABLE`. Do not use it as the public origin. Keep it noindex. |
| Railway `production` | Environment exists, 0 services, IaC prepared (`.railway/railway.ts`) |
| Mac mini | Canonical write DB. State UNKNOWN. Refresh script: `deploy/refresh-staging-db.sh` |

## 10. Environment variables needed

**Railway production `api`:**
- `DATABASE_URL` (from the DB reference)
- `CIVIC_BOOTSTRAP_MODE=runtime`
- `PORT=8000`

**Railway production `web`:**
- `CIVIC_API_URL` (private domain)
- `PORT=3000`
- `CIVIC_PUBLIC_BASE_URL` and `CIVIC_INDEXING_ENABLED=true`: set only at the indexing step, §15

**Sites hosted env (B):**
- `MODUIGUKGAM_UPSTREAM_ORIGIN`: the https origin of the production Web. It is not a secret.

**DB refresh (one-shot, owner-run or approved):**
- `SOURCE_DATABASE_URL`
- `TARGET_DATABASE_URL`
- `BACKUP_DIR`

## 11. Secret names only

`DATABASE_URL`, `SOURCE_DATABASE_URL`, `TARGET_DATABASE_URL`, `CIVIC_OPERATOR_TOKEN`,
`ASSEMBLY_API_KEY`, `NEC_API_KEY`, `NKIS_API_KEY`, `DART_API_KEY`, `MOIS_ORG_CODE_API_KEY`.

None of them goes into Sites, its prompts, `.openai/hosting.json`, the Web bundle, logs or receipts.

## 12. Sites preview steps

1. Get the G1 approval. Then:
   - plan and apply Railway production
   - refresh the DB with the equality check passing
   - confirm `/ready` returns 200
   - give only the Web a generated domain
2. Run `python -m workers.public_beta_preflight --web-base-url https://<railway-web> --expect-indexing disabled --person-id <real id> --organization-id <real id>`. It must PASS.
3. In ChatGPT (desktop Codex or Work), use `@Sites` to create a Site named **모두의국감** from the
   minimal proxy project (runbook §3 rules).
4. Set `MODUIGUKGAM_UPSTREAM_ORIGIN`. Save a version and keep the audience at owner-only.
5. Review the private preview using the QA in §13.

## 13. Desktop and mobile QA

Test at 390 px and on desktop, logged out.

**Home (`/`):**
- 모두의국감 appears in the header and the title
- the search box is in the first viewport
- the today line and the 자료 범위 section are present

**Search:**
- a real public name leads to `/people?q=` and shows the result
- the person detail shows 핵심 기록, and 근거 열기 reveals the source card
- the same-name warning shows wherever duplicates exist
- a nonsense query shows "검색 결과가 없습니다"

**Gukgam (`/gukgam/2026`):**
- the date index works and the `#audit-YYYY-MM-DD` deep links resolve
- with no data, the page shows the source-gated empty state

**Errors and admin:**
- a random person UUID returns the Korean 404
- `/admin/review` returns 404 with the title "모두의국감"

**Leaks:** scan the HTML and network responses for emails, phone numbers, `TEL_NO`, tokens and
internal hosts. There must be no write controls.

**Robots:** `robots.txt` and the meta tags must match the intended indexing state.

## 14. Public publish steps

1. Deploy the **reviewed saved version**. Every deployment URL is production.
2. Set the audience to **Anyone on the internet**. This needs public publishing enabled on the
   account or workspace.
3. Record the default URL `<slug>.openai.chatgpt.site`. A slug such as `moduigukgam` is fine. Do not
   buy or connect a domain.
4. Open the URL as an unauthenticated visitor and repeat §13.
5. Run preflight against the Sites URL with `--expect-indexing disabled`.

## 15. Canonical URL, robots, sitemap and indexing

- Launch noindex. After the public smoke passes, and only if the Sites URL is the canonical public
  surface (B):
  1. Set `CIVIC_PUBLIC_BASE_URL=https://<site-host>` and `CIVIC_INDEXING_ENABLED=true` on the
     production Web only, then redeploy it.
  2. Preflight the Sites URL with `--expect-indexing enabled`.
  3. Check `rel=canonical`, `og:url`, `robots.txt`, and that the sitemap host is the Sites host.
- Never on staging.
- Under C2, the Railway or custom domain is canonical. Do not index the Sites page as a duplicate.
- Sites-native robots/SEO is undocumented. If the proxy cannot pass through `robots.txt` and meta
  tags, stay noindex and report it.

## 16. Rollback and unpublish

- **Unpublish:** set the audience back to owner-only. Never delete the Site; deletion is permanent.
- **Bad Site version:** redeploy the previous saved version.
- **Bad Web build:** redeploy the previous Railway image.
- **Indexing mistake:** unset `CIVIC_INDEXING_ENABLED` on the production Web.
- **Code:** revert `3dc51ca`. It has no schema or data impact.

## 17. STOP conditions

Stop and report with exact evidence when any of these happens:

**Cost or account:**
- Railway production services, a DB, or any paid resource or plan upgrade is about to be created
  without explicit owner approval (G1).
- A domain purchase is needed.
- Sites is unavailable on the account, public publishing is disabled, or a usage limit is hit.

**Data or security boundary:**
- Any path would give the FastAPI or PostgreSQL a public domain, add a public or token-protected API,
  or copy secrets into Sites.
- The only working shape needs D1/R2 or bundled data (C1) and the owner has not approved it.
- The network-access policy blocks the upstream host.

**Quality or safety:**
- CI is not green, or the PR is not merged.
- Any preflight or QA check fails.
- A leak or an admin surface is found.
- A copy claims "모든/전체/완전한" coverage.
- The DB refresh equality check fails, or the Mac canonical DB is unreachable.

## 18. Ready-to-paste Codex prompt

```text
You are Codex. You will deploy the public site "모두의국감" through ChatGPT Sites. It is the public
name of the Civic Intel public-read surface. Its purpose is 국정감사 참여 인력의 공개 이력과 근거 검색.

Repository: github.com/sionchu/civic-intel. Windows checkout: C:\Users\getch\ci-wt-frontend. Create
a new worktree from current origin/master. Do not reuse old ci-wt-* feature branches.

Step 1 — Revalidate
- git fetch origin master; record `git rev-parse origin/master`.
- Confirm that PR https://github.com/sionchu/civic-intel/pull/193 is merged, that CI is green, and
  that master contains commit 3dc51ca. If not, STOP and report.
- Read AGENTS.md, docs/exec-plans/active/moduigukgam-public-launch-v0.md,
  docs/operations/MODUIGUKGAM_SITES_DEPLOYMENT.md,
  docs/operations/CODEX_MODUIGUKGAM_SITES_DEPLOY_HANDOFF.md and
  docs/operations/EVIDENCE_PREVIEW_DEPLOYMENT.md.
- Read the current official Sites docs:
  https://help.openai.com/ko-kr/articles/20001339-creating-and-using-chatgpt-sites and the Sites
  developer guide (learn.chatgpt.com/docs/sites).
- Confirm that Sites and public publishing are available on this account.

Step 2 — Decide the deployment shape. Do not guess framework or network support.
- Option A (the Next server, FastAPI and PostgreSQL all on Sites) is not possible: there is no
  Postgres TCP and no separate API process. Re-confirm this on the real runtime.
- The default is B-proxy. A minimal Sites server forwards GET/HEAD requests server-side to
  MODUIGUKGAM_UPSTREAM_ORIGIN, the approved Railway production Web running merged master. It
  returns 404 for /admin*, returns 405 for other methods, strips cookies and auth headers, passes
  status codes through, and holds no secrets.
- B needs owner gate G1 first: a Railway production apply (cost), the DB snapshot refresh from the
  Mac canonical DB, and a public domain for the Web only. If G1 is not explicitly approved in
  writing, STOP before creating any Railway resource. Report what is needed. Name C1 (a release-time
  public-projection snapshot, which needs owner approval) and C2 (Railway Web canonical, with Sites
  as a launch page) as the alternatives.
- Never make the private API or Postgres public, even behind a token. Never copy DATABASE_URL,
  operator tokens or provider keys into Sites. Never use Railway staging as the public origin. Never
  turn a D1 or static dump into a truth store.

Step 3 — Build the Site
- Use @Sites. Site display name: 모두의국감. All public copy comes from the Web, which is
  Korean-first. Do not rename internal Civic Intel packages, the API or CIVIC_* variables.

Step 4 — Private preview first. Every Sites deployment URL is production.
- Save a version. Keep the audience owner-only. Review the private preview.
- Run handoff §13 QA at 390 px and on desktop: search, a real person's detail page with evidence and
  sources, /gukgam/2026, no results, 404, /admin returning 404, and a scan for leaked contacts,
  secrets or private endpoints.
- Run `python -m workers.public_beta_preflight --web-base-url <origin> --expect-indexing disabled`
  with a real --person-id and --organization-id, against the Railway Web and then the preview.
- Do not publish just because the build succeeded.

Step 5 — Public publish
- The user explicitly requested public deployment of 모두의국감. You may deploy the reviewed version
  and set the audience to "Anyone on the internet" without asking again, but only if all of these
  hold:
  - no new paid resource or plan upgrade is required beyond an already approved G1
  - no private DB or API exposure
  - no domain purchase
  - all release gates pass
  - the public audience setting is clearly confirmed
- Use the default Sites production URL. Do not buy or register a domain.

Step 6 — After publish
- Open the real public URL as an unauthenticated visitor and verify:
  - the name 모두의국감
  - root search and a public Person result
  - the Person evidence page
  - /gukgam/2026
  - no-results, 404 and mobile
  - robots and canonical behavior
  - no admin exposure and no secret leakage
- Record the actual public URL.
- If any check fails, unpublish by setting the audience to owner-only and report.

Step 7 — Indexing
- Never set CIVIC_INDEXING_ENABLED on staging or on an unrelated service.
- If the Sites URL is canonical (B), set CIVIC_PUBLIC_BASE_URL=https://<site-host> and
  CIVIC_INDEXING_ENABLED=true on the production Web only, redeploy, and run preflight with
  --expect-indexing enabled against the Sites URL. Verify canonical, og:url, robots and sitemap.
- If Railway Web stays canonical (C2), say so and avoid duplicate-index conflicts.
- If Sites cannot pass robots and meta through, stay noindex and report.

Step 8 — Receipt
- Fill the Receipt table in docs/exec-plans/active/moduigukgam-public-launch-v0.md with: deployed
  commit, Site URL, Site name, KST timestamp, access setting, preview QA, public smoke, indexing
  status, known coverage limits and the rollback/unpublish path. Commit it on a branch and open a PR.
- Do not say "deployed" without the real URL and a successful public smoke.

Approval boundary. These are approved: code preparation, Sites private preview, Sites public
publish, the default Sites URL, minimal UI/metadata/SEO changes, and the public audience setting.
These need explicit owner approval:
- Railway production services or a DB (cost)
- any plan upgrade or domain purchase
- paid third-party services
- public exposure of the private API or PostgreSQL
- any security weakening
- data residency or compliance changes
- canonical DB migration to new hosting or storage, including a C1 hosted snapshot
Report unexecuted checks as NOT_RUN and blocked steps as BLOCKED, with evidence.
```

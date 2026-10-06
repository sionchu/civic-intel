# 모두의국감 — ChatGPT Sites deployment runbook

Status: `PREPARED_NOT_APPLIED`. No Site, `.openai/hosting.json`, Railway production service, domain
or indexing variable has been created by this document. Governing plan:
`docs/exec-plans/active/moduigukgam-public-launch-v0.md`.

모두의국감 is the public name of the existing Civic Intel public-read surface. It is not a second
product, a second data store or a new API. Everything in `EVIDENCE_PREVIEW_DEPLOYMENT.md` (private
FastAPI, private PostgreSQL, runtime never migrates/seeds, Mac mini canonical write DB, hosted DB is a
replaceable read snapshot) stays in force.

## 1. ChatGPT Sites constraints (official docs read 2026-10-06; re-read before acting)

Sources: help.openai.com/en/articles/20001339-creating-and-using-chatgpt-sites (ko-kr is a machine
translation of the same article) and the Sites developer guide at learn.chatgpt.com/docs/sites
(developers.openai.com/codex/sites redirects there), plus learn.chatgpt.com/docs/enterprise/sites.md.

- Public beta for Plus, Pro, Business, Enterprise and Edu. Not on Free/Go. The rollout is gradual.
  On Enterprise, both Sites and public publishing are off by default.
- You create a Site in Work (web) or in Work/Codex (desktop app) with `@Sites`. Saving, deploying and
  managing happen in ChatGPT web or the desktop app. The Codex CLI and IDE only edit and test the
  local project. The project link is stored in `.openai/hosting.json`.
- "Every deployment URL is a production URL." The safe sequence is: save a version → review the
  private preview → deploy that exact version. The deploy reports the production URL (the default
  host is `<slug>.openai.chatgpt.site`).
- A new Site is visible only to its owner and workspace admins. Audience options:
  - selected users or groups
  - invited external viewers
  - the workspace
  - "Anyone on the internet", only when public publishing is enabled

  A public Site needs no ChatGPT workspace access. Visitor access never grants editing.
- Runtime: "Some frameworks, private networks, databases, background services, and hosting patterns
  aren't supported." The docs name no framework. Storage is D1 (relational, 10 GB) and R2 (object).
  HTTP/HTTPS/WebSockets work; raw TCP does not. A Site therefore cannot open a PostgreSQL wire
  connection.
- Outbound HTTPS is allowed, subject to the workspace Sites network-access policy where one exists.
- Hosted environment variables and secrets live in Site settings and are owner-only. They never go in
  prompts, files, Site content or `.openai/hosting.json`.
- Custom domain: only a domain the owner already owns, connected through DNS. Sites does not register
  domains. Custom domains are not available on Enterprise at launch.
- To unpublish, restrict the audience. Deletion is permanent. You can list saved versions and
  redeploy one. No explicit rollback procedure is documented.
- Robots, SEO and canonical handling are **not documented**. Codex must check them on the real
  runtime.
- There is no data residency at launch, and beta usage limits apply.
- A search snippet claimed "not available in EEA/CH/UK". That was not found on the pages read, so
  treat it as UNVERIFIED.

## 2. Topology fit

The repo runs as three processes: Next standalone server (Web), FastAPI (private) and PostgreSQL
(private, DB access only through `DATABASE_URL`). A Sites runtime cannot run FastAPI as a separate
process and cannot reach PostgreSQL over TCP. Hosting the API and DB on Sites would also mean a
second data store. **Option A, the whole topology on Sites, is therefore not available.** The repo
reached the same conclusion earlier in `EVIDENCE_PREVIEW_DEPLOYMENT.md` § ChatGPT/OpenAI Sites.

Data origin as checked on 2026-10-06:

| Surface | State |
|---|---|
| Railway staging Web `web-staging-efe2.up.railway.app` | HTTP 200, title still `Civic Intel — Evidence Directory`, `noindex`. `/gukgam/2026` renders `SERVICE_UNAVAILABLE` (staging API/DB older than the Gukgam projections). Staging is not production truth. |
| Railway `production` environment | Exists with 0 services (`PREPARED_NOT_APPLIED`). |
| Mac mini canonical DB / serve host | UNKNOWN from this session. It was last reported offline on 2026-10-04 (`HANDOFF.md`). A public beta at `d167730` was mentioned but is NOT VERIFIED. |
| Private FastAPI | No public URL, by design. |

So no approved, current, public-read origin exists today. Every working Sites shape needs one owner
decision first.

## 3. Chosen shape and alternatives

**Recommended: B — Sites edge over an approved public Web origin ("B-proxy").**

- Sites hosts a minimal Workers-compatible server whose only job is to forward GET/HEAD requests
  server-side to one fixed upstream: the 모두의국감 Next Web service at the prepared commit.
- That Web service runs in Railway `production` with private API → private PostgreSQL (the existing
  `.railway/railway.ts` contract).
- The browser sees only the Sites URL. API and DB stay private. The proxy carries no secrets, does no
  writes and stores no data.
- Proxy rules:
  - The upstream origin is a hosted env var (`MODUIGUKGAM_UPSTREAM_ORIGIN`, the https origin of the
    production Web). It is not a secret.
  - Allow `GET`/`HEAD` only. Anything else returns 405.
  - `/admin` and `/admin/*` return 404 at the edge.
  - Forward the path and query only. Strip cookies and `Authorization` in both directions. Never
    forward `oai-authenticated-*` headers.
  - Pass status codes through (404 stays 404, 503 stays 503).
  - Pass through `<meta name="robots">`, `robots.txt` and `sitemap.xml` from the upstream. Indexing
    is decided once, by the Web env (§5).
- **Owner approvals required first:**
  1. Apply Railway `production`: 3 creates, 0 staging changes, 0 destroys, and no public API/DB
     domain. This has usage cost.
  2. Populate the production read snapshot from the canonical Mac DB with
     `deploy/refresh-staging-db.sh` (target = production). This needs the Mac online.
  3. Expose only the production Web through a Railway generated domain. That domain is the proxy
     upstream.

Alternatives, in case the owner declines B or Codex finds B unsupported:

- **C1 — release-time public-projection snapshot on Sites.**
  - A Workers-compatible read-only frontend renders data exported, at one verified commit, from
    exactly the public API responses (`/people`, `/people/{id}`, `/ontology/people/{id}`,
    `/sources/{id}`, `/gukgam/2026/*`, `/organizations*`).
  - The export goes into versioned Site assets or D1, carries a manifest (commit, export time, source
    revision, counts, SHA-256) and is replaced whole on every release.
  - No cost and no network exposure. The downsides:
    - It needs a new frontend adapter.
    - It is a new hosted copy without data residency.
    - The owner must explicitly accept it as a replaceable read snapshot, never a truth store.
  - Not ready today.
- **C2 — Railway production Web as canonical, Sites as a launch page linking to it.** This has the
  same Railway approvals as B and the smallest Sites content. The canonical URL is the Railway or
  custom domain, not Sites.
- **Not allowed:**
  - a public FastAPI/PostgreSQL endpoint, including a token-protected public API
  - staging as the public origin
  - D1 as a canonical DB
  - copying `DATABASE_URL`, operator tokens or provider keys into Sites

## 4. Secrets and environment (names only)

| Where | Name | Note |
|---|---|---|
| Railway production `api` | `DATABASE_URL`, `CIVIC_BOOTSTRAP_MODE=runtime`, `PORT=8000` | From IaC. Never in Sites. |
| Railway production `web` | `CIVIC_API_URL` (private domain), `PORT=3000` | From IaC. |
| Railway production `web` (later step only) | `CIVIC_PUBLIC_BASE_URL`, `CIVIC_INDEXING_ENABLED` | Set only after the canonical URL is fixed and public smoke passes (§5). |
| Sites hosted env (B only) | `MODUIGUKGAM_UPSTREAM_ORIGIN` | Public https origin of the production Web. Not a secret. |
| Never on Web or Sites | provider keys (`ASSEMBLY_API_KEY`, `NEC_API_KEY`, `NKIS_API_KEY`, `DART_API_KEY`, `MOIS_ORG_CODE_API_KEY`), `CIVIC_OPERATOR_TOKEN`, `DATABASE_URL` | |

## 5. Canonical URL, robots, sitemap and indexing

- Launch default is **noindex**. Leave `CIVIC_INDEXING_ENABLED` unset, and the Web emits
  `noindex,nofollow`, `Disallow: /` and an empty sitemap.
- Indexing comes only after: the public Sites URL exists → the B-proxy public smoke passes → set
  `CIVIC_PUBLIC_BASE_URL=https://<site-host>` and `CIVIC_INDEXING_ENABLED=true` on the
  **production** Web only → redeploy → run
  `python -m workers.public_beta_preflight --web-base-url https://<site-host> --expect-indexing enabled`.
- Canonical, OG URL and the sitemap host then point at the Sites host. The Railway generated domain
  serves the same pages with `rel=canonical` → Sites. Railway staging stays noindex. Do not set
  indexing variables on staging.
- Under C2 the canonical URL is the Railway or custom domain, and Sites must not claim to be
  canonical.

## 6. Sequence (B)

1. Revalidate:
   - `origin/master` contains the prepared commit
   - CI is green
   - Sites is available and public publishing is enabled
   - the network-access policy allows the upstream host
2. With owner approval: plan, then apply Railway production. Run the DB refresh with its
   count/revision equality check. Verify `/ready` is 200, then give only the Web a generated domain.
3. Run `python -m workers.public_beta_preflight --web-base-url https://<railway-web> --expect-indexing disabled --person-id <id> --organization-id <id>`.
4. Create the Site "모두의국감" with the proxy. Save a version and review the private preview at
   owner-only audience (QA §7).
5. Deploy the reviewed version and set the audience to Anyone on the internet. Record the URL.
6. Run the public smoke as an unauthenticated visitor (§7), then preflight against the Sites URL
   (`--expect-indexing disabled`).
7. Optional same day: enable indexing per §5.
8. Write the release receipt (`docs/exec-plans/active/moduigukgam-public-launch-v0.md` § Receipt).

## 7. Smoke and QA

Run at 390 px mobile and desktop, in a logged-out browser:

- `/`: 모두의국감 in the header and `<title>`, the search box is in the first viewport, and the
  today (KST) schedule line plus the coverage section are shown.
- Search a real public name (for example, a current member's name) → `/people?q=…` lists that person
  → the detail page shows 핵심 기록 → open 근거 → the source card shows the policy and date.
- Search a nonsense string → "검색 결과가 없습니다."
- `/gukgam/2026`: dates/committees/targets or the source-gated empty state. Never assert "no audit".
- `/people/<random-uuid>` → 404 "기록을 찾을 수 없습니다". `/admin/review` → 404 with title
  "모두의국감" only.
- No `TEL_NO`, `E_MAIL`, email addresses, phone numbers, staff or family data, tokens, API origins
  or `railway.internal` in HTML or network responses. No write controls.
- `robots.txt` and the robots meta match the intended indexing state.

## 8. Rollback and unpublish

- Unpublish: set the Site audience back to owner-only. The URL stops being public immediately.
  Never delete the Site; deletion is irreversible.
- Bad Site version: redeploy the previous saved version.
- Bad Web build: redeploy the previous Railway image (compatible schema). Downgrade only on a
  restored disposable copy.
- Indexing mistake: unset `CIVIC_INDEXING_ENABLED` on the production Web and redeploy. robots
  returns `Disallow: /`.

## 9. Codex authority

Codex may do these without asking:

- read docs and repo
- run local checks
- create the Site
- save versions and use the private preview
- deploy a reviewed version and set the audience to public
- set the non-secret `MODUIGUKGAM_UPSTREAM_ORIGIN`
- run read-only smoke and preflight
- write the receipt
- unpublish on a failed smoke

Codex must get explicit owner approval before any of these:

- creating Railway production services or any paid resource or plan upgrade
- loading or copying DB data
- giving any API/DB a public domain or relaxing auth
- buying or connecting a domain
- adopting C1 (a hosted data snapshot)
- changing data residency or compliance scope
- turning on indexing anywhere other than the production Web after a passing public smoke

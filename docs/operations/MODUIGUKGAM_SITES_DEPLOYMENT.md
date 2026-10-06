# 모두의국감 — ChatGPT Sites deployment runbook

Status: `PREPARED_NOT_APPLIED`. No Site and no `.openai/hosting.json` exist yet. No Railway
production service, domain or indexing variable has been created.

- Governing plan: `docs/exec-plans/active/moduigukgam-public-launch-v0.md`.
- Owner decision (2026-10-06, in thread): generate the site **from the Mac canonical DB** and ship it
  **through ChatGPT Sites**.

모두의국감 is the public name of the existing Civic Intel public-read surface. It is not a second
product, data store or API. Everything in `EVIDENCE_PREVIEW_DEPLOYMENT.md` stays in force: private
FastAPI, private PostgreSQL, the runtime never migrates or seeds, and the Mac mini holds the canonical
write DB.

## 1. ChatGPT Sites constraints (official docs read 2026-10-06; re-read before acting)

Sources:
- help.openai.com/en/articles/20001339-creating-and-using-chatgpt-sites (the ko-kr page is a machine
  translation of the same article)
- learn.chatgpt.com/docs/sites (developers.openai.com/codex/sites redirects here)
- learn.chatgpt.com/docs/enterprise/sites.md

What they say:
- **Availability.** Public beta for Plus, Pro, Business, Enterprise and Edu; not Free or Go. The
  rollout is gradual. On Enterprise, both Sites and public publishing are off by default.
- **Where it runs.** Sites are created in Work (web) or Work/Codex (desktop app) with `@Sites`.
  Saving, deploying and managing happen only in ChatGPT web or desktop. The project link lives in
  `.openai/hosting.json`.
- **Deploys are production.** "Every deployment URL is a production URL." Save a version, review the
  private preview, then deploy that exact version. The default host is
  `<slug>.openai.chatgpt.site`.
- **Audience.** A new Site is limited to its owner and workspace admins. "Anyone on the internet" is
  available only when public publishing is enabled. Visitors never get editing rights.
- **Runtime.** Some frameworks, private networks, databases, background services and hosting
  patterns are not supported. HTTP/HTTPS/WebSockets work; raw TCP does not. Storage is D1 and R2.
- **Settings.** Hosted env and secrets are owner-only Site settings. Custom domains are only
  owner-owned domains connected through DNS.
- **Unpublish.** Restrict the audience. Deleting a Site is permanent. Saved versions can be listed
  and redeployed.
- **Not documented.** Robots, SEO and canonical handling: Codex verifies these on the real runtime.
  There is no data residency at launch, and beta usage limits apply.

## 2. Chosen shape: static public-read snapshot built from the Mac canonical DB

```text
Mac canonical PostgreSQL ──(DATABASE_URL, Mac only)──▶ private FastAPI on 127.0.0.1
        ▶ `npm --prefix apps/web run build:sites -- --api http://127.0.0.1:8000`
        ▶ dist/moduigukgam-site/  (static HTML/JS + snapshot-manifest.json)
        ▶ ChatGPT Sites (static assets only) ▶ public visitors
```

- The bundle is this repository's own Next app rendered with `output: "export"`. Pages, evidence
  panels, same-name warnings and empty or UNKNOWN states are identical to the server build.
- **Nothing private leaves the Mac.**
  - The API and DB are contacted only at build time, on loopback.
  - The bundle holds no API origin, credentials, operator surface or write path. `/admin` is not
    built.
  - Sites needs **no env vars and no secrets**.
- **It is a replaceable read snapshot, not an SSOT.**
  - `snapshot-manifest.json` records `REPLACEABLE_PUBLIC_READ_SNAPSHOT_NOT_SSOT`, the commit, KST
    time, counts and the bundle SHA-256.
  - The footer shows "자료 기준 … (공개 기록 스냅샷)".
  - Never edit the bundle. Rebuild it from the DB.
- **It reads at least as tightly as the live site.** It contains exactly what the public API returns
  (`/people`, `/people/{id}`, ontology, `/sources/{id}`, `/organizations*`, `/gukgam/2026/*`):
  published Claim/Evidence for public canonical Persons and Organizations only.
- **"Today" stays correct.** 오늘/다음/지난 schedule labels are computed in the reader's browser
  (KST), so they stay right between rebuilds. `?q=` search is restored in the browser.
- **Rebuilding.** New data is a rebuild followed by a Sites save-and-deploy. Between rebuilds the
  site shows the snapshot as of its build time.

The build fails closed when any of these is true:
- `/ready` is not ready
- `/people` is empty
- any required route or public Person page is missing
- an `admin/` path is present
- the bundle contains `TEL_NO`, `E_MAIL`, `normalized_payload`, `raw_payload`, `railway.internal`,
  the operator token header, a `postgresql://` URL or the API origin
- an HTML or RSC payload contains email-like text

Shapes that were not chosen:
- **Next/FastAPI/Postgres on Sites:** impossible, because Sites has no TCP to PostgreSQL and cannot
  run a separate API process.
- **Sites proxy to a Railway production Web:** needs paid production services.
- **Exposing the API to Sites:** forbidden.
- **Railway staging as the public origin:** staging is stale and is not production truth.

## 3. Build host prerequisites (the Mac mini)

1. The Mac is online and the canonical PostgreSQL is reachable locally. Its state is UNKNOWN in this
   session. It was last reported offline on 2026-10-04.
2. Make a clean checkout of the **merged master** that contains PR #193. Record `git rev-parse HEAD`.
   The manifest records `git_worktree_dirty`; it must be `false`.
3. Install with `python -m pip install .` and `npm --prefix apps/web ci`.
4. Start the API against the canonical DB, bound to loopback only. Prefer a read-only DB role if one
   exists.

   ```sh
   CIVIC_BOOTSTRAP_MODE=runtime DATABASE_URL=<canonical, from the Mac env file> \
     python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000
   ```

   `curl -s http://127.0.0.1:8000/ready` must return `{"status":"ready"}`.
5. Build: `npm --prefix apps/web run build:sites -- --api http://127.0.0.1:8000`. It must end with
   `"status": "PASS"`. The output goes to `dist/moduigukgam-site/`, or to the path given with
   `--out`.
6. Stop the API.
7. Smoke-test locally:

   ```sh
   python -m http.server 8090 --bind 127.0.0.1 --directory dist/moduigukgam-site
   python -m workers.public_beta_preflight --web-base-url http://127.0.0.1:8090 \
     --expect-indexing disabled --person-id <real> --organization-id <real>
   ```

   It must PASS.

Check that the manifest counts match what you expect from the canonical DB. As of 2026-10-04 the
DB had 151 public Gukgam targets across 7 committees and 444 Organizations. The public People count
must be re-measured.

### 3a. Witness lists (증인·참고인) — before the snapshot build

Witness rows are published as committee-scope Claims on `국회 <위원회>` Organizations. Names stay
source-listed text and are never linked to a Person. Each canonical-DB write below needs two owner
actions: review of the packets and approval of the exact plan SHA.

1. Copy `C:\Users\getch\civic-intel-acquisition\gukgam-2026` to the Mac, for example to
   `/Users/lee/Developer/civic-intel-acquisition/gukgam-2026`. Re-verify the artifact SHA-256 values.
2. The owner reviews each packet with `WITNESS_REVIEW_2026-10-06.md` in that folder and sets
   `"review_status": "HUMAN_REVIEWED"` on every accepted packet. This step is owner-only. For 산자위,
   approve one version only.
3. Import each reviewed packet as observations only. Run it without `--commit` first:

   ```sh
   python -m workers.gukgam_witness_import --packet <packet.json> --artifact <original file> \
     --confirm-exact-attachment-rights --database-url "$DATABASE_URL" [--commit]
   ```

   `--confirm-exact-attachment-rights` is the owner's confirmation that the attachment's rights
   were reviewed.
4. Dry-run Claims for all imported packets together:

   ```sh
   python -m workers.gukgam_witness_claim_commit --database-url "$DATABASE_URL" \
     --create-committee-organizations --packet <p1> --packet <p2> ...
   ```

   The owner approves the printed `plan_sha256` and the committee Organizations to create. Then
   rerun the same command with `--commit --expected-plan-sha256 <sha>`. Reruns are idempotent and
   reuse existing Claims.
5. Continue with the snapshot build.
   - `/gukgam/2026/` shows the 공식 증인·참고인 명단.
   - `/people/?q=<이름>` lists matching witness rows below the Person results, with the note
     "인물 기록과 자동 연결하지 않음".

**Rehearsal.** Run on a disposable SQLite copy, with packets marked reviewed in scratch only (this
is not an attestation):
- 16 packets were imported, producing 1,850 Claims and 12 committee Organizations.
- The snapshot build passed.
- The bundle was 87 MB, mostly committee Organization pages, each up to about 5 MB of HTML for
  roughly 300 Claims. Codex checks this against the Sites asset limits.

## 4. Sites sequence

1. In ChatGPT (desktop Codex/Work, or Work on the web), ask `@Sites` to create a Site named
   **모두의국감** from the folder `dist/moduigukgam-site` as a **static site**. Confirm the project
   produces compatible deployment artifacts.
   - Do not add a server, D1, R2, env vars or secrets.
   - Request the URL slug `moduigukgam` if it is free; otherwise use any lowercase slug.
2. **Save a version** and keep the audience owner-only. Run the private preview QA in §6.
3. **Deploy that saved version.** Set the audience to **Anyone on the internet**. Record the URL.
4. Run the public smoke in §6 as a logged-out visitor, plus preflight against the Site URL.
5. To update later:
   - rebuild into the **same folder**; the build keeps `.openai/`
   - save a version, preview it, then deploy it
   - every deploy is production

## 5. Canonical URL, robots, sitemap and indexing

- Launch with **noindex**. The default build emits `noindex,nofollow`, `Disallow: /` and an empty
  sitemap.
- Turn indexing on only after the public smoke passes, and only if the Sites URL is the canonical
  public surface:
  1. Rebuild with
     `-- --api http://127.0.0.1:8000 --base-url https://<site-host> --index`. This emits
     `index,follow`, `rel=canonical`, `og:url`, robots `Allow: /` plus the sitemap line, and sitemap
     URLs with trailing slashes. These were verified locally.
  2. Save a version, preview it, deploy it.
  3. Run preflight with `--expect-indexing enabled`.
- Sites-native robots handling is undocumented. If Sites overrides `robots.txt` or the meta tags,
  stay noindex and report it.
- Railway staging stays noindex. Do not set indexing variables on any Railway service for this
  launch.

## 6. Smoke and QA (390 px mobile and desktop, logged out)

- **`/`:**
  - 모두의국감 appears in the header and the `<title>`
  - the search box is in the first viewport
  - the 오늘 (KST) date matches the real date
  - the schedule line and the 자료 범위 section are present
  - the footer shows 자료 기준 with the build time
- **Search:**
  - searching a real current member's name lands on `/people/?q=…` with that person listed
  - the detail page shows 핵심 기록 and 근거 열기, and the source card shows policy and date
  - client navigation between pages works
  - a nonsense query shows "검색 결과가 없습니다"
- **`/gukgam/2026/`:**
  - the date index and `#audit-YYYY-MM-DD` links resolve
  - today's KST date is labelled 오늘 if it is in the plan
- **404 and admin:**
  - `/people/<random-uuid>/` returns the Korean 404, or the host's 404 if Sites ignores `404.html`.
    Record which one.
  - `/admin/review/` returns 404
- **Leaks:**
  - no emails, phone numbers, `TEL_NO`, tokens, `127.0.0.1` or internal hosts in HTML or network
    responses
  - no forms other than the GET search
- **Indexing:** `robots.txt`, the meta robots tag and `/snapshot-manifest.json` match the intended
  indexing state.

## 7. Rollback and unpublish

- **Unpublish:** set the audience back to owner-only. Never delete; deletion is permanent.
- **Bad version:** redeploy the previous saved version.
- **Bad data:** rebuild from the DB, then save, preview and deploy. Never hand-edit the bundle.
- **Indexing mistake:** rebuild without `--index`, then save, preview and deploy.
- **Code:** revert the merge of PR #193. It has no schema or data change.

## 8. Authority

**Codex may do these without asking:**
- read docs and the repo
- run local checks
- run the snapshot build on the Mac against the loopback API
- create the Site
- save versions and use the private preview
- deploy a reviewed version and set the audience to public
- run read-only smoke and preflight
- enable indexing per §5 after a passing public smoke
- write the receipt
- unpublish on a failed smoke

**These need explicit owner approval:**
- any paid resource or plan upgrade, including Railway production
- any public API or DB endpoint, tunnel or proxy, or any relaxed auth
- copying `DATABASE_URL`, operator tokens or provider keys anywhere except the Mac API process
- buying or connecting a domain
- adding Sites D1/R2, server code or secrets
- changing data residency or compliance scope beyond this static public snapshot
- writing to the canonical DB (the witness import and Claim commit in §3a run only after the
  owner has reviewed the packets and approved the exact plan SHA)

# 모두의국감 — ChatGPT Sites deployment runbook

Status: `RELEASE_01_LOCAL_REVIEW_WITH_BLOCKERS` (2026-10-08). Native read-only Sites inspection
confirmed the existing `moduigukgam` Site at version 3, active/public, with no D1 bindings:
`https://moduigukgam.leeje92.chatgpt.site`. This does not verify its current source commit or
served contents. RELEASE-01 made no Site, hosted D1, access, secret or canonical DB change.

- Governing plan: `docs/exec-plans/active/moduigukgam-public-launch-v0.md`.
- The D1-backed Worker candidate, current evidence and blockers are in
  `docs/exec-plans/active/sites-storage-split-v0.md`. The current full static input exceeds the
  256 MiB limit; it is not a passing large-data fallback. Cutover requires separate owner approval.
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

## 2. Existing static path: public-read snapshot built from the Mac canonical DB

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

The build fails closed when any of these is true (including the unchanged 256 MiB limit):
- `/ready` is not ready
- `/people` is empty
- any required route or public Person page is missing
- an `admin/` path is present
- the bundle contains `TEL_NO`, `E_MAIL`, `normalized_payload`, `raw_payload`, `railway.internal`,
  the operator token header, a `postgresql://` URL or the API origin
- an HTML or RSC payload contains email-like text
- the uncompressed bundle exceeds 256 MiB

### 2a. RELEASE-01 Worker candidate (local-only; not a cutover)

Reuse the same Next UI and `data.ts -> public-read.ts` boundary. The generated Sites Worker
reads publication-gated, gzip-compressed API answers from exactly one ACTIVE local D1 snapshot;
PostgreSQL remains the canonical store. The footer displays that snapshot's `generated_at_kst`,
while schedule today/next/past remains a reader-time KST fact.

The fixed 1,142-Person input measured 5,164,508,878 B for static export (guard FAIL), versus
1,724,822 B for the final clean Mac Worker artifact (GREEN). Data is outside the code artifact:
4,028 paths / 6,372 parts / 105,913,861 gzip bytes. No R2 or hosted write endpoint is introduced.
These replace the older 504-Person measurements as current local evidence; full measurements,
hashes, commands, 27-route comparison and retained screenshot locations are in the active plan.

Local procedure on an isolated checkout:

```sh
node apps/web/scripts/export-public-projection.mjs --api http://127.0.0.1:8100 --out <local-projection>
node apps/web/scripts/build-sites-worker.mjs --out <local-worker> --load-local <local-projection>
```

Use the existing healthy loopback API when authorized; never restart it merely for this build.
Windows scoped npm command, when the installed npm reproduces the retained lock issue:

```powershell
npx --yes npm@11.21.0 exec -- node apps/web/scripts/build-sites-worker.mjs
```

The generated stage applies schema and dataset only via Wrangler `--local`. STAGED data is
validated against exact metadata, paths, parts, statuses, hashes and gzip bytes before one atomic
ACTIVE/PREVIOUS transition. Keep the intended previous projection's validated `rollback.sql`.
Load/activate/rollback retries are idempotent. Rebuilding preserves local D1. Schema-1 projections
require a schema-2 re-export; do not weaken the reader or edit canonical records to accommodate it.

The installed Sites 1.0.0-c storage guide requires bounded schema-only migrations and keeps seeds
outside them. Current native D1 tools provide bounded reads only. A Sites-managed hosted bulk
writer was not verified. Cloudflare account-level import commands are not proof of Sites access.
Do not use an unauthenticated endpoint, embed seed data in a migration, or invent an import path.
Binding, writer design/secrets, fresh hosted load, private preview, save/deploy and public change
are separate owner approvals. The largest Person's Aside rendered comparison remains BLOCKED;
do not call the candidate `READY_FOR_CUTOVER`.

Shapes that were not chosen:
- **Next/FastAPI/Postgres on Sites:** impossible, because Sites has no TCP to PostgreSQL and cannot
  run a separate API process.
- **Sites proxy to a Railway production Web:** needs paid production services.
- **Exposing the API to Sites:** forbidden.
- **Railway staging as the public origin:** staging is stale and is not production truth.

## 3. Build host prerequisites (the Mac mini)

1. On 2026-10-08 the Mac's existing loopback API at port 8100 was ready and returned 1,142 public
   People / 387 Organizations. Recheck readiness before a later build; this is not a standing
   authorization to write or restart the canonical service.
2. Make a clean checkout of the approved source commit. Record `git rev-parse HEAD`.
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
6. Stop only an API process started and owned by this build. Leave an existing canonical API running.
7. Smoke-test locally:

   ```sh
   python -m http.server 8090 --bind 127.0.0.1 --directory dist/moduigukgam-site
   python -m workers.public_beta_preflight --web-base-url http://127.0.0.1:8090 \
     --expect-indexing disabled --person-id <real> --organization-id <real>
   ```

   It must PASS.

Check manifest counts against the captured public API input. RELEASE-01 measured 1,142 People,
387 public Organizations, 151 Gukgam targets and 1,731 witness/reference rows; the actual Gukgam
page had 2,963 anchors. These are dated observations, not fixed future requirements.

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

All steps below require separate owner approval under RELEASE-01. Its local QA does not authorize
publication. A failing full static bundle cannot be saved as a passing fallback.

1. Reuse the existing **모두의국감** Site (`moduigukgam`) and its exact returned project ID;
   do not create a duplicate Site. For the static path, use a verified passing static artifact.
   - Do not add a server, D1, R2, env vars or secrets.
2. **Save an approved version** and run owner-private version-preview QA in §6. Preserve the
   existing published Site's audience; do not restrict it merely to review an unpublished version.
3. **Deploy that reviewed saved version** only after owner approval. Preserve the existing audience;
   any public-access change needs separate approval. Record the exact version and URL.
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
  - the static footer shows the capture/build time; the Worker footer shows ACTIVE snapshot time
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
- **Code:** redeploy the last known-good saved version after approval. A source revert must target
  the actual faulty change; PR #193 is not the Worker cutover. Do not claim the full large-data
  static rebuild passes merely because an earlier saved static version remains available.

## 8. Authority

**RELEASE-01 may do these without asking:**
- read docs, repository, existing Site metadata and publication-gated loopback API responses
- install local dependencies; run local tests/builds/previews and read-only smoke
- write schema/data only to disposable local D1; validate lifecycle and rollback
- make verified code commits and update existing PR #204 without force-pushing or merging master
- update the active plan and this runbook with executed evidence

**These need explicit owner approval:**
- hosted D1 creation, binding, import, activation or a hosted writer/security design
- Sites project/settings changes, version save, hosted private preview, deploy or access changes
- public publication, indexing or unpublishing
- any paid resource or plan upgrade, including Railway production
- any public API or DB endpoint, tunnel or proxy, or any relaxed auth
- copying `DATABASE_URL`, operator tokens or provider keys anywhere except the Mac API process
- buying or connecting a domain
- adding Sites D1/R2, server code or secrets
- changing data residency or compliance scope beyond this static public snapshot
- writing to the canonical DB (the witness import and Claim commit in §3a run only after the
  owner has reviewed the packets and approved the exact plan SHA)

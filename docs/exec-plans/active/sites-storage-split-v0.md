# 모두의국감 Sites storage split v0 (D1 public read projection)

**Status: `P0_PROVEN_LOCALLY_CUTOVER_NOT_APPROVED`.** The D1-backed Sites Worker candidate builds
and serves the same public pages from a local D1. The static snapshot is still the only production
path. No Site setting, storage binding, D1 database, deploy or paid resource was created or changed.

- Branch `feat/sites-storage-split-v1`, rebased on `origin/master` `109db9b` (PR #200, #201, #202
  merged). Worktree `/Users/lee/Projects/civic-intel-wt-sites-storage`.
- Runbook for the current static path: `docs/operations/MODUIGUKGAM_SITES_DEPLOYMENT.md`.

## Problem: public data growth is the deployment artifact

Baseline A, the current canonical state: the static bundle built from `0143c23`
(`civic-intel-deploy/dist/moduigukgam-site-0143c23`). It has 504 public People, 387 Organizations
and the applied PR #200 data (62 committee roles, 542,361 vote Claims; 10 recent votes per page).
Measured with `node apps/web/scripts/bundle-size-report.mjs <bundle>`:

| | Bytes | Share |
|---|---|---|
| Total (2,719 files) | 246,474,169 (235.06 MiB; 91.8% of 256 MiB) | |
| `organizations/` detail + directory | 141,789,896 | 57.5% |
| `people/` detail + directory | 96,903,409 | 39.3% |
| `gukgam/` | 6,974,159 | 2.8% |
| Code: `_next/` JS + CSS | 669,865 | 0.3% |
| By type: HTML / RSC `.txt` | 154,759,961 / 91,002,660 | 62.8% / 36.9% |

- Person detail: 92,978,239 bytes total; mean 184,481, median 215,376, p95 246,976 bytes.
- Organization detail: mean 362,056, p95 462,209, max 8,523,124 bytes per page.
- Every record is written twice (HTML plus the RSC payload of the same data).
- The build already drops byte-identical Next payloads (PR #195, #199). What is left has
  23,920 bytes of identical content, so there is nothing more to deduplicate.
- Earlier bundle, `2e3c324`: 214,565,625 bytes. It had 90 member pages with a baked read error,
  which is why it was smaller.
- To stay under 256 MiB, PR #202 cut the votes shown per person from 20 to 10. The static shape
  grows linearly with records (about 184 KB per Person and 362 KB per Organization).

There is no separate Baseline B. PR #200 was already applied to the canonical DB before this work
started (receipt in HANDOFF, `pre-section-producers-20261006-201238.dump`), so the representative
state is the current state.

## Official Sites contract (read 2026-10-06)

Sources: learn.chatgpt.com/docs/sites.md, and the installed official Sites plugin
`openai-curated-remote/sites` 1.0.0-c (`skills/sites/SKILL.md`, `references/storage.md`,
`references/identity-and-secrets.md`, `templates/vinext-starter`).

| Item | Verified |
|---|---|
| D1 storage | 10 GB per Site (docs) |
| R2 storage | No fixed limit; plan usage limits apply (docs) |
| `.openai/hosting.json` | `project_id`; `d1`/`r2` hold logical binding names (`DB`, `BUCKET`) or `null`; `static: {directory}` only for static Sites (omit for Worker builds) |
| Save vs deploy | Separate steps; every deploy is production |
| Server runtime | Cloudflare Workers, 128 MB per isolate, HTTP only (plugin); Next apps run through the Vinext starter |
| Schema | Drizzle migrations in `drizzle/`; "Sites applies hosted migrations before uploading the Worker"; migrations are schema-only |
| Seed or backfill data | "Backfills and seed datasets belong outside migrations." |
| Local D1 | Miniflare via `wrangler d1 execute --local` against the built `dist/server/wrangler.json` |
| Statement size | `SQLITE_TOOBIG` at about 100 KB, observed in local D1 (so rows are chunked) |

**NOT_VERIFIED: how to load rows into the hosted D1.** No documented import, update or bulk-load
tool exists. The documented writer paths are:

- a Site-hosted endpoint, which on a public Site needs its own authorization (a Site secret)
- the owner-private service token (`siwc_bypass_bearer_token`)
- a Site MCP tool

Each adds a write path or a secret to the production Site, so each needs owner approval. This P0
does not build any of them.

## Decision

- **PostgreSQL** stays the canonical SSOT.
- **D1** holds a `REPLACEABLE_PUBLIC_READ_SNAPSHOT_NOT_SSOT`: the exact publication-gated API
  responses, keyed by the API path each page already requests, gzip-compressed.
  - No PostgreSQL schema is copied and no domain model is rebuilt.
  - No identity, publication, SourcePolicy or FACT/UNKNOWN decision is made in D1 or in the Worker.
- **The Sites artifact** is code only. The same Next app runs on the official Vinext starter, and
  `app/public-read.ts` is swapped for a D1 transport at build time.
- **R2: `DEFERRED_NOT_NEEDED_FOR_P0`.** The only binary in the bundle is one reviewed portrait
  (38 KB). No public PDFs or large files are served.
- **Vote universe.** The 542,361 vote Claims stay in PostgreSQL. A Person response carries at most
  `RECENT_PLENARY_VOTE_LIMIT` (10) votes plus aggregates, and the exporter fails if any Person
  carries more.

## Implemented P0

| File | What it does |
|---|---|
| `apps/web/app/public-read.ts` | The one HTTP transport, extracted from `data.ts`, which now calls `readPublic(path)`. Behaviour is unchanged. |
| `apps/web/app/portrait.ts` | Imports the portrait manifest instead of reading it from disk at request time (Workers have no project filesystem). |
| `apps/web/scripts/export-public-projection.mjs` | Reads `/ready`, `/people`, `/organizations`, `/gukgam/2026/*`, every Person/Organization detail, ontology, money comparison and every cited `/sources/{id}`. Writes `projection-manifest.json`, `load.sql`, `activate.sql` and `rollback.sql`. |
| `apps/web/sites-worker/` | Drizzle schema plus generated migration (`snapshot_meta`, `public_read`), and the D1 transport `public-read.d1.ts`. |
| `apps/web/scripts/build-sites-worker.mjs` | Stages the installed plugin's Vinext starter with this app and the D1 transport, typechecks, builds, scans and writes the generated Sites project and `worker-manifest.json`. `--load-local` loads a projection into local D1. |
| `apps/web/scripts/bundle-size-report.mjs` | Size attribution. The static build now adds a compact `size` block to `snapshot-manifest.json`. |
| `apps/web/scripts/public-boundary.mjs` | The one forbidden-token and email scan, shared by the static build, the Worker build and the exporter. |

Exporter guarantees:

- deterministic path order
- semantic hash over `(path, status, sha256)`; `snapshot_id = ps-<hash prefix>`
- `generated_at` and `git_commit` are transport fields kept outside the hash
- per-API-call `request_id` dropped from stored 4xx answers
- every Person must be `RESOLVED`; UUID ids only; at most 10 votes per Person
- forbidden-token and email scan on every row
- 5xx fails the export; deterministic public 4xx answers (404/422) are kept as answered
- rows split into 40,000-byte gzip parts

Snapshot activation:

- `load.sql` inserts a `STAGED` snapshot (`ON CONFLICT DO NOTHING`, so re-running is idempotent).
- `activate.sql` acts only if the staged snapshot is complete (part count matches and status is
  `STAGED`). It turns `ACTIVE` into `PREVIOUS`, then deletes the older `PREVIOUS`.
- The Worker serves only when exactly one `ACTIVE` snapshot exists.
- A missing row inside an exported scope is a public 404. Anything else is
  `SERVICE_UNAVAILABLE`, never UNKNOWN.

## Evidence (2026-10-06, Mac mini, read-only API on `127.0.0.1:8100`)

The API ran master `0143c23`; its Python code is identical to this branch.

- **Export.** 504 People, 387 Organizations, 419 Sources, 2,593 paths (386 public 4xx money
  answers), 2,602 parts. 34,654,283 JSON bytes became **5,885,251 gzip bytes**; the largest row is
  192,626 bytes before chunking.
- **Determinism.** Two runs gave the same `snapshot_id` `ps-7ab8512f102174d2` and semantic hash.
  `load.sql` rows and `activate.sql` were byte-identical.
- **Worker artifact.** **1,581,236 bytes** (1.51 MiB, 120 files); the Worker upload is 711 KiB.
  - The build has no `--api` input; the exporter is the only data path.
  - No person name from the data appears in `dist` (checked with `이준석`: 0 files).
- **Local D1.** The migration, 2,603 load statements and 4 activation statements applied. The
  Worker on `127.0.0.1:8790` served `/`, `/people`, `/people?q=…`, Person and Organization detail,
  `/gukgam/2026`, `/robots.txt` and `/sitemap.xml` with 200.
  - An unknown Person returned 404, and `/admin/review` returned 404.
  - Static assets and the reviewed portrait loaded.
- **Snapshot lifecycle in local D1.**
  - Re-running `load.sql` and `activate.sql` on the ACTIVE snapshot changed nothing (2,602 parts).
  - Activating a snapshot that was not loaded was a no-op.
  - A second snapshot went STAGED, then ACTIVE, with the old one becoming PREVIOUS.
  - `rollback.sql` swapped them back and forth.
  - Re-activating the PREVIOUS snapshot was refused because it was not STAGED.
- **Static vs D1 on 27 routes.** The routes were `/`, three directories, 17 People (12 random, the
  portrait Person, 4 non-Assembly linked People) and 6 random Organizations, compared against the
  `0143c23` static bundle.
  - Every route had the same set of Claim/Evidence/Source/record UUIDs.
  - The visible text was identical except for the footer line `자료 기준 … KST (공개 기록 스냅샷)`,
    which the Worker build does not render yet (see gaps).
- **Checks.** `make verify` PASS: ruff, typecheck, pytest (1,027 passed, 3 skipped), quality, and
  web lint, typecheck, tests (53/53) and build. The staged Worker `tsc --noEmit` passes inside
  `build-sites-worker.mjs`. `git diff --check` is clean.
- **Static path still builds.** `build-sites-snapshot.mjs` from this branch, against the same API,
  returned PASS.
  - The result is 246,474,169 bytes and 2,719 files, the same totals as the `0143c23` bundle.
  - The new `size` block in `snapshot-manifest.json` reports `budget_state: CRITICAL`
    (91.8% of 256 MiB).
  - The 220/240 MiB project thresholds are reported only; enforcing them would block today's
    production rebuild.

| Metric | Static (current, `0143c23`) | D1 Worker proof |
|---|---|---|
| Deployment artifact | 246,474,169 B (235.06 MiB) | 1,581,236 B (1.51 MiB) |
| Public People / Organizations | 504 / 387 | 504 / 387 (same records) |
| Person data inside the artifact | 96,903,409 B | 0 B |
| D1 | – | 2,603 rows; 5,885,251 B gzip payload (`load.sql` 12,508,657 B as hex SQL) |
| R2 | – | 0 (deferred) |
| Growth per added Person | about 184 KB of artifact | 0 B of artifact; about 6–7 KB gzip in D1 |

Browser QA (390 px and 1440 px) is **BLOCKED**. The Worker preview binds to Mac loopback, and
exposing it to the PC browser was refused as a local-service exposure. Client-side navigation
(RSC fetches) is therefore **NOT_RUN**; server-rendered HTML and asset loading were verified with
HTTP requests only.

## Ownership and conflicts

| Path | Needed | Other open work | Action |
|---|---|---|---|
| `apps/web/app/data.ts` | transport seam | none open | changed (body of `getJson` only) |
| `apps/web/app/portrait.ts` | Worker has no fs | none open | changed |
| `apps/web/scripts/build-sites-snapshot.mjs` | shared scan + size block | #202 merged | changed (imports, scan, manifest) |
| `apps/web/tests/ui.test.mjs` | assertions moved to `public-read.ts` | #197, #198, #175 | 3 lines; trivial rebase |
| `apps/web/app/layout.tsx` | snapshot label | #198 | **not touched** (gap below) |
| `apps/web/app/people/**`, `organizations/**`, `styles.css`, `DESIGN.md` | no | #197, #198, #175 | not touched |

## Remaining gaps before any cutover

1. **Snapshot label.** `layout.tsx` reads `CIVIC_SNAPSHOT_AT` at build time. The Worker should show
   the ACTIVE snapshot's `generated_at_kst` from D1. This is a small `layout.tsx` change after #198
   lands, and it is required before cutover.
2. **Hosted D1 load (NOT_VERIFIED).** Pick one owner-approved writer:
   - an authenticated import route with a Site secret, or
   - an owner-private import through the service token.

   Then chunk `load.sql` into `batch()` calls. A full snapshot is about 11.9 MiB of SQL (2,603
   statements).
3. **Search.** `/people` still sends all 504 directory rows (about 0.66 MB JSON) and filters in the
   browser, as the static site does. A bounded server-side search needs a `roster-grid.tsx` change
   (owned by #197/#175); it is deferred.
4. **Browser QA** at 390 px and 1440 px, including client navigation, on a private Sites preview.
5. **Indexing.** The Worker build runs with indexing off (no `CIVIC_PUBLIC_BASE_URL`). An indexed
   Worker build needs those env values set as Site settings, not baked per snapshot.

## Production cutover plan (needs owner approval at each marked step)

1. Close gaps 1 and 2 in code. Run the full verification.
2. **[owner]** Add a D1 binding to the existing Site `moduigukgam` (never a new Site), with the
   Worker source from `build-sites-worker.mjs --out <linked folder>` keeping its `project_id`.
3. **[owner]** Save a version (owner-private) so Sites applies the migration. Load and activate a
   fresh export through the approved writer, then check row count and part count against
   `projection-manifest.json`.
4. Run private-preview QA: runbook §6, plus the 27-route comparison against a static build of the
   same DB state.
5. **[owner]** Deploy the saved version (production) and run the public smoke.
6. Data refresh afterwards: export, load (STAGED), activate. No redeploy.

Rollback:

- **Data:** run the exported `rollback.sql`, which swaps ACTIVE and PREVIOUS.
- **Code or shape:** redeploy the last static saved version. The static build stays in the repo and
  keeps working; it is the fallback until the owner retires it.

## STOP

Any live Site storage binding, hosted D1 creation or load, Sites save/deploy of the Worker shape, or
paid usage needs the owner's explicit approval. None was done.

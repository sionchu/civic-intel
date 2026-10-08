# 모두의국감 Sites storage split v0

Status: `READY_FOR_REVIEW_WITH_BLOCKERS` (RELEASE-01, 2026-10-08).

The code-only D1 Worker, local snapshot lifecycle and ordinary reader flows are verified.
Full browser verification of the largest Person page remains BLOCKED: two bounded Aside
attempts ended with `fetch failed: other side closed`. Its HTTP response, input hash and UUID
comparison succeeded; these do not establish rendered-page equivalence. No cutover is approved.

## Authority and branch ownership

- This task permits code, read-only diagnosis, dependency installation, local previews and writes
  to disposable **local** D1 only. Hosted D1 creation/binding/import/activation, Sites save/deploy,
  public access changes, canonical PostgreSQL writes, new secrets and paid resources are prohibited.
  This overrides the older runbook's wider authorization.
- Existing PR [#204](https://github.com/sionchu/civic-intel/pull/204), head branch
  `feat/sites-storage-split-v1`, is reused. Work is isolated on `codex/sites-release-01` in the
  Codex-managed Windows worktree; the original checkout's `packages/domain/contracts.py` edit
  and untracked `.worktrees/` are preserved.
- Start: PR head `6a9d87e2f127ff49edfc524d91bde073bb32da11`; remote master
  `339363f5cf35502abb14fc2af04ed629a7ee8250`. Master was merged into the candidate without
  conflicts. Windows integration baseline `54923974f51bc1a2c62c6c8d728325760dd52876`;
  independently created Mac integration baseline `f4d63bc99489a6b19d413372a78a687a63a4a75e`.
  Verification below ran on these baselines with the implementation diff, before its commit.
  Final code contents matched across Windows and Mac (SHA-256 after newline normalization;
  the replay helper differed only by an extra trailing newline).
- `work/moduigukgam-reference-polish-v0` at `4debb204dbe97fb4c35c24e924f72e17cb155a1d`
  was inspected and preserved. Its Mac worktree and the old PR worktree were clean.
  No changes to its roster, schedule, date rail or CSS were made. The shared root layout received
  only snapshot-time transport wiring and request-time refresh configuration.
- Native Sites read-only inspection: existing `moduigukgam` Site, version 3, active/public at
  `https://moduigukgam.leeje92.chatgpt.site`; D1 overview returned **no bindings**. No mutation
  call was made. This metadata does not establish the currently served source commit or contents.

## Fixed input and measured RCA

The already running private Mac API on loopback port 8100 was read without restarting it or
writing to PostgreSQL. Capture completed at 2026-10-08 10:24 KST. It is a fixed collection of
publication-gated API responses, not an attestation of one atomic PostgreSQL transaction.
`serve-public-projection.mjs` replays this collection on loopback only, verifies response hashes,
performs no upstream reads and rejects non-GET/HEAD requests. SSR, static and D1 comparisons use
this same frozen input. The schema-2 re-export at 10:29 KST matched all **4,028** original
`(path, status, response SHA-256, byte count)` tuples exactly.

Schema-2 manifest:

- Snapshot `ps-b0a439f3b8327121`.
- Semantic SHA-256 `b0a439f3b8327121a7b3c23b33d00ae3cf662fd305accfcf7e944e7c2e1ef7dd`.
- 1,142 People; 387 Organizations; 578 Sources; 4,028 paths; 6,372 gzip parts;
  386 contract-valid money-comparison client-error answers.
- JSON **774,973,923 B**; gzip **105,913,861 B**. Largest complete gzip response 928,434 B,
  split into at most 40,000 B per D1 part. The activated local SQLite file was 112,025,600 B.
- Frozen Gukgam result: 151 targets, 1,634 witnesses + 97 reference persons = **1,731 rows**.
  Actual browser DOM had **2,963 anchors**. These are measured results, not future assertions.

The same-input static build failed the unchanged 256 MiB guard at **5,164,508,878 B**
(**4,925.26 MiB / 4.81 GiB**, 4,633 files). This reproduces the supplied approximate 4.9 GiB
symptom closely; it is a new measured artifact rather than the previously reported artifact.

| Attribution | Bytes | Share |
|---|---:|---:|
| `people/` | 5,018,574,274 | 97.174% |
| `organizations/` | 137,894,659 | 2.670% |
| `gukgam/` | 7,257,782 | 0.141% |
| `_next/` | 656,141 | 0.013% |
| HTML, all routes | 3,291,095,795 | 63.725% |
| RSC `.txt`, all routes | 1,872,715,259 | 36.261% |
| JavaScript | 605,880 | 0.012% |
| Images | 39,258 | 0.001% |

Path and file-category rows are separate views of the same bytes, not additive categories.

| Detail-route distribution (HTML + associated files) | People | Organizations |
|---|---:|---:|
| Count | 1,142 | 387 |
| Mean bytes | 4,390,279 | 353,067 |
| Median bytes | 90,107 | 276,465 |
| p95 bytes | 24,117,082 | 451,816 |
| Maximum bytes | 47,635,441 | 8,517,522 |

The largest Person JSON (`c939a7c0-a369-4b58-b97c-9aa841c6e8ad`) is **7,083,370 B**, with
2,383 Claims and a profile section containing 2,341 entries. Its HTML alone is 30,378,312 B.
This skew and large prerendered payloads explain why Person count alone is insufficient.
The API's Claim and profile representations both carry substantial data; the static renderer
also serializes data into HTML and RSC. Exact byte-identical waste after the existing cleanup
was only **22,510 B in 2 groups**. Further duplicate-file deletion would not solve the limit.
The 30 largest files and all route statistics are in `static-same-input-size.json` below.

Historical 2026-10-06 measurements (504 People, 235.06 MiB static, 1.51 MiB Worker, 5.9 MB gzip)
remain historical and are not acceptance evidence for this dataset. A separate newer UI checkout
at `74c39b0` had a 1,195,297,382 B filtered artifact; its implementation differs and it was not
used for same-code or same-input acceptance.

## Implementation

- Keep the canonical `data.ts -> public-read.ts` boundary and the existing Sites starter.
  Pin official `vinext@1.0.1` and its declared RSC peer `@vitejs/plugin-rsc@0.5.36` in the
  generated stage. Baseline beta.5 Link failure was reproduced in Aside as
  `Uncaught TypeError: e is not a function`; updated Link navigation keeps the document marker.
- Footer reads ACTIVE `generated_at_kst`. Vinext `cacheForRequest` pins one snapshot across
  metadata, layout probes and data reads; a later request sees the next ACTIVE. The root layout
  is request-time; the static builder's existing rewrite still produces a static layout.
  KST date components are unchanged and still use the reader's date.
- Projection schema version 2 extends **existing** `scope_json` semantics with exact expected
  paths, statuses and hashes. No new table, canonical persistence path or PostgreSQL migration.
  Existing schema-1 exports require re-export; the reader rejects them rather than guessing.
- Required listed records, ontology and cited Sources must return 200. Only the optional money
  comparison may preserve 404/422. Authentication, rate-limit, missing required records and 5xx
  fail export. Collect Source IDs from all exported responses, including Gukgam.
- Activation validates schema/manifest/count metadata, scope, path/part/status/hash and gzip bytes before one
  atomic status transition. Keep ACTIVE/PREVIOUS; retire older snapshots only after validation.
  Actual installed Wrangler uses one local D1 `batch()` transaction for the activation file.
  Load, activate and rollback retries are idempotent. Metadata and gzip statements stay under
  D1's 100 KB statement limit; dataset SQL stays outside schema migrations and deploy code.
- Known missing or corrupt exported responses are transport failures. Unknown valid UUIDs are
  404; malformed UUID inputs are 422 `INVALID_INPUT`. Common UUID textual forms normalize to
  canonical keys, without making identity or publication decisions.
- Builder preserves local D1 on rebuild, scans the public boundary and enforces 256 MiB.
  Stage lock is generated then validated by strict `npm ci`. On Windows, npm 11.6.2 reproduced
  optional-WASM/AJV lock failures; scoped npm 11.21.0 succeeds. No global npm/security change,
  root lockfile change, install fallback, new hosted endpoint, secret or R2 resource.

## Measurements and verification

Final clean Worker build: Mac **1,724,822 B** (146 files), headroom **266,710,634 B**, GREEN;
Windows **1,724,875 B**. Both are below 192/220/240 MiB internal budgets and 256 MiB hard limit.
Local preview may add/rewrite generated runtime files. The data-growth experiment measured that
local served tree at 1,730,217 B before and after adding another captured subset to disposable
D1: 26 -> 43 parts, 2 -> 3 snapshots, **0 B artifact growth**, identical SHA-256
`4b37fdef81f07ab4dae5a568bf59627222c8df43e850114a80976bed68498cf6`.
This is a bounded observed loading experiment, not a fabricated scaling benchmark.

Evidence is retained in ignored `dist/release-01-evidence/` in the Windows worktree, with original
Mac files at `/Users/lee/Projects/cvic-release-01-evidence/`. Generated data and screenshots are
not committed. Core tests and builder/exporter code are committed for repeatable verification.

| Check | Result | Command / evidence relative to evidence directory |
|---|---|---|
| Targeted exporter/reader/lifecycle/request-cache tests | PASS, 7/7, no skips on staged hosts | `node --test apps/web/tests/sites-storage.test.mjs`; `make-verify-final.log` |
| Web tests, typecheck, lint, production build | PASS Windows and Mac; 57/57 tests | `npm --prefix apps/web test`, `run typecheck`, `run lint`, `run build` |
| Worker staged typecheck/build and public-boundary scan | PASS Mac and Windows | `node apps/web/scripts/build-sites-worker.mjs`; Windows use `npx --yes npm@11.21.0 exec -- node ...`; `candidate-worker-final.log` |
| Full verification | PASS, 1,072 Python tests / 3 skips; Golden Set true; web 57/57 | Mac `PATH=/Users/lee/Projects/civic-intel-deploy/.venv/bin:$PATH make verify`; `make-verify-final.log` |
| Large same-input static export | FAIL, expected guard | `npm --prefix apps/web run build:sites -- --api http://127.0.0.1:8794 --out <evidence>/static-same-input`; `static-same-input.log`, size JSON |
| Small derived public subset static export | PASS, 2 People / 1 Organization, 1,258,358 B | Same command against local fixture port 8795; `static-small-fixture/snapshot-manifest.json` |
| Actual Wrangler local D1 lifecycle | PASS | `d1 execute DB --local --persist-to .wrangler/lifecycle-qa --file ...`; `d1-lifecycle.log`: STAGED, activation, corrupt-byte rejection, PREVIOUS, rollback and retries |
| Full 1,142-person local D1 activation | PASS | `build-sites-worker.mjs --load-local <projection-verified>`; local ACTIVE `ps-b0a439f3b8327121`, 4,028 paths |
| Same-input 27 rendered routes | PASS, 27/27 | Aside; `rendered-comparison-27-{a,b}.json`: exact main text, ordered hrefs, UUID sets and UNKNOWN counts. Includes largest Organization |
| Largest Person HTTP/data/UUID comparison | PASS | 200 from SSR and Worker, same input SHA; raw HTML UUID sets 7,167 each. Raw streamed text/order differs and is not rendered-DOM evidence |
| Largest Person full browser equality | BLOCKED | `browser-compare-2.log`: Aside connection closed; no visual PASS claimed |
| 1440px reader flow | PASS | `browser-desktop-final.log`: Link, marker, back/forward, search `?q=`, Tab/Enter, card and footer. History wait timed out in the wrapper, but fresh snapshots confirmed both transitions |
| 390px responsive rendering/hash | PASS with viewport limitation | Actual same-origin iframe content viewport 390x844 (top-level resizing unavailable). Opened and inspected screenshots; witness row visible; fresh audit URL and native date-link click visible in `browser-mobile-audit.log` |
| KST/counts/provenance | PASS | 2026-10-08 today, ACTIVE footer 10:29 KST, 151 targets / 1,731 rows / 2,963 anchors; stable UUID/link/UNKNOWN comparisons |
| Leak/error boundaries | PASS in executed scope | Builder/exporter scans; malformed input 422, unknown ID 404, missing/corrupt rows fail, auth/rate-limit/5xx export failures; Worker `/admin/review` 404 |
| Final diff and independent code review | PASS | `git diff --check`; final review found no remaining material code finding |
| Hosted import/binding, Sites preview/save/deploy/public cutover | NOT_RUN; writer BLOCKED | Not authorized and no supported hosted bulk writer verified |

Aside observations include a rejected read of a scratch file outside its allowed roots; that file
operation was stopped, with no permission broadening. Subsequent browser inputs were observed
public URLs supplied directly to the same Aside engine. No alternate browser transport was used.
The earlier test that changed an existing iframe's `src` from witness to audit overscrolled;
fresh direct-entry and actual date-link checks succeeded. That earlier capture is retained, not
silently treated as a passing screenshot. Source-policy and publication semantics were unchanged.

## Official Sites contract and next gate

Read on 2026-10-08: [official Sites documentation](https://learn.chatgpt.com/docs/sites) and
installed Sites 1.0.0-c `references/storage.md`, local-preview guide and Vinext starter.
D1 is supported (10 GB per Site); migrations are schema-only. The current callable connector
exposes bounded D1 overview/row **reads**, not arbitrary SQL imports. Cloudflare account-level
Wrangler/REST support does not establish access to a Sites-managed database. No hosted writer
was invented, no seed was hidden in a migration, and no unauthenticated import endpoint exists.

Next local task: restore supported Aside verification for the largest Person page and complete
its rendered comparison before seeking cutover approval. Native top-level 390px emulation also
remains unavailable; the responsive evidence uses a measured 390px iframe, not device emulation.

After local acceptance, the owner must separately approve a supported hosted writer/security
plan, D1 binding and fresh snapshot load, then owner-private Sites version/preview, exact-version
deploy and any public transition. Refresh data from canonical PostgreSQL rather than shipping
this QA capture. Roll back data with the validated target snapshot's `rollback.sql`; retain a
known-good saved code version. The static path remains in source, but its current full input
cannot be rebuilt under the limit and must not be described as a passing large-data fallback.

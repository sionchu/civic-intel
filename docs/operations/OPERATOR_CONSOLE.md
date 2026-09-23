# Operator Console

Private, read-only management of collected Civic Intel data. This extends the existing
`/admin/review` surface, not a second database, public dashboard, or generic SQL editor.

## Run

Use the repository's Python environment, Node.js, and existing migrated database.
Install/build the Web once after checkout:

```text
npm --prefix apps/web ci
npm --prefix apps/web run build
```

For the existing Civic Intel Railway staging project, an authenticated Railway CLI and
an already-authorized SSH key are required. No database connection string needs to be
copied into a command, file, browser, or chat:

```text
python -m workers.operator_console --railway-project f403bc33-2190-4177-9150-2971e25dd9ee
```

This uses only the existing `staging` / `postgres` service and a private SSH tunnel.
It does not create a service/domain, change Railway configuration, or register new data.
On Windows the launcher uses installed Git OpenSSH when available; the inspected host's
Windows OpenSSH tunnel exited 255 while Git OpenSSH worked without changing key permissions.

Alternatively, supply `DATABASE_URL` through the current process environment and run:

```text
python -m workers.operator_console --label LOCAL
```

Do not combine `DATABASE_URL` with `--railway-project`. A SQLite file must already exist and
be migrated. No startup migration, seeding, collection, or import is performed.
`--dev` uses the Next development server. Default ports are API `8310` and Web `3310`;
`--api-port` and `--web-port` select other unused ports. Both bind only to `127.0.0.1`.

Open `http://127.0.0.1:3310/admin/review` on that computer. A phone or another computer's
localhost is not the operator host. Ctrl+C closes the launcher's owned API, Web and tunnel.
No public hosting or multi-user authentication is included in this local operating mode.

## Views and meanings

- **Collection status:** actual DB counts and per-feeder/scope latest run, latest successful run,
  checkpoint timestamp, observation versions and distinct provider keys. A successful run does
  not imply exhaustive provider coverage. No invented coverage percentage or L3/L4 promotion.
- **DB records and connections:** 12 allowlisted kinds, SQL-side search/filtering, deterministic
  pagination (25 by default, at most 100 via API), and a selected record inspector.
- **Stored reference lineage:** exact foreign keys only; at most three levels, 80 nodes and a
  bounded neighbor window. Limits are visible. Incoming neighbors expand at the selected root
  and Claim-evidence links only; shared Source/Run hubs do not pull in unrelated siblings. Source policy, observations, snapshots, runs,
  Claims, Evidence, subjects and stored review/identity links remain distinct types.
- **Published role relations:** the existing Person/Organization ontology API, not a new gate.
  Current support is `HELD_ROLE` and ALIO `LISTS_EXECUTIVE`; other declared relation vocabulary
  is not silently implemented. Noncanonical role-holder/office nodes are not Persons. At most
  60 eligible edges are displayed, with an explicit truncation notice and text alternative.
- **Reviewed manifest:** reuse the exact checked-in org.go proposal/manifest and canonical
  no-write preflight. `READY_NO_WRITE`, `ALL_PRESENT`, partial or conflict states describe a
  fresh inspection; they are not a historical commit receipt. Organization creation and
  Gukgam Claim publication stay separate. No commit action exists here.
- **Source strategy:** render the existing `FEEDER_SOURCE_COVERAGE.md` matrix as documented
  capability and limitations, separately from measured DB lanes. No heuristic lane matching.

Current/superseded versions, epistemic status, publication status, identity status and source-run
status are not interchangeable. An OPEN-review count excludes resolved review rows; all review
rows can still be inspected in the record browser.

## Read API and access boundary

Private factory: `apps.api.operator:create_operator_app`.
New GET routes (only registered with explicit operator opt-in and a strong server-only token):

```text
/admin/operations
/admin/operations/records?kind=observations&q=...&feeder=...&scope=...&offset=0&limit=25
/admin/operations/records/{kind}/{uuid}
/admin/operations/manifest
```

Record kinds: organizations, people, claims, observations, sources, runs, evidence,
snapshots, reviews, policies, links and checkpoints. Unsupported filters fail explicitly.
The default public API retains disabled admin access. Private API requests require the token,
a loopback Host and no browser Origin. The Next server checks opt-in/loopback before reads
and supplies the token server-to-server; it is not a client prop, public env variable or URL.
Operational responses are no-store. Missing access and database errors never become zero counts.

The private factory uses the existing `SqlAlchemyRepository` with database-enforced read-only
connection defaults: PostgreSQL `default_transaction_read_only=on`, repeatable-read and a
15-second statement timeout; SQLite `query_only=ON`. Canonical repository defaults are unchanged.
All operational selectors use the existing mapped tables/session, not a parallel repository.

DTOs explicitly allow fields. Raw snapshots/fulltext, excerpts, unrestricted normalized JSON,
identity hints, cursor blobs, raw error summaries, credentials and contact fields are omitted.
Source URLs retain only known locator query parameters. Selected-map JSON export contains only
the same bounded DTO; it is not a database dump or full-corpus export.

## References and deliberate non-adoptions

- [Law Orbit](https://github.com/gschamisle/law-orbit): selected-center exploration and preserving
  context while inspecting evidence. No copied assets, branding, law corpus or 3D engine.
- [OpenMetadata](https://github.com/open-metadata/OpenMetadata): catalog, lineage and operational
  status as interaction references. No extra metadata platform/store is installed.
- [Cytoscape.js](https://js.cytoscape.org/): the single operator network renderer, pinned to
  `3.34.3` with bundled TypeScript types. Stable 2D layout, pan/zoom/fit, node inspection and
  an equivalent keyboard-readable relation list; no graph authoring or score-based layout.
- [React Flow](https://reactflow.dev/examples): considered as an editor/workflow alternative,
  not added alongside the read-only network renderer.
- [Postgres MCP](https://github.com/crystaldba/postgres-mcp): considered for schema/health/EXPLAIN
  diagnostics. Not installed; no unrestricted SQL/MCP endpoint is exposed by this console.
- [Korean Law ALIO MCP](https://github.com/scvcoder/korean-law-alio-mcp): potential future
  law/internal-regulation discovery reference, not a UI or canonical identity/rights authority.
  No external MCP data is imported by this slice.

## Verification and remaining boundaries

Regression tests in `tests/test_operator_console.py` cover counts, version/key semantics,
bounded reads, pagination, exact-reference lineage, non-merging names, allowlisted fields,
default-denied access, read-only engine enforcement, manifest drift and private tunnel parsing.
Web source-contract tests supplement, but do not replace, real-browser QA.

No DB editing, deletion, identity approval, automatic binding, Gukgam publication, org.go commit,
production deployment, public domain, scheduler or arbitrary source collection is included.
The pending exact 27-item org.go atomic commit remains an independent operational slice.

## Acceptance recorded on 2026-09-23

- Implemented from canonical base `84426b3434632f5e870d4804f020408d95228f61` in the isolated
  `work/operator-console-v0` worktree. Root checkout and deferred draft PR #75 were not modified.
- Actual private staging reads returned People `299`, Organizations `347`, Claims `5576`,
  ClaimEvidence `5576`, observation versions/unique keys `4170/4170`, Sources/Snapshots `370/370`,
  SourceRuns `21`, checkpoints `10`, IdentityReviewItems `1` with OPEN `0`, and `11` persisted lanes.
  Before/after counters were identical. OPEN=0 is not a claim that computed review queues are empty.
- Fresh canonical org.go inspection returned `READY_NO_WRITE`, exact `27` items, CREATE `27`,
  REUSE `0`. The Organization-only commit and all Gukgam publication remain unexecuted.
- The one-command launcher reached the existing private Railway staging database without creating
  public endpoints or cloud services. Read-only and 15-second SQL statement timeout were verified
  on the PostgreSQL session. All source acquisition paths remained unused.
- Local full regression passed `524` tests with `1` skipped; Golden Set passed. After the final
  invalid-configuration masking regression, all `14` operator tests, Ruff and mypy passed again.
  Web lint/typecheck, `24` UI contract tests, production build and standalone artifact checks passed.
  A clean `npm ci` accepted the minimal lockfile addition; no other package version was changed.
- Real Edge/CDP verification passed `15/15` checks against staging, including list pagination,
  SQL search, graph rendering/selection, keyboard alternative, native fresh reload preserving
  selection, existing public-role projection, 27-row preflight, source catalog, desktop `1440x1100`
  and mobile `390x844` layouts. No browser console/runtime errors or page horizontal overflow occurred.
- The default non-operator Web returned `404`, anonymous private API returned `403`, and an
  external Host on the private Web returned `404`. Operational API calls remained server-to-server.
- One intermediate Windows server transport log recorded a client-disconnect `WinError 10054`;
  the completed browser checks passed and the subsequent final launcher was healthy. This was not
  hidden or treated as evidence of a successful request.
- GitHub Verify is a separate PR gate; local/browser acceptance does not claim remote CI success.

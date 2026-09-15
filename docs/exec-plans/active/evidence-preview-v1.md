# Evidence Preview v1

Status: completed — M0 and M1 verified; M2 through M5 deferred.

Date: 2026-09-14

Baseline: `origin/master` at `1306f00976db6fc7460320885d3863fa236c4ba9`.

## Objective

Turn the existing direct-ID Evidence Directory and bounded ALIO Item 12 MONEY proof into a
failure-safe, honestly rendered, deployment-prepared preview. This plan owns execution order,
acceptance status and evidence. Product direction remains in the North Star, permanent data and
publication rules remain in the architecture documents, and visual rules remain in `DESIGN.md`.

## Scope and boundaries

This execution covers M0 and M1 only. It preserves the canonical
`Claim → ClaimEvidence → Source → SourcePolicy` path, exact observation/snapshot provenance,
Person/Organization subject XOR, current identity gates and the observation-only ALIO worker.

It does not add a feeder, perform unbounded enumeration, or bind ALIO Organizations automatically,
publish raw provider material, create a generic financial model, or implement M2–M5. A separately
approved bounded ALIO observation rehearsal is allowed within M1.4 and remains observation-only.
The seven existing L3 feeders and every blocked/L1/L2 source lane retain their current
source-specific maturity. Fixture, reviewed packet, live observation, published canonical record
and deployed data remain distinct evidence classes.

The root checkout, ignored runtime database, proposer candidate and other worktrees are outside
this worktree and must not be reset, cleaned, moved or rewritten.

## M0 — baseline and governing alignment

- [x] Fetch and compare `origin/master`; isolated worktree started clean at the reviewed SHA.
- [x] Read governing, product, design, workflow, role, batch, source, organization-publication
  and relevant active-plan documents.
- [x] Read the ALIO importer, connector, shared repository, canonical contracts/rows, migrations,
  API, web adapters/pages, tests and CI configuration.
- [x] Confirm the M1.1 risk remains in code: the CLI writes two Claims through two independent
  repository transactions and rejects a rerun when either provider key already exists.
- [x] Align only documented evidence classes, neutral UNKNOWN presentation, verification layers
  and migration/data-recovery requirements.

## M1.1 — atomic and idempotent reviewed ALIO pair

Status: completed locally on 2026-09-14.

### Required implementation

1. Reproduce the split-transaction failure with a disposable database and injected failure on
   the second Claim.
2. Add one shared-repository transaction for the reviewed two-Claim operation. Revalidate the
   Organization, policy, source/snapshot/observation chain, immutable versions and publication
   gate inside that transaction.
3. Make exact reruns no-op and return the stored Claim IDs. The logical identity must include the
   target Organization, source contract/scope/provider key, normalized version, predicate,
   fiscal year, amount/unit and exact Evidence provenance.
4. Recover an exact legacy one-Claim partial state by inserting only the matching missing Claim.
   Reject mismatched partial state without modification.
5. Use a database-backed uniqueness/concurrency guard rather than relying only on a pre-insert
   SELECT. Keep the single-Claim importer working through the same validation/write seam.

### Acceptance

- First commit persists exactly two Claims and two Evidence rows.
- Injected second-item failure rolls back both new items and preserves all prior rows.
- Rerun after failure succeeds; exact completed rerun is a no-op with stable stored IDs.
- Exact legacy partial recovery succeeds; a conflicting partial remains unchanged.
- Wrong subject, denied policy, mismatched source/snapshot and ambiguous observation versions
  make no change.
- Concurrent equivalent calls converge on one logical pair without duplicates.
- Dry-run, Person imports, the existing single-Claim path and Golden regressions remain valid.

Implementation and evidence:

- The pre-change regression injected failure into the second CLI write and observed one residual
  Claim, confirming the split-transaction risk.
- ALIO Item 12 Claim/Evidence IDs are now deterministic over canonical Organization, source
  contract, provider record key, immutable observation hash and exact Evidence provenance.
- `SqlAlchemyRepository.import_organization_claim_pair()` validates and writes both Claims in one
  transaction, reuses the single-Claim validation/write seam, recovers an exact legacy partial,
  rejects divergent semantics and retries one deterministic primary-key race.
- Targeted Item 12 tests: 29 passed. The full local suite: 325 passed, 4 warnings. Ruff, mypy (56
  source files), Golden quality, web lint/typecheck, seven UI tests and production build passed.
- No migration or dependency was added. The ignored runtime database was not opened or changed.

## M1.2 — honest public read states and Source boundary

Status: completed locally on 2026-09-14.

Replace blanket web fallbacks with a small discriminated read result. API responses must expose
safe stable error codes and request IDs for not found, insufficient eligible inputs, source/version
conflict, access denial and service failure without leaking exceptions, SQL, credentials or
private-source existence.

An anonymous Source read is eligible only when the Source is reachable from current published
Claims on a current publicly eligible Person or Organization. Published UNKNOWN and all evidence
stances remain eligible when their Claim passes the normal gate. Return an explicit public DTO
allowlist; do not expose the full Source or SourcePolicy model.

Acceptance requires deterministic API/UI regressions for success-empty, public 404, insufficient
comparison inputs, conflict, access denial and upstream/service failure. The UI must never turn a
transport failure into UNKNOWN or empty data and must never fall back to raw observations.

Implementation and evidence:

- FastAPI now returns safe error envelopes with stable codes and per-request IDs. Missing public
  records, invalid input, insufficient eligible annual Claims, source-version conflict and
  unexpected service failure are distinct. The disabled review route retains an indistinguishable
  public 404; the web adapter also renders an explicit access-denied result when a host boundary
  returns 403.
- `GET /sources/{id}` now resolves only Sources reachable through a current publishable
  Claim/Evidence path on a public eligible subject. Its DTO allowlists source identity, locator,
  publisher/date, source class, license/terms review date and policy summary; internal policy
  booleans, notes and operational metadata are absent.
- Server Components prefer `CIVIC_API_URL`; `NEXT_PUBLIC_API_URL` remains a compatibility fallback.
  Network/5xx failures are not rendered as empty data or `UNKNOWN`.
- Targeted API/ALIO tests: 47 passed. Full suite: 330 passed, 4 warnings. Ruff, mypy (56 files),
  Golden quality, web lint/typecheck, eight UI contract tests and production build passed.
- No migration or dependency was added. No private Source, raw observation or credential entered a
  public response.

## M1.3 — browser and standalone production artifact

Status: completed locally on 2026-09-14.

Run the production Next standalone artifact against FastAPI and a disposable migrated database.

Implementation and evidence:

- The previous `next build` output omitted `.next/static` from `.next/standalone`, so the server
  executable was present while its CSS and client chunks were not self-contained. The build now
  copies generated static assets (and `public` when present) into the standalone root and a separate
  contract check fails when the server, build ID or non-empty static tree is missing.
- A fresh ignored SQLite database was migrated to Alembic head and seeded from the Golden fixture;
  no existing runtime database was used or changed. FastAPI and the production standalone server
  were run as separate processes with the server-only `CIVIC_API_URL` contract.
- In a real browser, the ten-person roster rendered, name filtering reduced it to the selected
  resolved identity, and the person detail exposed Claim, Evidence and two reachable Source cards.
  A missing Person rendered the dedicated public not-found page. With FastAPI stopped, the roster
  rendered `SERVICE_UNAVAILABLE` instead of empty data or `UNKNOWN`. A disposable Organization with
  no eligible annual Claims rendered `INSUFFICIENT_ELIGIBLE_INPUTS` with its request ID. The ALIO
  known-positive fixture then rendered the two annual Claims, two Evidence inputs, one Source and
  the derived MONEY delta. Adding a second immutable 2024 observation version removed that derived
  card and rendered `SOURCE_VERSION_CONFLICT` without choosing a version.
- Desktop and 390 px viewport checks found no horizontal overflow, blank screen, Next error overlay,
  console warning or console error. The first keyboard focus was the `본문으로 건너뛰기` link.
  UI tests increased from eight to nine and the rebuilt standalone artifact passed its contract
  check. No browser dependency, migration or production data was added.
Use one existing or narrowly justified browser test tool. Verify people search → profile → evidence
→ origin link, organization direct-ID → MONEY → both Claim/Evidence inputs, missing UUID, API-down
and conflict states. Verify CSS/JS assets, hydration and console output, desktop and 390 px layouts,
keyboard navigation, enlarged text and long Korean content. Static string tests remain architecture
guards, not browser evidence.

The server-only API origin and any browser-public origin must be separated without exposing private
endpoints or secrets through `NEXT_PUBLIC_*`. Supported Node, CI and deployment artifact commands
must agree.

## M1.4 — PostgreSQL, load and recovery proof

Status: completed with GitHub Actions and provider-independent staging logical backup/restore proof
on 2026-09-15.

Keep one SQLAlchemy/Alembic repository and retain SQLite tests. Add only the required PostgreSQL
driver/configuration. Against a disposable PostgreSQL instance, verify clean upgrade to head,
upgrade/downgrade/upgrade where safe, Golden or reviewed fixture load, the atomic ALIO pair, API
reads and the MONEY projection. Add CI coverage where the project runner can provide the service.

Provide a repeatable operator data-load command that uses existing import/publication gates. Prove
backup and restore into a second disposable database, then compare schema head and canonical row
counts plus a representative provenance-backed read. Never test downgrade or restore against an
operational database.

Implementation and evidence:

- Added the `psycopg` SQLAlchemy driver and a PostgreSQL 16 CI service while retaining all SQLite
  tests. The integration test performs a clean upgrade, downgrade to `0004`, upgrade to current
  head, Golden seed, bounded ALIO observation load, atomic reviewed two-Claim import and public
  roster/MONEY reads through the shared repository and API.
- PostgreSQL exposed real ordering and migration portability defects hidden by SQLite. Canonical
  parent/dependent writes now flush in foreign-key order; migration `0005` uses an in-place
  PostgreSQL subject-XOR change and discovers the actual foreign-key name for downgrade.
- `SourcePolicy.rate_limit` is now `Text` through reversible migration `0006`; its pre-downgrade
  guard refuses truncation when any stored value exceeds 100 characters.
- CI run `34838519611` at `cd65b7eee82d887150009ff20700ddb6ca98b9fc` passed canonical
  verification, the SQLite migration round trip, PostgreSQL migration/load/API contracts and a
  custom-format `pg_dump` restored into a second database. The restored verifier confirmed head
  `0006`, ten public People, two published Organization Claims and a representative public read.
- Railway-managed backup/PITR is unavailable on the current staging plan: the owner-observed
  Dashboard states that backups and point-in-time recovery are available only for Pro customers.
  No Pro upgrade, billing/plan change or new Railway resource was made. This provider limitation
  is not an M1.4 blocker because the approved backup requirement is satisfied by the
  provider-independent logical proof below.
- On 2026-09-15, a read-only `railway connect postgres --tunnel-only` session was used to inspect
  staging and create the dump. A temporary SSH key was registered for that session and removed
  afterward; Railway then reported no registered SSH keys. The staging baseline was schema head
  `0006` on PostgreSQL `18.6`, with 26 public tables. The canonical counts for People,
  Organizations, Sources, SourceSnapshots, SourceRuns, SourceCheckpoints, FeederObservations,
  Claims, ClaimEvidence, PersonObservationLinks and IdentityReviewItems were all `0`;
  subject-XOR and ClaimEvidence provenance mismatch checks were `0`, and published/MONEY counts
  were `0`.
- The logical receipt captured application revision
  `b8c1f7666c8dcd2293da90a20cda1e41944a527c`, repository HEAD
  `33c664b3a93addb7d02c89c6ef1807a62ac6041b` at capture, schema head `0006`, and PostgreSQL
  `18.6` at `2026-09-15T00:17:52.2664981Z`. The private dump used custom format and `--no-owner`,
  was `57,261` bytes, and had SHA-256
  `47CE121735FB27F9DCBCA9B297A2041FE25FFAA3F3CEAB2CEBE8050F5C834CAF`. It remains outside the
  repository in a private temporary backup path and is not committed.
- `pg_restore --no-owner --exit-on-error` restored the dump into a loopback-only disposable
  PostgreSQL `18.6` database in `0.321` seconds. The restored schema head, 26-table set,
  canonical counts, subject-XOR/provenance checks and pilot MONEY counts matched the read-only
  staging baseline. The restored database API smoke returned `/ready 200`, `/health 200`,
  `/people 200` with zero rows, and `404` for an unknown Organization; the restore gate passed.
  Both source and restored staging databases were empty, so no live staging Organization/MONEY
  pilot row existed to compare. The non-empty pilot result remains separately evidenced by CI
  and fixtures, not attributed to this staging dump.
- The staging source was never dropped, reset, migrated, or written during the rehearsal: only
  read-only inspection and `pg_dump` were performed. The temporary PostgreSQL client binaries,
  disposable cluster, API process and transient key material were cleaned up after verification.
- GitHub Actions `Verify` run `34913882587` for the pushed logical-proof commit
  `6d979cdbd925f94328d578c3f941cb295d815201` passed in `2m25s`, including canonical verification,
  Alembic round trip, PostgreSQL migration/load/API contracts, PostgreSQL backup/restore and
  deployment artifact checks.

### Subsequent approved staging observation rehearsal

- The first approved live attempt failed closed because unrelated directory rows advertised
  `.pdf`/`.hwp` attachments while the selected known-positive rows were spreadsheet-backed. It
  created only a failed `SourceRun` (`00a234ee-dde6-407f-a4a9-2deed6e27875`); read-only inspection
  confirmed zero Sources, SourceSnapshots, Checkpoints and FeederObservations, so no partial
  recovery was needed.
- The minimal fix `d06b0cc6f7c8d0313a1973a1dbafb02b0f83d20a` preserves recognized document filenames
  as metadata for unselected rows, rejects unsupported formats only inside the selected allowlist,
  and continues to reject unknown extensions. Targeted ALIO tests (34), full pytest (exit 0 with
  one PostgreSQL-only skip), Ruff, mypy and Golden quality all passed locally. GitHub Actions
  `Verify` run `34916320972` for this commit completed successfully, including canonical,
  migration, PostgreSQL load/API, backup/restore and deployment-artifact checks.
- Through a private Railway tunnel, the bounded worker completed `C0019`, `C0129`, `C0908` with
  run `40ba451d-4d57-4f18-bbdb-122c516ebfde`, `SUCCESS`, three institutions and 15 observations.
  Staging now contains four Sources, four metadata-only SourceSnapshots, two SourceRuns (one
  earlier failed and one successful), one checkpoint at cursor `3`, and zero People,
  Organizations, Claims and ClaimEvidence. The successful run counters are
  `(records_seen, observations_created, observations_unchanged) = (15, 15, 0)`.
- Read-only QA confirmed schema head `0006`, 15 distinct provider keys, three report snapshots,
  zero fulltext snapshots, empty identity hints, zero orphan observations, zero unsafe source URLs,
  subject-XOR `0` and ClaimEvidence provenance mismatch `0`. A local API read smoke using the
  staging connection returned `/health 200`, `/ready 200`, `/people 200` with zero rows and
  unknown Organization `404`. Claim import was not run because an existing canonical Organization
  binding is required; no provider row was materialized as an Organization.
- The temporary Railway key was removed and local ephemeral key files deleted after verification.
  No provider plan/resource change, reset/drop/schema migration, public API/database exposure or
  new feeder was introduced. This is `LIVE_OBSERVATION` evidence, not published canonical data.

### Subsequent approved staging reviewed Claim/MONEY smoke

The zero-Organization state above was the pre-binding observation checkpoint. In the separately
approved reviewed-binding slice, the existing canonical Organization
`b6c4df5d-2d9b-4c26-aedb-2c5a0f079b11` (`정보통신기획평가원`, provider code `C0908`) was bound
explicitly. The provider observation was not used to create an Organization.

The existing reviewed importer was run first as a dry-run and then with `--commit`, both against
the same two deterministic ALIO observation keys `2026041303154117:2024` and
`2026041303154117:2025`. It produced the same Claim IDs
`6e8b4287-8a00-5820-ad5f-1e47ac868844` and `cc7ef8ab-1f40-5e08-b4be-302e3a0e04db`, and the same
ClaimEvidence IDs `68c61f94-65fc-5ca5-a867-3f93914f3865` and
`729cf75b-4c26-5d30-bf39-ce9ba496a6c7`. Read-only staging inspection then found one reviewed
Organization, two Claims, two ClaimEvidence rows, the existing 15 ALIO observations, Alembic head
`0006`, and no provenance or subject-XOR violations.

A local FastAPI read smoke using the private staging connection returned `/organizations/{id}`
`200`, `/organizations/{id}/claims` `200` and the 2024→2025 MONEY projection `200` with
`availability=AVAILABLE`, absolute delta `-2,162,000 KRW`, percent change `-14.39%`, and the
exact Claim/Evidence/SourceSnapshot/FeederObservation chain. This closes the reviewed ALIO
Organization binding → two fiscal-year Claim → MONEY staging smoke prerequisite while retaining
the ALIO maturity ceiling at `L2 SINGLE_PULL`; it does not promote ALIO to L3 or assert production
coverage.

The logical backup/restore receipt was captured before this approved staging write. No provider
plan/resource change, reset, drop, schema migration, public API/database exposure or new feeder was
introduced.

## M1.5 — deployment preparation and approval boundary

Status: completed in GitHub Actions on 2026-09-14.

Document and verify the selected artifact contract for the standalone web, FastAPI API, migrated
PostgreSQL database, environment variables, health/readiness checks, migration order, data load,
rollback and backup/restore. Prepare hosting manifests/runbooks only when they do not create public
resources or cost.

Creating public infrastructure, changing an operational database, purchasing a service, widening
access, transferring ownership or exposing a secret requires separate approval. Until then the
deployment state is `PREPARED`, never `DEPLOYED`.

Implementation and evidence:

- Added separate non-root FastAPI and Next standalone images, a loopback-bound PostgreSQL/API/web
  rehearsal manifest and a context denylist for secrets, ignored databases and build outputs.
- Added `/ready`, which verifies Alembic head and database connectivity while returning the same
  safe `SERVICE_UNAVAILABLE` envelope used by public reads when readiness fails.
- Added `docs/operations/EVIDENCE_PREVIEW_DEPLOYMENT.md` as the single runbook for configuration,
  migration order, dry-run/committed loading, readiness, backup/restore and restore-to-new-database
  rollback. OpenAI Sites was evaluated but not selected because it does not directly supply this
  repository's separate Next server, FastAPI process and PostgreSQL runtime contract.
- Targeted deployment/API checks passed with 21 tests. Full local verification passed with 335
  tests and one PostgreSQL-only skip, Ruff, mypy (57 files), Golden quality, web lint/typecheck,
  nine UI tests, production build and standalone artifact check. Docker is unavailable locally.
- GitHub Actions run `34838879854` at `0e90bae9269e980d38e45f0041fdcdc76852e17c`
  passed the full canonical suite, SQLite and PostgreSQL migration checks, PostgreSQL load and
  backup/restore, both Docker image builds and Compose contract validation.

## Deferred product specification — M2 to M5

These are preserved as future release candidates, not implementation permission:

- M2: searchable Person/Organization discovery, evidence drawer, availability periods and one
  rights-reviewed photo pilot. Data binding must still originate in eligible canonical reads.
- M3: authenticated read-only operations first, then audited narrow commands for binding,
  publication and correction with actor, reason, before/after state and rollback semantics.
- M4: one evidence-qualified current issue with explicit source scope and methodology.
- M5: separately gated reusable API/read-only MCP, explicit-interest discovery and moderated
  evidence-aware community. None may merge identity or publish FACT through a side door.

No large UI redesign, photo ingestion, admin write path, issue feed, MCP or community schema is
part of this execution.

## Verification and delivery loop

Each M1 stage follows regression → smallest canonical change → targeted checks → full project
verification → diff/Clean-v0 audit → coherent commit/push → actual CI head/result check. A local
pass, CI pass, published record and deployed service are reported separately.

Required final evidence:

- start/final SHA, branch, pushed remote equality and actual CI `head_sha`/result;
- M1.1 transaction, idempotence, recovery and concurrency outcomes;
- M1.2 API/UI state and public Source eligibility outcomes;
- M1.3 real-browser and standalone asset/runtime outcomes;
- M1.4 PostgreSQL migration/load/backup/restore outcomes;
- schema/dependency changes and their necessity;
- fixture/reviewed/live/published/deployed classification;
- deployment preparation state, approvals not exercised and remaining blockers.

## Stop condition

Stop after M1 implementation, verification and deployment-preparation reporting. Do not begin M2,
M3, M4, M5, a new feeder, a repeated source gate or an external institution inquiry. Report exactly
one next best action.

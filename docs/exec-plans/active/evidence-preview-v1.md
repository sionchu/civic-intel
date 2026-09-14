# Evidence Preview v1

Status: active — M0 through M1.4 complete; M1.5 implemented locally, final CI pending.

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

It does not add a feeder, promote maturity, enumerate or bind ALIO Organizations automatically,
publish raw provider material, create a generic financial model, or implement M2–M5. The seven
existing L3 feeders and every blocked/L1/L2 source lane retain their current source-specific
maturity. Fixture, reviewed packet, live observation, published canonical record and deployed
data remain distinct evidence classes.

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

Status: completed in GitHub Actions on 2026-09-14.

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
- PostgreSQL tooling was unavailable on the Windows host, so this stage's database and
  backup/restore execution evidence is CI evidence, not a local PostgreSQL claim.

## M1.5 — deployment preparation and approval boundary

Status: implemented and verified locally on 2026-09-14; final GitHub Actions artifact build is
pending.

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
  nine UI tests, production build and standalone artifact check. Docker is unavailable locally;
  CI builds both images and validates the Compose contract before this stage is final.

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

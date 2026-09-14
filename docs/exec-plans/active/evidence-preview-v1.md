# Evidence Preview v1

Status: active — M0 and M1.1 complete; M1.2 is next.

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

## M1.3 — browser and standalone production artifact

Run the production Next standalone artifact against FastAPI and a disposable migrated database.
Use one existing or narrowly justified browser test tool. Verify people search → profile → evidence
→ origin link, organization direct-ID → MONEY → both Claim/Evidence inputs, missing UUID, API-down
and conflict states. Verify CSS/JS assets, hydration and console output, desktop and 390 px layouts,
keyboard navigation, enlarged text and long Korean content. Static string tests remain architecture
guards, not browser evidence.

The server-only API origin and any browser-public origin must be separated without exposing private
endpoints or secrets through `NEXT_PUBLIC_*`. Supported Node, CI and deployment artifact commands
must agree.

## M1.4 — PostgreSQL, load and recovery proof

Keep one SQLAlchemy/Alembic repository and retain SQLite tests. Add only the required PostgreSQL
driver/configuration. Against a disposable PostgreSQL instance, verify clean upgrade to head,
upgrade/downgrade/upgrade where safe, Golden or reviewed fixture load, the atomic ALIO pair, API
reads and the MONEY projection. Add CI coverage where the project runner can provide the service.

Provide a repeatable operator data-load command that uses existing import/publication gates. Prove
backup and restore into a second disposable database, then compare schema head and canonical row
counts plus a representative provenance-backed read. Never test downgrade or restore against an
operational database.

## M1.5 — deployment preparation and approval boundary

Document and verify the selected artifact contract for the standalone web, FastAPI API, migrated
PostgreSQL database, environment variables, health/readiness checks, migration order, data load,
rollback and backup/restore. Prepare hosting manifests/runbooks only when they do not create public
resources or cost.

Creating public infrastructure, changing an operational database, purchasing a service, widening
access, transferring ownership or exposing a secret requires separate approval. Until then the
deployment state is `PREPARED`, never `DEPLOYED`.

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

# Civic Intel private admin console

The existing `/admin/review` workspace now supports source-record review and confirmed management,
not only DB inspection. Public routes remain read-only. See
[Admin operation contracts](../architecture/ADMIN_OPERATIONS.md) for transaction, identity and audit semantics.

## Start on the operator computer

Use the repository Python environment and existing Node.js installation. After checkout:

```text
npm --prefix apps/web ci
npm --prefix apps/web run build
```

Read/preview mode on the existing Railway staging database:

```text
python -m workers.operator_console --railway-project f403bc33-2190-4177-9150-2971e25dd9ee
```

Confirmed admin-write mode, only after the reviewed 0007 schema is deployed:

```text
python -m workers.operator_console --railway-project f403bc33-2190-4177-9150-2971e25dd9ee --enable-writes
```

`--actor` defaults to the local OS user. `--api-port` / `--web-port` choose unused ports; defaults
are 8310 / 3310. For an existing local/restored database, supply DATABASE_URL through the process
environment and use `--label LOCAL`, `RESTORED` or `TEST`. Do not combine DATABASE_URL with the
Railway option. No URL/password is printed or persisted; the private SSH tunnel is owned by the
launcher. All listeners bind to 127.0.0.1. Ctrl+C closes its own Web/API/tunnel processes.

Open `http://127.0.0.1:3310/admin/review` on that computer, not another device's localhost.
Read-only sessions cannot commit even if a client fabricates a confirm request. Write mode fails
closed before startup when 0007 is absent. The screen explicitly distinguishes READ/PREVIEW from
ADMIN WRITE and displays the actor. The console does not run migrations itself.

## Main workflows

**인물 검토·등록** is the default work queue. Named ALIO source rows appear whether or not a review
row was previously persisted. Filter 미검토, 보류, 대상 제외, 인물 연결 완료 or name/alias candidates.
Read institution, role, source-period and evidence context. Select individual rows or the visible
page (at most 25), enter a reason, preview and explicitly confirm. New Person registration creates
a role draft; the receipt offers a follow-on Claim review/publish action. Same-name/alias candidates
block naive new creation. Source record count and distinct name strings never claim unique people.

**DB 목록·연결** preserves the 12 existing bounded record browsers and exact-reference graph. Selected
Person records have name correction, explicit reviewed merge and soft deactivation. Selected Claims
have review, approval/publication, withdrawal and correction-draft controls. For link/merge choose a
current Person, search existing Evidence by name/content, inspect its source and attest the official
cross-role continuity. Selecting an Evidence ID alone does not make the identity judgment true.

**변경 이력** shows actual committed receipts with actor/time/reason/request ID and before/after.
No optimistic success is shown. If a response is lost, check the same request ID before creating a
new request. Retrying the identical operation is idempotent. A changed/expired preview must be rebuilt.

**수집 현황**, **검토 manifest**, **출처 계획·제약** retain the measured DB lane counts, exact org.go
no-write preflight and clearly separate documented source capabilities. The old 27-item org.go
Organization commit is still independent; no new admin command executes that import automatically.

Deletion means public removal/deactivation while preserving source/audit records; there
is no arbitrary hard-delete button. Claim correction creates a new attributable CLAIM draft, not a
rewritten official source row or automatically inferred typed relationship. A review/merge blocked
by source versions, identity conflict or unsupported domain dependencies must be investigated, not
forced by editing SQL.

## API

Existing read endpoints stay under `/admin/operations`. New allowlisted endpoints:

```text
GET  /admin/operations/capabilities
GET  /admin/operations/people-review?q=...&state=UNREVIEWED&offset=0&limit=25
GET  /admin/operations/evidence-options?q=...
GET  /admin/operations/history?offset=0&limit=25
POST /admin/operations/preview
POST /admin/operations/commit
```

Browser POSTs go to `/admin/review/actions`; that handler checks exact same-origin, explicit intent,
JSON type and bounded input, then supplies the private API token server-to-server. A signed preview
is command-specific and is not the API credential. No mutation route accepts SQL, a table name or
arbitrary field updates. See `packages/domain/admin.py` for the actual command schema.

PostgreSQL read-only mode uses repeatable-read with 15-second statement timeout; admin sessions use
READ COMMITTED and the explicit command locking protocol. Both modes pre-ping stale pooled sockets.
Readiness is checked every 30 seconds. After two failures the launcher can replace its own private
backend while retaining Web/token, within a finite two-retry budget. Connection failure remains an
error, never zero records. Restart after connectivity returns if the finite budget is exhausted.

## Structural research and deliberate choices

- [OpenRefine reconciliation](https://openrefine.org/docs/manual/reconciling): iterative faceted
  judgments, candidate review and original-value preservation. We do not inherit same-string mass
  matching as person identity authority.
- [React-admin mutations](https://marmelab.com/react-admin/Actions.html): wait for server acceptance
  before announcing success. Native Next components are retained; no second admin framework added.
- [OCCRP Aleph](https://docs.aleph.occrp.org/): entity/evidence investigation and contextual links.
- [Law Orbit](https://github.com/gschamisle/law-orbit): selected-center graph and source inspection.
  Existing Cytoscape 3.34.3 remains the sole renderer; no decorative 3D engine.
- [Splink](https://moj-analytical-services.github.io/splink/): probabilistic record-linkage candidate
  research, not an identity approval engine or dependency added here.
- [BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3): multilingual retrieval candidate. The official HF
  repository was inspected; no model download/inference/embedding store was needed for this workflow.
- [Postgres MCP](https://github.com/crystaldba/postgres-mcp) and
  [Korean Law ALIO MCP](https://github.com/scvcoder/korean-law-alio-mcp): no unrestricted SQL access or
  external legal corpus was added. Future tool access must use the same bounded approval contract.

## Verification and rollout evidence

Tests cover source-derived backlog, no-write previews, signed expiry/tampering, stale state,
idempotency, batch rollback, explicit source-context registration/link/merge, draft/publication/
withdrawal/correction, alias conflicts, dependency guards, database-enforced append-only audit,
foreign keys and populated migration round trips. Browser testing exercises real mutations against
a separate PostgreSQL fixture, not just source-string assertions or mock success messages.

The 2026-09-23 pre-rollout staging backup was restored into a local PostgreSQL 18.6 database.
0006 -> 0007 -> 0006 -> 0007 completed only there; domain fingerprints matched before/after:
People 299, Organizations 347, Claims/Evidence 5576/5576, observations 4170, snapshots 370.
The actual named ALIO workload is 3624 unreviewed records and 3076 distinct name strings, not
3076 verified people. Original staging rows were unchanged during this proof.

Backup SHA-256: `2e6edd95cc990a928c311e3220ceb81826f12ea197a1bf221c991f32dcb54624`.
Keep the logical backup outside Git on the operator host. No real-person decisions were executed
as migration tests. CI and actual staging activation must be reported separately from local tests.


## Implementation acceptance before rollout (2026-09-23)

- The full local suite passed 552 tests with 1 skipped and Golden passed; after the final
  institution/role search regression, all 22 focused admin tests, Ruff and mypy passed.
- Fresh disposable PostgreSQL tests independently passed reviewed Person linking, reviewed merge
  and idempotent retry. These used synthetic source records, not live Person decisions.
- Real Edge browser mutation QA passed 17 checks: batch preview/cancel/hold/reopen, registration
  into a draft, publication and exact Person–Organization graph, correction draft/replacement,
  withdrawal, alias-preserving rename, soft deactivation, durable history, intent/CSRF rejection,
  keyboard and desktop/mobile rendering. The final rebuilt production artifact passed the same
  17 checks again against a newly initialized PostgreSQL fixture.
- The populated staging backup/restore/migration proof above is complete. Master is configured to
  auto-deploy API with `python -m alembic upgrade head`; merge therefore requires successful CI and
  this recorded backup proof. Staging schema/application activation is checked separately.
- No live source collection, original org.go27 commit or real Person decision was performed by
  implementation tests. Existing source/domain fingerprints remain the acceptance baseline.

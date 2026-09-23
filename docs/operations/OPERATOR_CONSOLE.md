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


## Installed staging admin — 2026-09-23

The operator PC shortcuts `Civic Intel - Start.cmd` / `Civic Intel - Open.url` use ports3315/8315:
`http://127.0.0.1:3315/admin/review`. Start uses the canonical admin worktree and `--enable-writes`;
this is an explicitly enabled local-OS admin session, not a public administrative website.

PR141 merge `e141dc363a2c9357fb43519dde70f168a08c946d` passed GitHub Verify35852398793
(553 passed /1 skipped). A merge did not start an API deployment automatically. An exact tracked
source archive was explicitly uploaded to the existing staging API; deployment
`62438070-020c-4af2-bb7f-666065421dde` succeeded, with pre-deploy0006->0007 and readiness200.

Actual staging browser13/13 checks passed without a real command commit. Post-activation DB
inspection found schema0007, zero admin-operation receipts and unchanged six-table domain
fingerprints. Canonical People remain299; ALIO workload is3624 unreviewed named records /3076
name strings. Registration, linking and approval are now usable workflows, not already completed
collection work. Closure is in [the completed admin plan](../exec-plans/completed/admin-review-workflow.md).

One old standalone audit tunnel expired during verification; it was not the active admin session.
The successful final inspection used a fresh native read-only audit process. The first browser
harness run attempted to serialize a DOM node; the harness was corrected to return a Boolean,
then all13 real checks passed. No runtime behavior patch or additional data mutation was needed.


Access checks on the activated host: anonymous private API403 and untrusted-Host private Web404.
The older deployed public Web still returns200 for its legacy read-only review shell, but renders
PUBLIC_RECORD_NOT_FOUND with no new admin controls or operational rows; POST to its admin actions
path returns404. HTTP200 from that old shell is not an admin deployment or data-access success.
This activation deliberately did not redeploy the separate public Web service.


## Project subagent guidance and cheatsheet proposal (2026-09-24)

Repository-wide delegation is defined in [ROLE_MODEL.md](../roles/ROLE_MODEL.md), with thin
project `.codex/agents/` adapters and a three-child limit. User-wide configuration and running
admin processes are unchanged. The two existing skill documents now have required YAML metadata;
their procedures were not rewritten. These are instruction/configuration changes, not a new
agent runner, task-dispatch API, source run or DB mutation.

A restricted native smoke parsed the project config but could not load/execute the requested
named roles: its permitted-file shell read was rejected and it reported no named-role selector.
Zero children executed. This does not establish that all Codex clients lack support; it means
this invocation did not verify named-role execution. Do not label custom-agent runtime or MCP/DB
isolation as validated. Use only explicitly authorized isolated work until effective access is tested.

The [Gajae-Code cheatsheet](https://github.com/Yeachan-Heo/gajae-code/tree/main/docs/cheatsheet)
was inspected as a visual interaction reference: clarify -> plan/review -> act -> evidence,
role cards, workflow/operation categories, and troubleshooting. GJC is a different agent harness;
its commands are not Civic Intel commands. No GJC binary, provider login, bot or MCP was installed.

## Work playbook — implementation 2026-09-24

The existing admin now includes 업무 플레이북, with contextual entry points from selected ALIO
records, DB record details, source-run details and committed operation history. Six recipes map
current work to source_worker, record_curator, product_builder and independent review roles.
Existing admin controls, source status and provenance graph remain intact.

1. Select 1–25 records in 인물 검토·등록 and expand 업무 플레이북, or open a record/run/history item.
2. Choose the task, inspect its role/input/output boundary and add a bounded note without secrets.
3. Prepare a DRAFT. Server validates exact IDs and allowlisted-view versions; a missing/changed
   item rejects the entire selection. Code revision and current canonical instruction hashes are
   re-read for each request, not cached forever at process startup.
4. Copy or download Markdown/reference JSON. Request ID is not an execution ID. Changing selection,
   role recipe or note invalidates the prepared export. Nothing is saved as an agent job.

Identity-link requests require one observation, one candidate Person and selected Evidence;
lookup responses are bound to their kind/context to prevent stale asynchronous selection.
Collection-error requests require exactly one FAILED/PARTIAL source run. A product-fix request
can describe code work without selecting live rows; proposed paths are not granted permissions.

The export is deliberately reference-only: IDs, allowed foreign-key/hash anchors and scope names;
no provider body, names, excerpts, URLs, contacts, raw errors or existing operation reasons are
copied into it automatically. User-entered notes remain explicitly untrusted context, not shell
instructions or permission. This is not an automatic scrubber for secrets entered manually.
Source content must be separately checked against SourcePolicy before any later AI access.
A reference version identifies the allowed selected view, not the entire graph/database snapshot.

Endpoints on the explicitly opted-in private API only:

```text
GET  /admin/operations/playbook
POST /admin/operations/playbook/draft
```

The browser uses the existing same-origin/intent-checked `/admin/review/actions` with the fixed
`work_order_draft` operation; no arbitrary shell/path/role/privilege input or dispatch route exists.
These reads also work in read-only DB mode. No migration, new task DB or secondary source store.

### Execution integration remains blocked

A fresh synthetic native Codex probe reported `collaboration.spawn_agent` but no selector that
verified loading the named record_curator configuration; zero children executed and effective
child tool/credential restrictions were not established. Do not replace this with a task-name
label or silently enable a generic broad-privilege runner. The UI accurately shows 실행 미연동.
A future adapter must prove role loading, isolated inputs/tools, job ID/state/timeout/cancellation
and evidence handoff before a dispatch control is enabled. The request-preparation slice is usable;
it is not the completion of the agent execution/QA/approval/commit lifecycle.


Instruction-slice verification: six TOML files parsed; required metadata for both existing skills
was added without changing their bodies; changed-document relative links and `git diff --check`
passed. A separate restricted Codex session reviewed the exact policy/config texts and returned
PASS/no issues, with no tool calls. This is independent text review, not named-role runtime QA.
The strict-config invocation after metadata repair exited successfully without loader errors.
The earlier native named-role smoke remains BLOCKED/zero children. No application test, browser
QA, runtime deployment, live source collection or administrative record change is claimed here.


## Installed playbook preparation — 2026-09-24

Implementation PR144 / commit98dd4ca069c784c525996ad9ce707b86b483ccf9 passed Verify35889018114
(565 tests/1 skipped). The operator's existing3315/8315 private admin now runs this merged code
from `C:\Users\getch\civic-intel-playbook`; Desktop Start was updated, Open still targets3315.
Existing ADMIN WRITE controls are retained. This was a local operator-runtime update, not a cloud
API/Web deployment, migration or data-import run.

Open `http://127.0.0.1:3315/admin/review?tab=playbook` for all six tasks. For data work use the existing
record list, select exact records and expand 업무 플레이북; prepare/download the bounded reference
DRAFT. The executing-agent state remains NOT_CONNECTED. A generated request ID is not a job ID.
No task is persisted/dispatched and no source content is automatically sent to a model.

Actual staging Aside checks covered exact two selected IDs/versions, current code and role,
reference-only JSON/Markdown, six recipes, input/selection invalidation, preserved admin-write
capability and desktop layout. Nine structured checks passed; a separate note-edit check also
passed. The real viewport screenshot was visually inspected. Mobile viewport QA remains unverified.
Previous one-shot harness failures were API/timing issues, not successful tests; final evidence
came from interactive Aside browser actions and downloaded artifacts. No browser backend fallback.

Before/after read-only audits matched all inspected fingerprints and table counts, including
People299, Organizations347, Claims/Evidence5576/5576, observations4170, snapshots370 and zero admin
receipts; schema remains0007. Anonymous private API403 and untrusted-Host Web404 were rechecked.
No live Person/Claim decision, source collection, schema change or org.go27 commit was performed.
The [completed preparation plan](../exec-plans/completed/admin-work-playbook.md) records this scope;
[the native execution prerequisite](../exec-plans/blocked/admin-agent-execution.md) remains blocked.


A follow-up synthetic probe on2026-09-24 used only a disposable workspace and provided prompt,
ignored user-wide config, disabled apps/plugins/shell/browser/computer tools, and tested the installed
native multi_agent_v2 feature without changing project/global settings. It again returned BLOCKED:
no role selector in collaboration.spawn_agent, no child ID, no configured marker returned and zero
children launched. This confirms the tested route still does not justify enabling live dispatch;
it does not prove that every native interface or future client has the same limitation.

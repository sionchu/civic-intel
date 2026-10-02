# Assembly site pilot

Status: IN_PROGRESS, 2026-10-02. Owner selected option 1 from the reviewed
[orchestration proposal](../../operations/NEXT_PHASE_ORCHESTRATION.md).
Implementation base: `788ae0ce29fc86ce74283e8b3c0a53aeb1bb7a17`.
Current topology decision: Mac SSD DB/API, cloud web on Sites later; implementation base
`0865e5d`. The local SSD runtime is verified. Publication, Sites connectivity/Workers output
and rendered/mobile acceptance remain incomplete.

Owner priority update, 2026-10-02: Gukgam audited institutions first; retain the Assembly
capture, DRAFTs and conflict without publication. The existing Gukgam page/API and exact local
reviewed packets are reused under the [Gukgam work order](gukgam-2026-ontology-research.md).
Mac read-only inventory found zero Organizations/public audit targets. Institution bindings
and official witness/reference lists require their separate gates; legislators are audit actors.
Current continuation: [frontend/backend plan](../../operations/FRONTEND_BACKEND_INTEGRATION.md#국감-우선-진행).

## Scope and ownership

Prove one National Assembly current-roster site slice using the owner-selected Mac SSD
site-serving SQLite and loopback API, separate safe identity/DRAFT creation, gated public
records, and a readable Person→Claim→Evidence→Source UI. Preserve the successful original
SSD capture and existing Railway corpus/backup. Sites delivery is a later stage.
No generic transfer/importer, production service creation, new domain/indexing, paid plan
change, recurring collector or public API/database endpoint is in scope.

MAIN owns shared contracts, integrated worktree, actual operational access, keys, backup,
writer allocation, code integration and deployment. Original root master/user contract edits
are preserved. Child agents perform read-only preparation/review; they cannot access keys or
operational databases. No recursive delegation; at most three concurrent work slots.
Claude Opus is an external tool-less source-packet collaborator, not a Codex model subagent.

The preserved historical staging target is project `f403bc33-2190-4177-9150-2971e25dd9ee`, environment
`b66af015-7013-4c38-9720-de48ec6f9a71`, PostgreSQL service
`2a4eb90c-c73a-4d22-bd25-14d0f80c6a44`. Current schema, contents, deployed code and backup
must be verified before operational mutation. Allocation is coordination, not a universal lease.
Live source/identity/publication effects stay separate and require their actual gates.

## Work orders

- PILOT-WEB-API-BRIDGE (base f930a69): MAIN extends the canonical server-side public
  client in apps/web/app/data.ts with fixed-origin credentials, bounded GET routes,
  redirect rejection and an eight-second timeout. Owned paths include its runtime tests,
  web dependency/scripts, integration plan, INDEX and HANDOFF. Fixture requests only;
  no credential read, tunnel creation, source/DB mutation, Site registration or deployment.
  Acceptance: actual transport regressions, existing web contracts and full make verify.
  The later Worker build and real authenticated Site-to-Mac route remain separate.
- PILOT-OPUS-PACKET: bounded Person presentation proposal/patch only. Allowed paths:
  `apps/web/app/people/[id]/page.tsx` and `.profile-page`-scoped CSS in `styles.css`.
  Read-only context: DESIGN, DTO/data boundary, existing presentation helpers and UI tests.
  No tools, source rows, credentials, dependencies, domain/API changes or deployment authority.
  MAIN applies only validated exact-base changes and updates copy-coupled tests without
  discarding semantic/portrait/provenance regression checks.
- PILOT-DATA-PREFLIGHT: source_worker reviews existing contracts, SourcePolicy, exact effect
  paths, collision/coverage and recovery checks. No fetch or DB access; returns a bounded
  target-specific execution request. MAIN remains sole operational writer.
- PILOT-DEPLOY-PREFLIGHT: read-only Railway/GitHub metadata and release/backup route inventory;
  no credentials, SSH registration, data writes, config changes, push or deployment.
- PILOT-QUALITY/RISK: independently review actual candidate changes and exact data/exposure
  effects after preparation slots finish; read-only, no edits or fabricated human approval.

## Original staging milestones and gates

These establish the preceding executed pilot and its preserved evidence. The owner-selected
SSD continuation below supersedes target/recollection/resize steps; it does not erase the
existing PARTIAL run or authorize more Railway writes.

1. Pin baseline and activate this plan. Confirm source/worktree, source-policy grant, release
   path, private staging target and ownership. Baseline full local verification already exists;
   new changes receive focused and integrated verification.
2. Run one bounded authenticated Opus collaboration on permitted frontend code and synthetic
   semantics. Record actual model/exit/output hash. Apply/review the Person reading slice.
3. Read-only target preflight and logical backup/restore rehearsal. Pin schema/row/run counts
   and protect existing data. Prepare exact source execution environment and hard-stop/recovery.
   No ignored SQLite/Golden DB is a deployment input. If target access or existing writers are
   unverified, stop that operation and continue independent code/fixture work.
4. Integrate code, independent Quality/Risk review, targeted checks and `make verify`.
   Require actual PostgreSQL evidence for the claimed target path. Aside-only rendered UI
   acceptance checks directory→Person→Evidence→Source, responsive/keyboard/long-Korean and
   missing/error/UNKNOWN/PARTIAL/conflict states. Directly inspect captured screenshots.
5. In the approved exact target scope, run existing `civic observe assembly` once: feeder
   `national_assembly_members`, scope `current_member_roster`, SourcePolicy
   `11000000-0000-0000-0000-000000000001`, page100, max8 requests, interval≥1s,
   fetch120s, hard-stop180s. Audit coverage/provenance/privacy/checkpoint. No automatic retry.
   Then execute separately gated materialization to DRAFT and exact eligible publication.
   Keep ambiguous identities in review. Never invent human_verified or expected Person counts.
6. Validate the exact integrated commit/artifact on existing staging: CI, migration/readiness,
   public reads, DB preservation, rollback, current desktop/mobile UI. Deployment changes,
   public-record selection and any material access/cost decision are made only from their
   concrete reviewed result. Production resources/public-beta expansion remain a later plan.

## Evidence and acceptance

Acceptance requires the complete live site-reading chain at a reported commit, actual bounded
source run/checkpoint and coverage, valid identity/publication state, no source-key/private-contact
leakage, executed code/PG/recovery checks and actual Aside visual/interaction evidence.
Local checks, remote CI, deployment readiness, data commit and rendered acceptance are separate.
Missing browser readiness, target access, rights, coverage, identity or publication approval is
reported honestly; no layer is marked PASS from another layer's result.

## Progress

- Server-read continuation at base f930a69: canonical web client now keeps credentials
  server-only, binds Access credentials to one HTTPS origin, limits public GET paths,
  rejects redirects and times out at eight seconds. Actual disposable HTTP and mocked
  credential/error cases: eight runtime tests PASS; total web tests 34 PASS.
  Full make verify exit0: 862 Python PASS, four optional PG skips, six SQLite warnings,
  364.43s; lint/mypy/Golden/architecture/typecheck/Next 16.3.8 build and assets PASS.
  Security patches within the existing Next major and brace-expansion constraints applied;
  npm audit reports zero vulnerabilities. Node's typeless-module test warning remains.
  Independent code and plan reviews found no defect. New Vinext static check remains
  12 supported/zero issues; Worker build and live authenticated connection remain NOT_RUN.
  [Connection plan](../../operations/FRONTEND_BACKEND_INTEGRATION.md) and
  [executed code receipt](../../receipts/web-api-bridge-20261002.json).
- Baseline pinned at 788ae0c; integrated worktree initially clean. Existing candidate source
  0eb326d and previous test receipts preserved. No operational mutation at activation.
- Three prior status audits and the proposal's independent consistency review completed.
- Owner option1 selected; source/deployment preflight and frontend packet preparation delegated.
- Actual tool-less Opus collaboration completed: claude-opus-5-5, exit0, two turns,
  240.641s. MAIN validated the seven-file exact input base and applied the scoped Person patch.
  Final independent review found no actionable regression. UI commit: af46132d49d0e8106851c473bfcda69c50f89345.
- Final `make verify` exit0: 853 Python passes, 4 optional PG skips, 6 SQLite warnings;
  mypy 146 files, Golden 13 checks, architecture, web lint/typecheck, 26 web tests and production build PASS.
  All four optional PostgreSQL tests separately executed in a fresh disposable local DB, exit0.
- Live staging schema 0008 and 299 public people verified. Fresh private logical backup restored to a
  separate local PG18 database with matching canonical counts, policy, coverage and provenance.
  A synthetic 299-record PG rerun created zero duplicate observations and retained exact provenance.
- The authorized source effect ran once at 07:06Z. Parent exit 1; durable run 876cd05a is PARTIAL,
  ConcurrentWrite, 100 unchanged/0 created. Current checkpoint is page1, manifest100/299.
  Sources/observations/People/Claims/Organizations/public counts stayed unchanged; one snapshot
  and one run were added. No identity, publication, automatic retry or operational restore ran.
- Historical PostgreSQL logs identify file-extension failure with No space left on device.
  Actual data filesystem is 100% used, with 552960 bytes available; configured volume 500 MB.
  Shared memory has 61759488 bytes available. Capacity was missing from the original allocation
  preflight; it is now mandatory before any further source allocation. No speculative backend fix.
  Logs identify an INSERT into source_snapshots in the failure window, but no per-run/session
  correlation ID. Persisted ConcurrentWrite and disk-full diagnostics retain separate provenance.
- Owner reopened Aside. Actual production-artifact DOM evidence confirms directory filtering,
  Person content, keyboard audit disclosure, source-policy text, UNKNOWN/PARTIAL and not-found.
  Native source anchors preserve hrefs; final source hash navigation was observed after keyboard
  interaction. Immediate mouse navigation/scroll landing remain unconfirmed. Summary height 44px,
  focus outline 3px and no desktop overflow are DOM measurements, not visual acceptance.
  Screenshot calls timed out at 30s/60s; writable mobile viewport API is unavailable.
  UI verification incomplete; conflict/loading/transport-error and narrow layout remain NOT_RUN.
- An exact three-file UI patch applies cleanly to verified public master 77e2767 and matches the
  candidate bytes. No branch push, PR, merge or deployment ran. Deployed SHA remains unavailable
  in both runtime-variable and deployment-metadata probes. The Mac SSD capture is unchanged.

## Concrete recovery decision

Owner decision, 2026-10-02: supersede the resize proposal below with Mac/SSD topology 1.
Keep existing Railway data and its backup unchanged. Use a consistent SQLite backup of the
successful immutable SSD capture as a new private site-serving target; MAIN is its sole writer.
Reuse the byte-verified installed package and canonical API/UoW, with schema 0008 and a
read-only loopback API. Verify storage identity, disconnect behavior and public-read gates before
continuing separate identity/DRAFT effects. No new provider request is needed for this copy.
Sites documentation/SDK research and local deployment preparation are approved; the owner
explicitly referred to Sites publication as later. No Site registration/publication, cloud API
connectivity, public API endpoint, recurring collector or paid resource is executed in this step.
Full existing cloud-corpus migration is not implied by the fresh Assembly-only SSD target.
Operational details and evidence are recorded in
[SSD operations](../../operations/MAC_SSD_SITE.md).

Executed SSD continuation: consistent source backup PASS; schema/provenance/full manifest
PASS; offline sandboxed `civic materialize assembly` created 298 Persons/DRAFT Claims and
298 Evidence/links; one OPEN EXACT_BIRTH_DATE_CONFLICT preserved. No publication or fetch.
Canonical read-only API and user LaunchAgent now return health/ready/people/person 200,
298 directory entries, admin/review and DRAFT-only Source 404. Owner reported Python disk
access approval before the successful independent login-service probe and permanent startup.
Actual Mac SSD disposable missing/replaced-file checks return 503; read-only write rejection
PASS. Original capture hash unchanged. Reboot/unplug, cloud connectivity and Sites deployment
were not run. Details: [SSD operations](../../operations/MAC_SSD_SITE.md) and
[runtime receipt](../../receipts/mac-ssd-site-20261002.json).
Vinext 1.0.1 static check: 12 supported, zero issues; no Workers build or frontend port yet.
Final code verification is recorded with the SSD receipt; former resize choices below are
historical proposals, not the selected execution route.

Evidence is [the pilot receipt](../../receipts/assembly-site-pilot-20261002.json).
The source request is [the executed request](../../operations/staging-assembly-one-shot-request.json).
The exact UI release candidate is Person page, scoped CSS and copy-coupled UI assertions only;
it does not release the whole architecture branch. Its patch hash and applied-byte evidence are
in the receipt. Release remains gated by actual UI acceptance and a concrete public-code/deploy decision.

### Superseded staging options

These were evaluated before the owner selected the Mac SSD path. Neither is the current
recommended next action; retain them only as history of the preserved staging incident.

1. Previously considered: expand staging postgres-volume 88b510ef-4336-4cb3-ba30-09256636e427 from 500 MB
   to 2000 MB within the existing plan, after owner accepts cost/restart implications. Preserve the
   verified private backup and PARTIAL run. Verify schema/counts/readiness/capacity after resize,
   then separately allocate one fresh whole-roster run under the existing 8-request/1s/120s/180s
   limits. No blind resume of old pagination, automatic retry, identity or publication. If a paid
   plan change is required, stop and present its actual terms; this choice does not authorize it.
2. Previously considered: keep the current DB and Mac SSD capture; leave live source writes stopped and retain the
   committed frontend candidate while the Aside visual/mobile prerequisite is resolved.

Historical pricing check: Railway charged used volume storage at $0.15/GB/month; 2 GB fully used would be about
$0.30/month for volume storage alone. Subscription/CPU/RAM/egress are separate; the current
account plan and resulting total bill are not verified. Free/Trial has a 0.5 GB volume limit and
Hobby starts at $5/month. A full volume can require an offline resize and service restart; capacity
cannot currently be shrunk afterwards. Sources checked 2026-10-02:
[pricing](https://docs.railway.com/pricing/plans),
[volume behavior](https://docs.railway.com/volumes/reference).
No resize, plan change, deletion, VACUUM FULL, restart or new source attempt is authorized by this document.

## Stop and recovery

Serialize DB mutations and verify own child termination. Forced stop/RUNNING means
RECOVERY_REQUIRED and an explicit inspection, not a retry or invented FAILED. Policy ambiguity,
403/429, version drift, coverage failure and identity conflicts stop only the affected stage.
Never restore over an operational DB or downgrade it to test recovery. Keep the failed DB/run
and receipt. Meaningful cost, destructive loss, weaker security/public access, secret exposure
and unresolved rights remain owner decisions after concrete preparation.

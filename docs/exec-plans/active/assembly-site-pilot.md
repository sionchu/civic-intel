# Assembly site pilot

Status: IN_PROGRESS, 2026-10-02. Owner selected option 1 from the reviewed
[orchestration proposal](../../operations/NEXT_PHASE_ORCHESTRATION.md).
Implementation base: `788ae0ce29fc86ce74283e8b3c0a53aeb1bb7a17`.

## Scope and ownership

Prove one National Assembly current-roster site slice: bounded source acquisition into the
site-serving staging PostgreSQL target, separate safe identity/DRAFT creation, gated public
records, and a readable Person→Claim→Evidence→Source UI. Preserve the existing Mac SSD capture.
No generic transfer/importer, production service creation, new domain/indexing, paid plan
change, recurring collector or public API/database endpoint is in scope.

MAIN owns shared contracts, integrated worktree, actual operational access, keys, backup,
writer allocation, code integration and deployment. Original root master/user contract edits
are preserved. Child agents perform read-only preparation/review; they cannot access keys or
operational databases. No recursive delegation; at most three concurrent work slots.
Claude Opus is an external tool-less source-packet collaborator, not a Codex model subagent.

The staging target is project `f403bc33-2190-4177-9150-2971e25dd9ee`, environment
`b66af015-7013-4c38-9720-de48ec6f9a71`, PostgreSQL service
`2a4eb90c-c73a-4d22-bd25-14d0f80c6a44`. Current schema, contents, deployed code and backup
must be verified before operational mutation. Allocation is coordination, not a universal lease.
Live source/identity/publication effects stay separate and require their actual gates.

## Work orders

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

## Milestones and gates

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

- Baseline pinned at 788ae0c; integrated worktree initially clean. Existing candidate source
  0eb326d and previous test receipts preserved. No operational mutation at activation.
- Three prior status audits and the proposal's independent consistency review completed.
- Owner option1 selected; source/deployment preflight and frontend packet preparation delegated.
- Current observed browser prerequisite: Aside CLI works but daemon is absent. Attempt only
  documented non-destructive recovery; never substitute another browser transport.
- Current unknowns: actual deployed SHA/schema/contents, staging target backup, Opus execution,
  current rendered acceptance and target-specific source/identity/publication receipts.

## Stop and recovery

Serialize DB mutations and verify own child termination. Forced stop/RUNNING means
RECOVERY_REQUIRED and an explicit inspection, not a retry or invented FAILED. Policy ambiguity,
403/429, version drift, coverage failure and identity conflicts stop only the affected stage.
Never restore over an operational DB or downgrade it to test recovery. Keep the failed DB/run
and receipt. Meaningful cost, destructive loss, weaker security/public access, secret exposure
and unresolved rights remain owner decisions after concrete preparation.

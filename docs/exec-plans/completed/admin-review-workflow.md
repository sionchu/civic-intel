# Admin review workflow

Approved objective (2026-09-23): convert the existing private collection dashboard into an
operator workspace that can resolve work, not only count stored rows.

## Structural findings

- `decide_materialization` only automates the Assembly roster. ALIO observations and published
  organization disclosure Claims never enter a source-person review/registration workflow.
- Stored OPEN review rows are not the total unresolved workload. The UI needs an observation-backed
  work queue, not a claim that OPEN=0 means no work remains.
- Existing server-only tokens authorize private reads, but no bounded mutation service, concurrency
  preconditions, durable admin action receipts or correction lifecycle exists.
- A Person row, named disclosure, source identity and reviewed cross-source identity are distinct.
  A larger Person count alone is not success; registered/linked/held/excluded must reconcile to input.

## Coherent implementation scope

This approved plan supersedes earlier read-only admin exclusions, not the public read-only boundary.

One private admin workspace reusing existing repository, SourcePolicy, immutable observations,
IdentityReviewItem, PersonObservationLink and Claim/Evidence publication validation.

1. Real ALIO named-record queue, exact-name candidate discovery and per-disposition counts.
2. Signed preview -> explicit confirmation -> atomic command + receipt. No generic SQL/CRUD route.
3. Persist HOLD/EXCLUDE/REOPEN, reviewed source-scoped Person registration and evidence-backed linking.
4. Claim review/publication/withdrawal and a version-preserving correction draft; entity name correction
   and explicit soft deactivation. Source snapshots/observations are never overwritten.
5. Reviewed Person merge with explicit surviving ID, bridge evidence and impact; block unsupported
   dependent records instead of silently discarding/reassigning unknown domain objects.
6. Browser UI for selected/bounded batch actions, reason/evidence, before/after, stale-preview rejection,
   actual commit result and audit history. Server acknowledgement precedes success feedback.

## Required minimal migration / risk note

No existing row records generic operator actor, immutable before/after, command hash and idempotency.
`IdentityReviewItem` only represents identity reviews; overloading it with every DB operation would
break semantics. Add one append-only `admin_operations` receipt table in Alembic 0007. No second
raw store or graph store. Existing domain tables/IDs remain intact. The read contract can accept
0006 during rollout because 0007 is purely additive; writes require 0007 and explicit private opt-in.

Before operational migration: populated backup -> disposable restore -> 0007 upgrade/downgrade/upgrade
-> counter/provenance checks. Upgrade the existing API to the compatible read contract before changing
staging schema. No downgrade on staging, no unreviewed real-person create/link/merge/delete.

## Evidence gates

Unit/integration: auth, CSRF, signed preview expiry/tamper, payload and database drift, source policy,
immutable observation versions, duplicate identity conflicts, whole-batch rollback, idempotent retry,
no implicit FACT promotion, audit history, migration populated round trip and public read compatibility.
Browser: actual source queue, selection/batch, preview/cancel/commit, correction + publish + withdrawal,
new Person registration/link/merge on disposable data, audit and keyboard/mobile; no fake buttons.
Regression: full verify and GitHub CI. Report code, test DB writes, staging reads/migrations/writes
and production deployment independently.

## Concurrency and publication semantics

Admin write sessions use READ COMMITTED, an advisory transaction lock, row locks and a Person-table
lock for identity operations; previews carry a five-minute signed command/state fingerprint. A stale
state cannot be committed. Read-only sessions retain repeatable-read. Accepted source-record Persons
are explicit human-reviewed registrations, not automatic name-based identities. New role Claims
remain DRAFT/CLAIM until separately approved; correction drafts preserve original Claims until a
successful replacement publication. Merge/deactivation retain original records and dependent evidence.

## Algorithms / references

OpenRefine: faceted reconciliation and explicit judgments; never apply its same-string mass-match rule
to person identity. React-admin: explicit mutation acknowledgement and audit; reuse interaction, not
install another app framework. OCCRP Aleph: entity-centric evidence/navigation.
Splink and BGE-M3 were evaluated as future candidate retrieval/ranking, not identity authority.
The first deterministic candidate blocker is exact canonical name + existing source anchors;
reasons stay visible. No model/API expense, embeddings, fuzzy AUTO_MERGE or private-field harvesting.

## Closure — 2026-09-23

Status: COMPLETE for the private admin dashboard/workflow slice, not for person collection coverage.
PR #141 merged as `e141dc363a2c9357fb43519dde70f168a08c946d`; GitHub Verify `35852398793`
passed, including 553 tests / 1 skipped, migrations, PostgreSQL load, backup/restore and artifacts.

Merge did not itself create a new Railway deployment. The exact tracked source archive was uploaded
explicitly to the existing staging API. Deployment `62438070-020c-4af2-bb7f-666065421dde` reached
SUCCESS; pre-deploy applied 0006 -> 0007 and `/ready` returned 200. No new service/domain was created.
The public API remains the non-operator factory; admin write authority exists only in the opted-in
loopback session on the operator PC.

Fresh PostgreSQL inspection at 2026-09-23T14:43:45Z confirmed schema0007, zero admin receipts and
unchanged pre/post fingerprints for People299, Organizations347, Claims5576, Evidence5576,
observations4170 and snapshots370. ALIO queue:3624 UNREVIEWED records /3076 distinct name strings.
No live Person registration/link/merge/deactivation/publication or org.go27 import was performed.

The actual staging browser passed13/13 checks: write-mode capability, real backlog, canonical count,
preview/cancel, exact evidence map, unresolved candidates, empty committed-action history, Claim
status filter, original org.go preflight, CSRF and desktop/mobile rendering. Mutation browser17/17
and explicit link/merge tests remain disposable PostgreSQL evidence, not live decision evidence.

Operator shortcuts now target `http://127.0.0.1:3315/admin/review` and the canonical admin worktree.
The existing worker defaults remain3310/8310; this installed launch explicitly uses3315/8315.
Source backup remains outside Git under the restricted operator backup directory.

## Next concrete action

Use the ALIO review queue to select and inspect a bounded real batch, then perform explicit
reviewed registration/linking from the admin. Do not infer thousands of unique People from name
strings or execute real-person decisions as dashboard tests. The older org.go27 atomic import
remains a separate pending action.

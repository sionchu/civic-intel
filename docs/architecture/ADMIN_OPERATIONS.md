# Private admin operations

## Purpose and authority

The approved admin-review workflow changes the internal operator boundary, not the public
read-only product. The shared SQLAlchemy repository remains the only write implementation.
Raw SourceSnapshots and FeederObservations remain immutable. No generic SQL or table editor exists.

## Workload is not a Person count

The ALIO queue is derived from PUBLIC named source observations and exact stored observation links
plus latest IdentityReviewItem disposition. It reconciles UNREVIEWED / HELD / EXCLUDED / REGISTERED /
CONFLICT to the named-record total. Distinct name strings are not deduplicated people. Stored OPEN
review rows alone do not describe backlog. Exact name or stored-alias overlap returns candidates,
never identity authorization. The automatic Assembly materialization rule is unchanged.

## Explicit commands

`packages.domain.admin.AdminCommand` is the allowlisted immutable input contract. Each command
contains a unique request ID, 1–25 selected record IDs, an operation and substantive reason. Identity
registration/link/merge requires an explicit human review attestation. Link/merge also needs a
specific surviving/current Person, existing official Evidence and a named official continuity basis.
The existing cross-lane resolver still rejects name-only evidence and hard birth-date conflicts.
The attestation is a human judgment, not an algorithm proving that the document entails identity.

Registration validates the exact successful ALIO checkpoint, observation version, PUBLIC name,
source storage permission and current Organization binding. It creates a reviewed source-context
Person/link and DRAFT, attributable CLAIM role record with exact Evidence. It does not bulk-promote
names, issue FACTs, publish automatically or resolve all cross-source duplicates.

Supported actions:
- HOLD / EXCLUDE / REOPEN on named ALIO source records;
- REGISTER_PERSON / LINK_PERSON;
- SUBMIT_REVIEW / PUBLISH / WITHDRAW for canonical Claims;
- CORRECT_CLAIM as a new attributable draft with its own selected Evidence;
- RENAME_PERSON with previous name retained as an alias;
- DEACTIVATE_PERSON with related current Claims withheld and links/appointments deactivated;
- MERGE_PERSON with explicit survivor, bridge Evidence, bounded dependency review and preserved
  original Person/Claims/Evidence. Unsupported asset/event/hypothesis dependencies block the merge.

A correction draft does not hide the original. Publishing it supersedes/withholds the exact original
atomically. A generic correction is not silently rewritten into an official source-specific role
predicate. Re-extracting a changed official role still needs a new verified source record.

## Transaction and audit contract

Preview performs no writes. Its command/state fingerprint is HMAC-signed, actor-bound and valid for
five minutes. Commit needs that signature and explicit final confirmation; it revalidates every
relevant record and current scope. Stale state or any invalid item cancels the entire batch.
PostgreSQL uses READ COMMITTED, an advisory transaction lock and locked inspected rows; Person
mutations additionally lock the Person table against competing identity writes. SQLite uses BEGIN
IMMEDIATE. Newly created rows flush by FK table order. Unknown dependent domain references fail closed.

A successful transaction appends one immutable `admin_operations` receipt containing actor, action,
reason, request/command/state hashes, selected IDs, field-level before/after, evidence basis and result.
A repeated identical request returns its original receipt; a changed request with the same ID fails.
The receipt and domain writes commit together. The database rejects audit UPDATE/DELETE. Failed or
cancelled previews are not reported as completed actions. No general undo or hard-delete operation
is exposed; explicit reopen/withdraw/deactivate/correction operations retain history.

## Publication and graph

Approval reuses `validate_claim_publication`; it never changes epistemic status into FACT.
Reviewed ALIO role publication rechecks source version and exact Person/Organization/observation
binding. Only published, source-backed, active exact bindings enter `DISCLOSED_ROLE_AT` edges.
Both Person and Organization graph reads retain canonical IDs and Evidence/Source references.
Source-listed noncanonical role-holder nodes remain distinct records, not inferred Persons.

## Deployment and security

One additive migration, 0007, owns the append-only receipt table. No domain rows are migrated.
The canonical reader deliberately accepts 0006 during rollout; admin commits require 0007.
Migration 0001 excludes the new table so fresh 0006 databases do not pre-create a future schema.
No operational downgrade is permitted. Before rollout: populated logical backup, separate restore,
upgrade/downgrade/upgrade on the disposable database, and unchanged domain fingerprints.

The local operator factory is opt-in; defaults remain read-only. `--enable-writes` activates only
bounded confirmed commands and records the OS/operator actor. API token is server-only; browser
writes pass through an origin/intent-checked Next handler. List/detail/history data is no-store.
No public admin, extra cloud service, unrestricted MCP SQL, external model or duplicate datastore.
This is a trusted local-OS admin boundary, not a multi-user internet RBAC product.

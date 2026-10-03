# Gukgam Mac Organization identity work order

Task `gukgam-mac-organization-identity-preparation`, MAIN / record curator,
base `7b539a4d6c17c9ed1240f1680ad39c80e5fa8879`, 2026-10-03.
Status: **REVIEW_PREPARATION_ONLY**. This work order prepares the active plan's Mac
target/source/Organization review; no canonical identity decision has been made.

The Mac target has zero Organizations. The historical 41 target-to-Organization draft
occurrences belong to another database, so their references must be reviewed against
the Mac's own source evidence and canonical state. The first institution scope is the
existing 47-row Science pilot: 32 institution roles, 13 general witnesses and 2 reference
people. Historical 41-pair review and the 70-item MOIS proposal remain separate work.

## Assigned target and fresh baseline

| Field | Evidence / current state |
|---|---|
| Target alias | `canonical-mac-ssd` |
| Assigned existing file | `/Volumes/data/civic-intel/service/assembly.sqlite` |
| Transport | Remote Desktop Commander; read-only aggregates |
| Observed interval | 2026-10-03 05:21:21.984117–05:21:22.425214 UTC |
| Schema / file mode | 0008 / 0600 |
| Integrity / FK violations | quick_check ok / 0 |
| Preserved corpus | 298 People, 298 DRAFT Claims, 298 Evidence rows |
| Source corpus | 3 Sources, 3 Snapshots, 299 observations, 1 SUCCESS run |
| Organization / witness / MOIS rows | 0 Organizations, 0 witness runs, 0 MOIS runs |
| Active runs / checkpoint | 0 RUNNING; one valid same-scope, cursor-matched checkpoint |
| Loopback health | HTTP 200; body not read |
| Target identity at a later write | Fresh exact target/file/schema proof required |
| Exclusive writer ownership | NOT_PROVEN by these read-only counts |

This timestamped baseline is an observation, not an operational write grant. Recheck the
assigned file and its current state at any later effect boundary. The separate Assembly
capture target, a disposable local proof DB and historical staging are not substitutes
for this service target. [Mac runtime contract](MAC_SSD_SITE.md).

## Versioned review inputs

| Input | Bound reference | Review state |
|---|---|---|
| Institution-witness PDF | SHA-256 `7ef99c6e217dc775cb2878f395a02eebcdd95cb4eecfa852b6d08b94d0217b9f` | Exact previously captured bytes; actual field review pending |
| General/reference PDF | SHA-256 `bb1cf15928ef93e5e4e974fa2971fad628bedc58a1416ea890a46de9308f861d` | Exact previously captured bytes; actual field review pending |
| Witness research / full packets | 412 rows: 370 institution roles, 29 general, 13 reference; full packet counts370+42 | DRAFT_NOT_HUMAN_REVIEWED |
| Pilot packets | Exact existing32+15 rows and their versioned manifests | DRAFT_NOT_HUMAN_REVIEWED |
| Plan occurrence candidates | Existing source-to-plan review; every pilot row retains two occurrences | Neither date selected; raw plan/current-edition check pending |
| Single-code MOIS candidate | Existing ignored local user-review artifact, SHA-256 `e38190c87c0f3bb61b5ff7ee25c77f25a5b7cd481c34f7f05716977866a89530` | Candidate only; not a Mac Source/Observation or identity decision |
| Historical41-pair DRAFT | Historical reference digest `9bb202c3de7c219382f69c91b8b0014bba7442428b673b55ac7ebbf766e711a9` | Recorded reference only; original private artifact not reverified in this heartbeat |
| Historical41 validated DRAFT | Historical digest `ea46c6c5e75cc8dc006de2eddcf5a244331c9a2a058e9f99c07c49b3352078a8` | Not an approved batch; old database identifiers are not Mac bindings |
| Separate70-item MOIS proposal | [Existing review artifact](../research/gukgam_2026_mois_organization_proposal_2026-09-28.json) | Review-only; outside this pilot identity choice |

The heartbeat revalidated the local research/packet hashes and canonical parsing, not the
PDFs themselves or current official editions. The private MOIS artifact was not opened
or rehashed in this heartbeat; its digest above is the prior recorded review reference.
No provider rows or provider code values are reproduced here. Exact source/packet details
remain in the [witness contract](../architecture/GUKGAM_WITNESS_PACKET.md),
[source-to-plan receipt](../receipts/gukgam-witness-plan-review-20261003.json) and
[bounded MOIS receipt](../receipts/gukgam-mois-lookup-20261003.json).

## Required review record before a canonical decision

For each selected source occurrence, the eventual review must retain:

1. The exact source policy, artifact/packet version, printed target label and occurrence
   reference. An institution heading, audited target and employer are distinct fields.
   Any field-level human review must come from an actual reviewer of the exact fields.
2. The institution's identity evidence, provider namespace, provider identifier, full
   hierarchical name, organization level and relevant lifecycle/time fields. A source
   identifier is not a canonical Organization UUID. A name match or org.go/MOIS code
   resemblance does not decide cross-source identity.
3. The Mac target's own source/snapshot/observation provenance after any separately
   authorized acquisition. The recorded Mac source corpus comes from the Assembly capture;
   local MOIS or historical staging provenance must not be claimed as present on Mac.
4. The actual decision and supporting evidence: unresolved candidates remain review-only;
   a resolved choice requires the reviewed source-specific creation/binding contract and
   applicable canonical path. Historical staging Organization IDs are not copied into
   the Mac. Multiple candidates or missing evidence fail closed.
5. A separate identity-effect request with immutable code/package, precise inputs, target,
   current preflight, writer ownership and stop conditions. No Organization materializer
   or crosswalk is authorized by this document. Person identities and Claims use their
   own subsequent contracts.

Decisions currently remain **NOT_DECIDED**. SourcePolicy and exact-target readiness precede
source effects. Actual source-field review precedes witness acquisition. Organization
review does not waive that acquisition gate. A source success, Organization creation or
identity decision does not approve Claim publication. See
[Organization Claim/Evidence](../architecture/ORGANIZATION_CLAIM_PUBLICATION.md),
[MOIS provider identity](../architecture/MOIS_ORGANIZATION_CODE_FEEDER.md) and
[identity resolution](../architecture/IDENTITY_RESOLUTION.md).

## Acceptance and execution boundary

This preparation is reviewable when the assigned target, timestamped baseline, exact
pilot/source version references, historical-only references and undecided gates are
explicit and linked. Its output is this work order and the monitoring receipt; it is
not a worker input, approved identity artifact or canonical Claim batch manifest.

No source fetch, operational DB write, migration, restart, human attestation, canonical
Organization/Person creation, publication or deployment is executed. MAIN owns the next
integration/effect request after the applicable factual review exists. Ongoing heartbeat
checks preserve the current target and report changed or unavailable state.

Governing [active execution plan](../exec-plans/active/gukgam-2026-ontology-research.md)
and [monitoring evidence](../receipts/collection-status-20261003.json).

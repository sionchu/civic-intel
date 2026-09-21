# Assembly reviewed distinct-Person resolution v1

Status: completed on 2026-09-16 for local, CI, staging and browser evidence; the next implementation
milestone is the existing Evidence Directory read-model path.

## Objective

Close the existing `EXACT_BIRTH_DATE_CONFLICT` review for the official National Assembly current
roster only when an operator explicitly accepts that the provider record represents a distinct
canonical Person. The transaction must retain the existing candidate Person, preserve the exact
observation provenance, and use the normal public Claim/Evidence path.

This is a reviewed resolution of one already committed observation. It does not relax the
automatic `AUTO_CREATE` / `AUTO_LINK` / `REVIEW_REQUIRED` / `HARD_CONFLICT` gate and does not
promote the Assembly source beyond its existing L3 enumeration contract.

## Reviewed input

- Review item: `b0b404b2-4c23-4577-8678-c9047cac7fe6`
- Observation: `0fce4b39-95cf-4401-b0c2-e3583dad14b9`
- Provider record key: `H7X3372O`
- Existing candidate: `1bd253ae-3de7-42de-81e5-b450c1fb8e8b`
- Source scope: `national_assembly_members` / `current_member_roster` /
  `legislative_member_roster`

The resolution is bounded by the provider key, exact observed birth date, exact canonical name,
the successful full-roster checkpoint manifest and the official Assembly API SourcePolicy. It
never uses name-only linking, an asset/row key as a Person ID, or a family/adjacency inference.

## Persistence contract

Use the existing `IdentityReviewItem`, `PersonObservationLink`, `Person`, `Claim`,
`ClaimEvidence`, `Source`, `SourceSnapshot`, `SourceRun` and `SourceCheckpoint` records.

- A successful review creates one new `RESOLVED` Person and one published Assembly `HELD_ROLE`
  Claim with deterministic Claim/Evidence IDs for safe retry.
- The new Person receives a `REVIEWED_CREATE` link with
  `REVIEWED_DISTINCT_IDENTITY`; the automatic four-action enumeration report is unchanged.
- The original candidate is never updated, merged or superseded.
- The review item is marked `RESOLVED` with a non-secret operator note in the same transaction.
- A failed policy, source-contract, checkpoint/version, identity, publication or reference gate
  rolls back the Person, Claim, Evidence, Link and review-state update together.
- A retry of the already resolved item is a read/validation-only idempotent result. A newer
  current-roster observation version cannot resolve an older open review.
- No migration or persistent table is needed; the existing string-backed action/class columns
  already persist the extended canonical enum values.

## Milestones

### M0 — local contract and regression gate

- [x] Add the explicit reviewed action/class without changing automatic decisions.
- [x] Add the source-specific repository transaction and operator CLI operation.
- [x] Cover success, candidate preservation, exact provenance, idempotent retry, stale-version
      rejection, publication rollback and public profile exposure.
- [x] Inspect the complete diff and create the coherent local commit.
- [x] Push the coherent commit and record the CI result.

M0 local evidence (2026-09-16): the focused Assembly/materialization/API regression passed with
36 tests and the reviewed-resolution module passed with 10 tests; the complete Python suite
passed with `349 passed, 1 skipped`; Ruff and mypy passed; the Golden quality report passed; web
lint, typecheck and nine UI tests passed; the production build and standalone asset preparation
passed. No schema, migration or dependency change was made.

M0 remote evidence (2026-09-16): commit `d81499f433256dc59f8fcf2dca0ec77a34ba2a01` was pushed
to `origin/master`. GitHub Actions Verify run `35080092373` completed successfully in 2m41s,
including canonical verification, Alembic round trip, PostgreSQL migration/load/API,
provider-independent backup/restore and deployment-artifact checks.

### M1 — staging reviewed resolution

- [x] Capture a fresh provider-independent logical staging backup outside the repository before
      any database write; no Railway plan/resource change is allowed.
- [x] Deploy the pushed code to the existing staging API service only.
- [x] Resolve the exact review item through the explicit source-specific CLI operation.
- [x] Run the existing successful-roster Base Profile publisher for the newly linked observation.
- [x] Read-only verify counts, candidate preservation, review status, exact Claim/Evidence/
      Source/Snapshot provenance, subject XOR and privacy gates.

M1 backup/restore evidence (2026-09-16): the pre-write staging baseline was read through the
existing private Railway tunnel at schema head `0006`, PostgreSQL `18.6`, with 26 public tables.
It contained 298 People, 1 Organization, 7 Sources, 7 SourceSnapshots, 3 SourceRuns, 2
SourceCheckpoints, 314 FeederObservations, 298 PersonObservationLinks, 1 open IdentityReviewItem,
1,491 Claims and 1,491 ClaimEvidence rows. `asset_disclosures` and `asset_items` were empty.

The provider-independent logical backup was captured from that staging database with
`pg_dump --format=custom --no-owner` at `2026-09-16T09:52:17.5347818Z` (UTC), measured `349,651`
bytes, SHA-256
`CBDC5534E105E4695450A4044F75B34C679C479889D19867D834333576942973`. The dump remains in a
private temporary path outside the repository and is not committed. The active staging API
revision at capture was `10ef8317cd01ac3f1c8933647a0cfecdf1c7b69b`; the repository revision being
prepared is `ac9fbc6a2391cec9a884cdd7db7472d8582e41b1`.

The dump restored with `pg_restore --no-owner --exit-on-error` into a loopback-only disposable
local PostgreSQL `18.6` `restore_target` in `0.451` seconds. Restored schema head/table set and
all baseline counts matched. The restored read checks returned subject-XOR invalid `0`,
ClaimEvidence provenance mismatches `0`, SourceSnapshot fulltext rows `0`, and the restored API
returned `/ready 200`, `/health 200`, `/people 200` with 298 rows and unknown Person `404`.
The disposable cluster was stopped and removed after the smoke; the staging database was not
dropped, reset, migrated or written. Railway-managed backup/PITR remained unused and no new
resource or billing change occurred.

### M2 — staging/API/browser evidence

- [x] Verify `/people` exposes the new resolved Person and the existing candidate separately.
- [x] Verify the new profile shows only canonical Claim/Evidence output and the four Base Profile
      fields; raw normalized provider payload and contact fields remain absent.
- [x] Record staging/browser evidence separately from CI, release and production claims.

M1/M2 staging evidence (2026-09-16): the existing Railway staging `api` service was redeployed
from source as deployment `5da14c38-4f77-4bc1-a247-3910c4fb03d7`, commit
`013df121f3ff17c5ee2f251b0a79585123507a3c`, with status `SUCCESS`. No new service, plan, domain,
schema revision or dependency was introduced.

The approved source-specific operation resolved review item
`b0b404b2-4c23-4577-8678-c9047cac7fe6` for provider record `H7X3372O` with action
`REVIEWED_CREATE` and decision class `REVIEWED_DISTINCT_IDENTITY`. It created Person
`8b5f1e48-e7be-47cb-994e-da89dfdbce55` and Claim
`6ea439b2-cebd-553a-9be4-58936bf4fc94`. The existing candidate Person
`1bd253ae-3de7-42de-81e5-b450c1fb8e8b` remained unchanged; the two same-name records retain
their distinct birth dates and provider-scoped identity.

The existing Base Profile publisher returned `SUCCESS` for run
`4fa48daa-5b02-45eb-ad98-2fb01ee5c5f8`, considering 299 observations and publishing 1,195 claims
with 1,191 unchanged claims. Final read-only QA found 299 resolved People, 299 observation links,
one resolved review item, 1,496 Claims and 1,496 ClaimEvidence rows. Base Profile counts were
`ASSEMBLY_PARTY=299`, `ASSEMBLY_DISTRICT=299`, `ASSEMBLY_COMMITTEES=298` and
`ASSEMBLY_REELECTION=299`; the single missing committee field remained explicit.

The new Person's role and four Base Profile Claims all point through the same official Assembly
Source, SourceSnapshot and feeder observation for `H7X3372O`. Subject-XOR invalid count,
ClaimEvidence provenance mismatch count, forbidden normalized contact-field count, fulltext row
count and provider-key-as-Person-ID count were all `0`. Existing ALIO remained one Organization,
15 observations and two organization Claims.

The public staging Web rendered `299 resolved identities`. Both the existing candidate profile
and the reviewed distinct profile opened separately; the latter showed the canonical identity,
Assembly role, four Base Profile fields and visible Evidence traces. No raw normalized provider
payload or contact fields appeared. This is staging/browser evidence, not a production coverage
or publication claim. The private tunnel was closed and Railway reported zero registered SSH keys
after verification.

## Acceptance gates

- Automatic full-enumeration output remains the four existing actions and the open conflict is
  never materialized by a routine roster run.
- The reviewed transaction is limited to the exact Assembly current-roster review and a current
  successful checkpoint manifest.
- Person/Organization subject XOR, SourcePolicy eligibility and exact snapshot/observation
  provenance remain valid.
- The transaction is atomic and idempotent; stale immutable versions and malformed review state
  fail closed.
- Existing ALIO Organization/Claim/MONEY data and all existing regressions remain intact.
- No new feeder, generic review framework, raw payload store, schema migration, public mutation
  endpoint, BTIS import or R&D runtime dependency is introduced.

## Next after closure

After this slice is closed with local, CI, staging and browser evidence, the next implementation
milestone is the existing Evidence Directory read-model path. It must continue to consume
canonical public People and Claims rather than raw feeder observations.

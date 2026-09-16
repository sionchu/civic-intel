# Assembly reviewed distinct-Person resolution v1

Status: in progress — one source-specific operator resolution for the current Assembly roster
conflict.

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

- [ ] Capture a fresh provider-independent logical staging backup outside the repository before
      any database write; no Railway plan/resource change is allowed.
- [ ] Deploy the pushed code to the existing staging API service only.
- [ ] Resolve the exact review item through the explicit source-specific CLI operation.
- [ ] Run the existing successful-roster Base Profile publisher for the newly linked observation.
- [ ] Read-only verify counts, candidate preservation, review status, exact Claim/Evidence/
      Source/Snapshot provenance, subject XOR and privacy gates.

### M2 — staging/API/browser evidence

- [ ] Verify `/people` exposes the new resolved Person and the existing candidate separately.
- [ ] Verify the new profile shows only canonical Claim/Evidence output and the four Base Profile
      fields; raw normalized provider payload and contact fields remain absent.
- [ ] Record staging/browser evidence separately from CI, release and production claims.

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

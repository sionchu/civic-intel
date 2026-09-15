# Assembly Person Bootstrap v1

Status: active — M0–M4 implementation and staging data proof are complete; post-push deployed
Web smoke and CI closure remain in the delivery loop.

## Objective

Use the existing National Assembly current-roster L3 lane to enumerate the provider-declared
complete current roster in staging, then use the existing source-specific materialization gate to
bootstrap resolved canonical People and their evidence-backed roster role claims.

```text
official current roster API
 -> successful unfiltered full enumeration
 -> SourceRun / SourceCheckpoint / SourceSnapshot / FeederObservation
 -> existing Assembly materialization decision
 -> resolved Person or explicit review/conflict queue
 -> Claim / ClaimEvidence / Source provenance
 -> existing /people and /people/{id} reads
```

The existing `workers/assembly_roster.py`, `OpenAssemblyMemberConnector`, shared repository and
`packages.verification.materialization` rules are the only implementation foundation. This plan
does not create a second batch runner, identity resolver, raw-payload store, crosswalk table,
Person schema or UI bypass.

## Identity and publication rules

- `MONA_CD` is a provider identity in the National Assembly namespace. It is not `Person.id`.
- A provider identity may support only the existing source-specific `AUTO_CREATE` / `AUTO_LINK`
  rules. Name-only linking, fuzzy matching, similarity scores and asset/row keys as Person IDs are
  prohibited.
- `REVIEW_REQUIRED` and `HARD_CONFLICT` remain explicit outcomes and create/retain the existing
  identity review queue. They are not silently converted to People or public Claims.
- Materialization is permitted only from the exact observation IDs of a `SUCCESS` full
  `national_assembly_members` / `current_member_roster` enumeration. Failed or partial runs never
  materialize.
- Published output continues through `Claim → ClaimEvidence → Source → SourcePolicy`, with the
  exact `SourceSnapshot` and `FeederObservation` retained. Raw party, district or committee
  payload fields must not be rendered by a parallel UI path.

## Milestones and gates

### M0 — staging safety baseline

- [x] Capture a current provider-independent logical backup/restore receipt for staging after the
      completed ALIO smoke and before Assembly writes. Keep dump and restore target outside the
      repository; never record credentials, passwords or a full database URL.
- [x] Read-only verify staging Alembic head, existing ALIO Organization/Claim/MONEY baseline and
      no unexpected schema/resource change.
- [x] Do not reset, drop, migrate or overwrite staging. Use an existing private tunnel or an
      already available disposable local PostgreSQL restore target; create no paid resource.

M0 evidence (2026-09-15): a `pg_dump --format=custom --no-owner` capture was created at
`2026-09-15T08:29:56.2862488Z` in a private temp path outside the repository. The dump size was
`64,744` bytes and its SHA-256 was
`9D941BCC4476D3906747019753CF895A2529FCCFA797685007285C279C5C621E`. It was restored with
`pg_restore --format=custom --no-owner --exit-on-error` into loopback-only disposable PostgreSQL
`18.6` database `restore_target` in `0.351` seconds. Read-only comparison of staging and restored
databases matched Alembic head `0006`, all 26 public tables, the ALIO Organization/Claim/MONEY
baseline (`1` Organization, `15` observations, `2` Claims, `2` ClaimEvidence), and zero
subject-XOR/provenance mismatches. No provider plan/resource, database reset/drop/migration or paid
resource was used.

### M1 — complete current-roster enumeration

- [x] Run the existing unfiltered Assembly enumerator against staging with the official API key
      supplied only through the process environment.
- [x] Require provider-declared total, page metadata, expected page count, complete page coverage,
      unique `MONA_CD` keys, deterministic page fingerprints and committed observation IDs.
- [x] Record the `SourceRun`, `SourceCheckpoint`, source/snapshot provenance and run counters.
- [x] If the run is not `SUCCESS`, retain the fail-closed run/queue state and do not materialize.

M1 evidence (2026-09-15): the existing unfiltered worker completed run
`4fa48daa-5b02-45eb-ad98-2fb01ee5c5f8` with `status=SUCCESS`, three committed pages, provider
`list_total_count=299`, `records_seen=299`, `observations_created=299` and
`observations_unchanged=0`. The checkpoint cursor was `3` with page size `100` and expected page
count `3`; the 299 provider keys and 299 external-ID links were distinct and complete. No
materialization was attempted until this successful enumeration was committed.

### M2 — source-specific Person materialization

- [x] Only after M1 `SUCCESS`, invoke the existing `enumerate_and_materialize()` path for the
      exact successful observation set.
- [x] Record counts for `AUTO_CREATE`, `AUTO_LINK`, `REVIEW_REQUIRED` and `HARD_CONFLICT`, plus
      all open review item IDs and reasons.
- [x] Verify resolved People are canonical rows whose IDs differ from provider `MONA_CD` values;
      preserve exact provider identity in source-scoped external IDs/links.
- [x] Verify materialization idempotency and no partial Person/Claim/Evidence/Link state on a
      publication or identity-gate failure using existing regressions and staging read QA.

M2 evidence (2026-09-15): the same successful run materialized 298 canonical People with
`AUTO_CREATE=298`, `AUTO_LINK=0`, `REVIEW_REQUIRED=0` and `HARD_CONFLICT=1`. The single open
review item is `b0b404b2-4c23-4577-8678-c9047cac7fe6` with reason
`EXACT_BIRTH_DATE_CONFLICT`; it was not published as a Person or Claim. Read-only staging QA
found 299 observations, 298 Person links, 298 roster Claims and 298 ClaimEvidence rows; all 299
provider IDs were retained as source-scoped external IDs, no provider key equalled a Person ID,
and no Assembly fulltext or forbidden normalized contact key was stored. Subject-XOR and
ClaimEvidence provenance mismatch counts were both zero.

### M3 — public read smoke

- [x] Read staging `/people` and an actual resolved `/people/{id}` through the existing API/web
      contract. Confirm the roster is no longer an empty placeholder and the profile shows only
      evidence-backed canonical output.
- [x] Confirm exact ClaimEvidence/source/snapshot/observation provenance is reachable through the
      existing read path and raw provider party/district/committee payload is not a UI side door.
- [x] Separate staging/browser evidence from published release and deployed coverage claims.

M3 evidence (2026-09-15): the staging Web browser smoke rendered `298 resolved identities` in the
public roster and opened resolved profile `/people/017b6ddd-e52a-4221-b1fd-e7d0999c81a8` for
`이상휘`. The profile displayed the canonical identity, one evidence-backed `HELD_ROLE` career
entry and its `Evidence trace` to the official Assembly API Source; it did not render raw party,
district or committee payload fields. The source panel exposed the policy state and official URL,
while the exact snapshot/observation identifiers remained in the audit trace. This is staging
browser evidence only, not a production release or a public coverage claim.

### M4 — small Person Base Profile v1 slice

Only after M1–M3 pass, evaluate and implement the smallest source-specific roster projection for
`party`, `district`, `committees` and `reelection` when each field has atomic Claim/Evidence or an
existing canonical semantic. Do not create a generic profile/financial framework. Preserve field-
level provenance, explicit missingness and source/version boundaries; do not infer absent values.
The result must be a separate coherent slice and must not expose raw normalized provider payload.

- [x] Build only the four source-specific field Claims from the latest successful complete-roster
      manifest; keep `MONA_CD` source-scoped and retain exact snapshot/observation provenance.
- [x] Import Claims and ClaimEvidence through one shared repository transaction, make reruns
      idempotent, and fail closed when an immutable newer observation would conflict with a current
      field Claim.
- [x] Project the fields through the existing profile read model as `AVAILABLE`/`PARTIAL`/`UNKNOWN`
      without adding raw normalized payload or direct provider-field API/UI bypasses.
- [x] Record missing-field counts, skipped review/conflict observations and the resulting staging
      Claim/Evidence counts.

M4 evidence (2026-09-15): the source-specific publisher consumed the exact successful run
`4fa48daa-5b02-45eb-ad98-2fb01ee5c5f8` and considered 299 observations. It published 1,191
current Assembly base-profile Claims and one ClaimEvidence per Claim for 298 resolved People;
`committees` was absent for one source row and one `HARD_CONFLICT` observation was skipped with
its existing open review item preserved. The final read-only staging QA found field counts of
`party=298`, `district=298`, `committees=297`, `reelection=298`, 1,191 ClaimEvidence rows, zero
subject-XOR violations, zero provenance mismatches, zero fulltext snapshots and zero forbidden
normalized contact fields. The publisher's idempotent recovery output reported
`observations_considered=299`, `observations_published=298`, `published_claims=1,191` and
`missing_field_counts={"committees":1}`; the non-zero unchanged count reflects an earlier
per-observation retry that had already committed a subset before its tunnel failed, after which
the batch transaction completed the remaining Claims without overwriting them.

The implementation adds no table, migration, dependency or generic profile framework. The local
regressions cover atomic provenance, idempotent rerun, explicit missingness and immutable version
conflict. Python full verification passed with `345 passed, 1 skipped`; Ruff, mypy, Golden quality,
web lint/typecheck/UI tests, production build and standalone artifact checks also passed. The
staging Web deployment used for the earlier M3 smoke predates this M4 code, so the new profile
section is not counted as deployed/browser evidence until the post-push deployment smoke.

## Acceptance and verification

- Staging backup/restore receipt exists before Assembly writes and the original database is not
  dropped, reset or migrated by this plan.
- The Assembly run is `SUCCESS` with a provider-declared complete roster; a partial/failed run has
  zero materialization writes attributable to that attempt.
- Materialization outcome counts and review queue are recorded; all four existing decision classes
  retain their current semantics.
- `/people` contains actual `RESOLVED` canonical People after a successful bootstrap, while no
  provider key is used as a canonical Person ID and no name-only merge occurs.
- Existing ALIO reviewed Organization Claim/MONEY result remains intact and exact provenance checks
  remain clean.
- Targeted Assembly/materialization/API/profile checks, full local verification, diff review and
  actual GitHub Actions Verify results are recorded separately. `make verify` availability is not
  assumed.

## Out of scope and deferred candidates

- No new feeder, source-gate, OpenWatch ingestion, BTIS/국외출장연수정보시스템 crawling/import,
  or repeated ALIO/MPM/CleanEye investigation is part of this plan.
- BTIS/국외출장연수정보시스템 may be documented as a later source candidate only after this
  milestone sequence; no runtime dependency is permitted here.
- MiroFish, OASIS and BettaFish remain R&D references only and must not become runtime
  dependencies.
- No admin, community, issue, contribution, local-council or UI expansion is included.

## Delivery loop

Close each milestone with regression → smallest change → targeted verification → full verification
→ diff/Clean-v0 audit → coherent commit/push → actual CI head/result. Stop and report a blocker if
the provider key is unavailable, backup/restore cannot be completed without cost, the source no
longer declares complete coverage, or any identity/provenance gate fails.

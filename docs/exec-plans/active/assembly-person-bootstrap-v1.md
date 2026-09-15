# Assembly Person Bootstrap v1

Status: active — plan established after the ALIO reviewed Organization Claim/MONEY milestone
closed at `b8b23984de5aad4ce762afbd528558a25a764116` on 2026-09-15.

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

- [ ] Capture a current provider-independent logical backup/restore receipt for staging after the
      completed ALIO smoke and before Assembly writes. Keep dump and restore target outside the
      repository; never record credentials, passwords or a full database URL.
- [ ] Read-only verify staging Alembic head, existing ALIO Organization/Claim/MONEY baseline and
      no unexpected schema/resource change.
- [ ] Do not reset, drop, migrate or overwrite staging. Use an existing private tunnel or an
      already available disposable local PostgreSQL restore target; create no paid resource.

### M1 — complete current-roster enumeration

- [ ] Run the existing unfiltered Assembly enumerator against staging with the official API key
      supplied only through the process environment.
- [ ] Require provider-declared total, page metadata, expected page count, complete page coverage,
      unique `MONA_CD` keys, deterministic page fingerprints and committed observation IDs.
- [ ] Record the `SourceRun`, `SourceCheckpoint`, source/snapshot provenance and run counters.
- [ ] If the run is not `SUCCESS`, retain the fail-closed run/queue state and do not materialize.

### M2 — source-specific Person materialization

- [ ] Only after M1 `SUCCESS`, invoke the existing `enumerate_and_materialize()` path for the
      exact successful observation set.
- [ ] Record counts for `AUTO_CREATE`, `AUTO_LINK`, `REVIEW_REQUIRED` and `HARD_CONFLICT`, plus
      all open review item IDs and reasons.
- [ ] Verify resolved People are canonical rows whose IDs differ from provider `MONA_CD` values;
      preserve exact provider identity in source-scoped external IDs/links.
- [ ] Verify materialization idempotency and no partial Person/Claim/Evidence/Link state on a
      publication or identity-gate failure using existing regressions and staging read QA.

### M3 — public read smoke

- [ ] Read staging `/people` and an actual resolved `/people/{id}` through the existing API/web
      contract. Confirm the roster is no longer an empty placeholder and the profile shows only
      evidence-backed canonical output.
- [ ] Confirm exact ClaimEvidence/source/snapshot/observation provenance is reachable through the
      existing read path and raw provider party/district/committee payload is not a UI side door.
- [ ] Separate staging/browser evidence from published release and deployed coverage claims.

### M4 — small Person Base Profile v1 slice

Only after M1–M3 pass, evaluate and implement the smallest source-specific roster projection for
`party`, `district`, `committees` and `reelection` when each field has atomic Claim/Evidence or an
existing canonical semantic. Do not create a generic profile/financial framework. Preserve field-
level provenance, explicit missingness and source/version boundaries; do not infer absent values.
The result must be a separate coherent slice and must not expose raw normalized provider payload.

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

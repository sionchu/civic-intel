# Cross-Lane Identity Candidate Pipeline v0

Status: IN_PROGRESS — implementation and focused regressions pass; full verification, CI and
staging read-only proof pending (2026-09-19).

## Objective and boundary

Generate a deterministic, read-only review candidate list from the published ALIO item-4 current
executive Claims and current canonical public People. This replaces person-by-person discovery with
a bounded source-specific reduction step. It does not resolve identity, create a Person, write a
PersonObservationLink, publish a Claim, reacquire ALIO, add a feeder or expose a new API.

The completed Kim Dong-cheol packet remains the semantic calibration case only. It is not required
to appear in this current-roster candidate output and no Kim-specific materialization preflight is
part of this milestone.

## Read contract

The pipeline reuses the canonical repository reads:

1. `public_organizations()` for current public Organizations;
2. one `published_organization_claim_contexts(...)` batch for Claim/Evidence context;
3. `public_people()` for current `RESOLVED` People.

Only current published Claims with the existing ALIO item-4 predicate, source contract, source
scope and semantic scope are accepted. Candidate fields come only from published Claim qualifiers
and the Organization/Person contracts. Raw FeederObservation normalized payloads, contact fields,
masked/vacant rows and non-ALIO Claims are not loaded for candidate generation.

## Candidate contract

`packages/verification/alio_person_candidates.py` defines the immutable, non-persistent
`CrossLaneCandidatePair` and report types. The candidate key is
`(alio_claim_id, person_id)`, so distinct ALIO Claims remain distinct observations while repeated
identical keys are de-duplicated or fail closed on conflicting values.

Discovery normalization is only surrounding-whitespace stripping plus Unicode-preserving
`casefold()` exact comparison. The reason is
`EXACT_CANONICAL_NAME_OVERLAP_DISCOVERY_ONLY`; it is not identity evidence, an exact identity,
an auto-link or a score.

Each pair calls `resolve_cross_lane_identity()` with an ALIO candidate and a canonical Person
candidate and an empty evidence tuple. Every generated pair must therefore remain
`REVIEW / CONTEXT_REVIEW` with `cross_lane_bridge_evidence_missing`. Any unexpected resolution
fails closed.

## Operator command

The source-specific read-only command is:

```text
python -m workers.alio_cross_lane_identity_candidates --database-url "$DATABASE_URL"
```

It has no `--commit` path and emits deterministic JSON without timestamps, raw payloads,
credentials or private contact data.

## Maturity boundary

```text
Stage 1 — automated discovery:
exact canonical-name overlap only -> REVIEW queue

Stage 2 — reviewed evidence research:
EXTERNAL_ID / EXACT_BIRTH_DATE / OFFICIAL_BIOGRAPHY_CONTINUITY /
OFFICIAL_CAREER_CONTINUITY

Stage 3 — existing resolver:
REVIEW / RESOLVED / UNRESOLVED

Stage 4 — separate materialization decision:
not part of v0
```

Candidate generation is not identity resolution. Research-level `RESOLVED` is not permission to
merge or materialize a canonical Person.

## Verification and staging gate

Focused candidate, resolver and profile regressions pass locally. Remaining gates are full
repository verification, GitHub Verify, then one approved staging read-only command. The staging
receipt will record only safe counts: ALIO executive Claims considered, public People considered,
candidate pairs, unique executive names among candidates and unique Person IDs among candidates.
Before/after canonical People, Organizations, Claims, ClaimEvidence and PersonObservationLinks
must remain unchanged. A zero candidate count is a valid result.

## Closure

Close with `CROSS_LANE_IDENTITY_CANDIDATE_PIPELINE_V0 — PASS` only when the bounded input,
discovery-only name rule, review-only resolver behavior, deterministic output, query shape,
read-only command, staging proof, unchanged canonical counts, full verification and GitHub Verify
all pass.

## Next concrete action

After PASS, take only the small staging candidate set through reviewed official-source bridge
research and classify each as `HAS_NON_NAME_BRIDGE`, `NO_BRIDGE_FOUND` or `HARD_CONFLICT`; do not
materialize a Person.

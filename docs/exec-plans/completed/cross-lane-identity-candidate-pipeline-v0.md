# Cross-Lane Identity Candidate Pipeline v0

Status: COMPLETE — `CROSS_LANE_IDENTITY_CANDIDATE_PIPELINE_V0 — PASS` (2026-09-19).

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

## Verification and staging receipt

Focused candidate, resolver and profile regressions pass locally. Full repository verification
also passed: pytest `386 passed, 1 skipped`, Ruff, mypy, Golden quality, Web lint/typecheck/UI
`11/11`, production build, standalone contract check and Markdown link validation. GitHub Verify
`35368004198` passed for commit `e188cafc736351b507873d1b9ba9bddc9b31955b`.

The single staging proof ran in private ephemeral Sandbox `a6e61745-b303-412b-85cf-4f16b7b9fd94`
in `us-west2`, using the exact commit above and the read-only command:

```text
python -m workers.alio_cross_lane_identity_candidates --database-url "$DATABASE_URL"
```

Safe receipt:

```text
status=REVIEW_ONLY
alio_executive_claims_considered=3624
public_people_considered=299
candidate_pairs=56
resolved_pairs=0
review_pairs=56
unresolved_pairs=0
unique_executive_names=40
unique_person_ids=41
```

All 56 candidates had
`EXACT_CANONICAL_NAME_OVERLAP_DISCOVERY_ONLY`; all remained
`REVIEW / CONTEXT_REVIEW` with `name_match` and
`cross_lane_bridge_evidence_missing`. No bridge research or enrichment was performed.

Before and after read-only counts were identical:

```text
schema=0006
people=299
organizations=347
claims=5466
claim_evidence=5466
subject_xor=0
alio_item4_claims=3970
alio_item4_evidence=3970
alio_executive_claims=3624
alio_executive_evidence=3624
person_observation_links=299
identity_review_items=1
```

The 3970 ALIO item-4 total includes 3624 executive disclosure Claims and 346 institution
classification Claims; only the executive disclosure contract is a candidate input. The Sandbox
was destroyed successfully and a follow-up list showed no remaining entry or running Sandbox for
the task. No staging write, importer, acquisition, migration, deployment or Railway resource
change occurred.

## Closure

Close with `CROSS_LANE_IDENTITY_CANDIDATE_PIPELINE_V0 — PASS` only when the bounded input,
discovery-only name rule, review-only resolver behavior, deterministic output, query shape,
read-only command, staging proof, unchanged canonical counts, full verification and GitHub Verify
all pass.

## Next concrete action

Proceed to `Civic Intel Governance Ontology + Gukgam 2026 Scale Collection & Visual Explorer v0`
with agent-based implementation and independent verification. Do not begin person-by-person
materialization from this candidate set.

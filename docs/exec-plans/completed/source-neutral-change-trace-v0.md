# Source-neutral derived CHANGE trace v0

Status: COMPLETED 2026-09-28.

Base: `a35678d`.

## Objective

Prove that Civic Intel's CHANGE primitive is not Assembly-specific by introducing one small,
source-neutral derived-change trace contract used by two already-existing published read models:

- Assembly historical role-display change for a Person;
- ALIO Item 12 annual business-expense change for an Organization.

This slice must not create a generic analytics framework. Source-specific comparability,
coverage, correction semantics and numerical/text interpretation remain in their existing
renderers.
## Scope

Add one rendering-layer helper that records only the invariants shared by both concrete cases:

- both inputs are current PUBLISHED FACT Claims asserted true;
- both Claims target the same canonical Person or Organization;
- each input retains its exact ClaimEvidence references;
- REFUTE evidence blocks the derived trace and SUPPORT evidence is required;
- caller-supplied order keys and values are retained without interpreting their domain meaning;
- the trace emits a deterministic source-neutral trace key, Claim IDs, Evidence IDs and Source IDs.

The existing public Assembly CHANGE and ALIO MONEY top-level IDs/method versions remain unchanged.
The new trace is additive metadata under each derived result.
## Non-goals

- no new source, collection run, Claim, Person or Organization;
- no new API route or schema/migration;
- no automatic comparison of arbitrary Claims;
- no inference that money movement is good/bad, waste, wrongdoing or performance;
- no reinterpretation of Assembly role text;
- no generic scoring, ranking, event framework or time-series engine.

## Acceptance

- the common module contains no Assembly, ALIO, Gukgam, election or year-specific constants;
- existing source-specific validation remains in the existing renderers;
- Assembly and ALIO outputs preserve their current top-level IDs and existing fields;
- both outputs include the same `SOURCE_NEUTRAL_DERIVED_CHANGE_TRACE_V1` contract;
- focused unit/regression tests prove same-subject/public-FACT/evidence gates and both concrete uses;
- current Mac PostgreSQL organization MONEY response is unchanged except for the additive trace;
- full `make verify` passes;
- no operational DB write, source fetch, publication or deployment occurs in implementation.

## Closure evidence

- Added `SOURCE_NEUTRAL_DERIVED_CHANGE_TRACE_V1` with no source, season or provider constants.
- Assembly historical Person CHANGE and ALIO Item 12 Organization MONEY both emit the same trace
  contract while retaining their source-specific comparability and interpretation rules.
- Operational Mac PostgreSQL C0908 MONEY output preserved its existing ID, values and all prior
  fields byte-for-byte after removing only the additive `details.change_trace`.
- Focused tests cover deterministic output, same-subject enforcement, PUBLISHED FACT gating,
  REFUTE rejection and SUPPORT requirement, plus both concrete integrations.
- Full repository verification passed: `643 passed / 3 skipped`, Golden Set PASS, Web `26/26`,
  and the Next standalone production build completed.
- No source fetch, operational DB write, Claim publication, schema change or deployment occurred.

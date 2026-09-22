# org.go Organization Proposal v0

Status: COMPLETE — review-only proposal slice closed; no Organization or Claim writes.

## Objective

Build a deterministic review artifact for org.go provider rows whose exact provider name equals a
current Gukgam `NO_EXACT_CANONICAL_NAME_OVERLAP` target label. This slice prepares review
evidence only. It does not materialize Organizations or publish Gukgam targets.

## Baseline

```text
canonical base: 1deb820ac1d4fef2d0b15bfce4e3b1f8f8c98cb4
current Organizations: 347
Claims: 5576
ClaimEvidence: 5576
org.go live provider rows: 63
Gukgam review items: 390
```

## Proposal contract

- match rule: exact provider-name equality to a current Gukgam `NO_EXACT` label only;
- current Organization universe count must equal the universe used by the Gukgam review;
- any current canonical exact-name conflict fails closed;
- duplicate provider code or provider name fails closed;
- a `NO_EXACT` item that unexpectedly contains candidates fails closed;
- no alias expansion, fuzzy similarity, ranking, embeddings or organizational-proximity matching;
- no Organization write, Claim/ClaimEvidence write, binding or publication.

## Live receipt

A reviewed live run on 2026-09-22 produced:

```text
current Organizations: 347
provider rows: 63
Gukgam review items: 390
proposal_count: 27
Gukgam occurrence_count: 41
canonical_name_conflict_count: 0
```

The normalized proposal core reproduced byte-for-byte across repeated runs when transport-only page
hashes were excluded.

```text
proposal core SHA-256:
e0c0a6e39cf0844c3b653bd7884356dff5cca56d78044888fe111940a4f9d194
```

Normalized review artifact:

`docs/research/gukgam_2026_orggo_organization_proposal_2026-09-22.json`

Post-run read-only counts remained Organizations `347`, Claims `5576`, ClaimEvidence `5576`.

## Verification

- targeted Ruff: PASS;
- targeted mypy: PASS;
- proposal regression: `5/5` PASS;
- full repository verification: `503 passed, 1 skipped`; Golden Set `passed: true`;
- no DB write path exists in the proposal module;
- live proposal generation performed read-only DB access and provider HTTP fetches only.

## Next boundary

A separate materialization contract may consume this reviewed proposal later, but it must require an
explicit reviewed manifest, re-check current canonical Organization conflicts, create no duplicate
Organization names/codes, and must not publish Gukgam Claims in the same slice.

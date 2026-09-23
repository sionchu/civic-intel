# org.go Reviewed Organization Materialization v0

Status: COMPLETE — explicit manifest contract + staging dry-run proof; no staging write in this slice.

## Objective

Materialize only reviewed org.go Organization proposals through an explicit operator manifest, while
keeping Gukgam Claim publication in a separate later slice.

## Contract

- schema: `civic.orggo.reviewed_organization_manifest.v1`
- reviewed proposal SHA: `e0c0a6e39cf0844c3b653bd7884356dff5cca56d78044888fe111940a4f9d194`
- reviewed manifest SHA: `f2a455a7b4f2271d73a5fb329af5dbc608aa5ebbe7938f46b55d05d84e64b6ab`
- items: `27`
- deterministic Organization ID: UUIDv5 of provider `org_code` in a source-specific namespace
- exact provider fields are binding: name/category/orgCode/chartId/source locator
- same-name canonical conflicts and deterministic-ID/name collisions fail closed
- unrelated Organization-universe drift fails closed
- partial materialization state fails closed at commit preparation
- commit requires exact expected manifest SHA plus explicit `--commit`
- Organization import is atomic and Claim-free
- no candidate enumeration, fuzzy/alias/embedding matching, network fetch or Gukgam publication

## Staging dry-run receipt

Two unchanged no-write staging preflights were byte-identical:

```text
current Organizations: 347
Claims: 5576
ClaimEvidence: 5576
items: 27
to create: 27
to reuse: 0
write_performed: false
automatic_candidate_enumeration: false
gukgam_claim_publication: false
network_fetch: false
receipt SHA-256: 0d97de2dfc03676acee83a855facbdbff32704a9e6486e2aeb5a60fbd043e332
```

Post-dry-run counts remained `347 / 5576 / 5576`.

## Verification

Targeted Ruff/mypy passed and materialization regression passed `8/8`. Full repository verification passed `511` tests with `1` skipped and Golden Set `passed: true`; Web lint/typecheck/test passed `23/23`. GitHub Verify remains the final Linux/deployment artifact merge gate.

## Next boundary

After this contract is merged, a separate staging commit slice may recreate only the exact 27-item
manifest and proposal, require the same fresh preflight receipt and exact manifest SHA, and execute
one Organization-only atomic commit. No Gukgam Claim may be published in that slice.

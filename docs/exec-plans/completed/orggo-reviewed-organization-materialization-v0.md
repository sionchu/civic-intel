# org.go Reviewed Organization Materialization v0

Status: COMPLETE — explicit manifest contract, dry-run proof and Organization-only operational commit; no Gukgam Claim publication.

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

## Operational closure — 2026-09-28

- The Mac staging/data PostgreSQL copy was restored at schema `0008` from the verified
  post-Assembly/OpenDART baseline and then completed the MOIS current Organization-code lane at
  `133930 / 133930`, checkpoint `134 / 134`, latest run `SUCCESS`.
- Before the org.go mutation, the exact 27-item manifest
  `f2a455a7b4f2271d73a5fb329af5dbc608aa5ebbe7938f46b55d05d84e64b6ab` was re-preflighted
  twice against the Mac database. The LF receipt SHA was
  `ff3add8f74358418bbd251cd5e35781db33f4b425b83457416a324a259443b91`; converting that
  single JSON line to the historical Windows CRLF form reproduced the canonical staging receipt
  `0d97de2dfc03676acee83a855facbdbff32704a9e6486e2aeb5a60fbd043e332` byte-for-byte.
- One explicit Organization-only atomic commit returned `COMMITTED`, `item_count=27`,
  `organizations_created=27`, `organizations_reused=0`, `write_performed=true`,
  `automatic_candidate_enumeration=false`, `gukgam_claim_publication=false` and
  `network_fetch=false`. The commit receipt SHA is
  `d60279879d412dc1be2f36b7fd3ffb81423ae1135eead4c91eb5fecb04897982`.
- Post-commit counts were Organizations `374`, People `9120`, Claims/ClaimEvidence
  `14397/14397`, Gukgam observations `57` and Gukgam source runs `14`. Public Claim-backed
  Gukgam targets remained `110`; this slice created no Claim or ClaimEvidence.
- A fresh read-only binding review now has `151` exact-one mentions and `239` no-exact
  mentions across the same `390` total mentions. The new org.go materialization accounts for
  exactly `41` exact-one mentions across `27` Organizations. These are review candidates only.

## Next boundary

Do not convert the new `41` exact-one occurrences into a reviewed Claim batch automatically.
An operator must explicitly review and confirm the exact `review_key ↔ Organization` pairs before
the canonical reviewed Gukgam batch manifest/preflight/commit path is used. Claim publication remains
a separate atomic slice.

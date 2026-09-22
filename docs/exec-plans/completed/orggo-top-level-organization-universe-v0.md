# org.go Top-Level Organization Universe v0

Status: COMPLETE — credential-free L2 source slice closed; no canonical materialization.

## Objective

Add a conservative official Organization-universe source for the remaining Gukgam `NO_EXACT`
coverage without deriving Organization identity from Gukgam text. The source is the MOIS
Government Organization Management System institution-chart list at `www.org.go.kr`.

## Baseline

```text
master/origin master at start: 44acaa0df49a6b2e799991e0e4234ba62dd98fe3
canonical Organizations: 347
public Gukgam targets: 110 across 6 committees
Gukgam NO_EXACT: 280 mentions / 256 distinct labels
MOIS credential: absent
```

## Contract

- provider Organization key: seven-digit `orgCode`;
- provider detail locator: `chartId`;
- provider category retained verbatim;
- list pagination: `pageIndex` only;
- metadata-only retention; raw/fulltext/excerpts/AI/commercialization disabled;
- no Organization creation, Claim creation or Gukgam binding.

## Verification receipt

Fixture contract:

- targeted Ruff passed;
- targeted mypy passed;
- connector regression passed `9/9` before live proof;
- full repository verification after final source/docs changes passed `498` tests with `1` skipped and Golden Set `passed: true`;
- Web lint/typecheck/test passed with `23/23`; Next production build compiled, typechecked, generated all routes and static pages successfully before the known Windows process-exit anomaly. GitHub Verify remains the final Linux/deployment artifact gate;
- malformed subject locator, duplicate `orgCode`, missing/ambiguous total count and row-count overflow all fail closed.

Live credential-free proof on 2026-09-22:

```text
provider total: 63
pages: 7
page row counts: 10 / 10 / 10 / 10 / 10 / 10 / 3
distinct orgCode: 63
distinct names: 63
categories: 중앙행정기관 49 / 중앙행정기관에 준하는 기관 8 / 헌법기관 4 / 헌법상 자문기구 1 / 기타 1
```

Page SHA-256 receipts are recorded in `ORGGO_TOP_LEVEL_ORGANIZATION_FEEDER.md`.

Exact-name planning comparison against the current Gukgam `NO_EXACT` universe found `27` distinct
label overlaps covering `41` occurrences. This is planning evidence only; it created no canonical
Organization, Claim or publication.

## Maturity decision

This lane closes at **L2 SINGLE_PULL**. The live connector is proven, but no persistent
SourceRun/checkpoint/resume/idempotent enumeration contract exists. A later L3 slice must implement
those operational guarantees explicitly.

## Next boundary

If continued, build a **review-only Organization proposal** from org.go rows whose exact provider
name equals a current `NO_EXACT` Gukgam target label. The proposal must preserve `orgCode`, category
and source provenance and must not auto-create Organizations or auto-publish Gukgam targets.

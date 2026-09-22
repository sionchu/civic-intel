# MOIS Standard Organization Code Universe v0

Status: COMPLETE — L1 contract/connector slice closed; live fetch remains `NOT_RUN` pending an approved credential.

## Objective

Stage the Ministry of the Interior and Safety Standard Organization Code API as the next canonical
Organization-universe source candidate without creating Organizations or changing Gukgam
publication semantics.

The immediate product need is the post-Gukgam coverage gap: all current exact-one reviewed
occurrences are published, while `280` remaining Gukgam mentions are `NO_EXACT`. This plan does
not turn those mentions into Organizations. It establishes an independent official Organization
source whose provider keys and lifecycle fields can support later reviewed materialization.

## Baseline

```text
master/origin/master at start: ca81a34726972d20b46c32d7ccaaa77f748e9d7f
canonical Organizations: 347
public Gukgam targets: 110 across 6 committees
Gukgam unpublished exact-one: 0
Gukgam NO_EXACT: 280 mentions / 256 distinct labels
current staging/host MOIS_ORG_CODE_API_KEY: absent
```

## Governing source contract

Official source reviewed on 2026-09-22:

```text
data.go.kr dataset: 15077870
endpoint: https://apis.data.go.kr/1741000/StanOrgCd2/getStanOrgCdList2
provider record key: org_cd
current-only selector: stop_selt=0
pagination: pageNo / numOfRows / totalCount
license: 이용허락범위 제한 없음
development approval: automatic
operation approval: automatic
```

The API exposes current institutions only at the dataset level and carries hierarchy/lifecycle
fields including `high_cd`, `highst_cd`, `rep_cd`, `crt_de`, `chg_de`, `base_date`, `adpt_date`,
`cls_de`, `stop_selt` and `preorg_cd`.

## Milestone A — contract and connector

- [x] review official catalog, operation, fields, traffic and license
- [x] compare org.go top-level institutions against current Gukgam NO_EXACT labels
- [x] prove 27 distinct / 41 occurrence exact-name planning overlap
- [x] define source-specific credential variable and no-secret persistence rule
- [x] implement SourcePolicy and typed connector record
- [x] validate current-only discovery URL and allowed filters
- [x] inject `ServiceKey` only at request time
- [x] parse JSON response and provider pagination metadata
- [x] validate `org_cd` and lifecycle/status fields
- [x] add deterministic redaction/error/parser tests

## Milestone B — verification and closure

- [x] targeted connector tests pass
- [x] ruff and mypy pass
- [x] full repository pytest/quality pass (`489 passed, 1 skipped`; Golden Set passed)
- [x] Web lint/typecheck/test/build remain unchanged and pass; GitHub Verify remains the final merge gate
- [x] relative documentation links pass
- [x] source coverage and parser inventory docs reference the new L1 lane
- [x] live fetch explicitly recorded `NOT_RUN` while key is absent
- [x] no worker, migration, Organization row, Claim or Gukgam binding added

## Closure receipt

- Targeted MOIS connector regression passed `15/15`; Ruff and mypy passed.
- Full repository verification after the final fail-closed parser changes passed `489` tests with `1` skipped; Golden Set returned `passed: true`.
- Web source files were unchanged by this slice. The existing branch-wide Web lint/typecheck/test/build verification passed; GitHub Verify is required before merge to close the Linux/deployment artifact gate.
- Staging and operator host both lack `MOIS_ORG_CODE_API_KEY`; live fetch remains `NOT_RUN` and no secret was created, requested or persisted.
- Exact-name planning comparison indicates this source could potentially cover `27` distinct current Gukgam `NO_EXACT` labels / `41` occurrences, but no Organization row, Claim, binding or publication was created.
- Parser semantics fail closed on malformed row lists and malformed pagination metadata; provider `use_cd` is retained only as `use_code` without stronger inferred meaning.

## Out of scope

This slice must not:

- request or expose a production/public-data credential;
- create `Organization` rows or a second Organization table;
- add fuzzy/alias/embedding matching;
- bind Gukgam `NO_EXACT` rows automatically;
- create Gukgam Claims from imported Organization records;
- claim L2/L3 without a credentialed live receipt and separate approval;
- create production Railway resources or enable indexing.

## Stop condition

Stop when the source-specific connector contract is deterministic and fully tested against fixtures,
all verification passes, and documentation records the exact L1 ceiling. The next slice, if later
approved and credentialed, is a bounded live `stop_selt=0` pull plus review-only Organization
proposal; it is not automatic materialization.

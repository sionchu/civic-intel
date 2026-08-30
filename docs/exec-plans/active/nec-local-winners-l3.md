# NEC local elected-office winner L3

Status: active — baseline and official source contract verified on 2026-08-31.

## Objective

Promote the Central Election Commission local elected-office winner source from L2
single-pull staging to L3 full enumeration on the existing canonical batch foundation.

This plan is limited to one bounded winner universe:

```text
(election_id, local election type)
```

It does not convert all NEC endpoints, add scheduling, redesign the UI or build a generic
batch framework.

## Governing source contract

Official source reviewed on 2026-08-31:

```text
catalog: https://www.data.go.kr/data/15000864/openapi.do
endpoint: https://apis.data.go.kr/9760000/WinnerInfoInqireService2/getWinnerInfoInqire
```

Required bounded inputs:

```text
sgId
sgTypecode
```

Pagination:

```text
pageNo
numOfRows
totalCount
```

Stable provider record key:

```text
huboid
```

Full L3 enumeration must not use optional `sdName` or `sggName` filters.

Official conditions:

- development traffic: 10,000 requests;
- operational account: review approval;
- license: 이용허락범위 제한 없음;
- final results may appear after provider transfer/validation, normally within two months.

## Privacy and semantics

The provider exposes an address. It must never enter the connector record, normalized
observation, source metadata, errors or snapshots.

Allowed winner fields:

```text
huboid
sgId
sgTypecode
sggName
sdName
wiwName
giho
gihoSangse
jdName
name
hanjaName
birthday
job
edu
career1
career2
dugsu
dugyul
```

Education, job and career strings remain candidate-submitted election disclosure, not
independently verified biography facts.

An L3 observation may carry identity hints from exact provider fields. It does not gain
automatic cross-Person merge or publication authority.

## Baseline

```text
origin/master: a56e7a665ce6de5bd12b11c75cbdc57ed4f40ffa
local starting HEAD: 0dec62ff208937fbe97673a1ceb56e234ef05bd6
Alembic head: 0004
existing NEC targeted tests: 8 passed, 1 cache warning
live NEC key: unavailable on this host; live fetch is NOT_RUN
```

## Milestone A — Contract and connector hardening

- [x] read governing repository documents and batch skill
- [x] inspect existing NEC connector/stager/tests
- [x] verify current official endpoint
- [x] verify current request/response fields
- [x] verify traffic/license conditions
- [x] confirm `huboid` provider key
- [x] confirm unfiltered `(sgId, sgTypecode)` bounded scope
- [ ] update SourcePolicy review evidence
- [ ] retain provider page/size response metadata
- [ ] expand privacy-minimized winner record fields
- [ ] preserve existing single-pull stager behavior

## Milestone B — Winner L3 enumeration

- [ ] define feeder, scope key, semantic scope and source contract
- [ ] reject province/district/party-filtered enumeration
- [ ] full pagination from page 1
- [ ] validate provider page/size echo
- [ ] validate stable total count and expected pages
- [ ] validate expected page row counts
- [ ] detect duplicate page content
- [ ] detect duplicate/conflicting `huboid`
- [ ] persist SourceRun/SourceCheckpoint/FeederObservation
- [ ] commit page and checkpoint atomically
- [ ] support PARTIAL and resume
- [ ] unchanged rerun no-op
- [ ] changed winner row creates immutable observation
- [ ] keep identity/materialization/publication boundaries
- [ ] add CLI entrypoint without breaking staging CLI

## Milestone C — Verification and closure

- [ ] deterministic multi-page test
- [ ] unchanged rerun test
- [ ] changed row test
- [ ] failed page/resume test
- [ ] total/page mismatch tests
- [ ] duplicate/conflicting key tests
- [ ] policy denial before network
- [ ] credential absent from persistence/errors
- [ ] address/contact absent from persistence
- [ ] zero-result bounded scope test
- [ ] existing NEC staging regression
- [ ] full Python verification
- [ ] web verification
- [ ] Alembic roundtrip
- [ ] inspect clean-v0 diff
- [ ] update feeder maturity to L3
- [ ] record live fetch as NOT_RUN when key remains unavailable

## Stop condition

Stop when the NEC winner roster for one unfiltered `(election_id, sgTypecode)` scope has:

1. complete deterministic pagination and coverage validation;
2. persistent run/checkpoint/observation state;
3. atomic resume and idempotent version behavior;
4. exact `huboid` identity hints without address persistence;
5. existing staging semantics preserved;
6. full local verification and migration roundtrip completed;
7. no second repository, raw store, generic framework or materialization bypass.

## Evidence

Update with commands and observed results during implementation.

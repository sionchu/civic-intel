# NEC local elected-office winner L3

Status: completed — stop condition met locally on 2026-08-31.

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
- [x] update SourcePolicy review evidence
- [x] retain provider page/size response metadata
- [x] expand privacy-minimized winner record fields
- [x] preserve existing single-pull stager behavior

## Milestone B — Winner L3 enumeration

- [x] define feeder, scope key, semantic scope and source contract
- [x] reject province/district/party-filtered enumeration
- [x] full pagination from page 1
- [x] validate provider page/size echo
- [x] validate stable total count and expected pages
- [x] validate expected page row counts
- [x] detect duplicate page content
- [x] detect duplicate/conflicting `huboid`
- [x] persist SourceRun/SourceCheckpoint/FeederObservation
- [x] commit page and checkpoint atomically
- [x] support PARTIAL and resume
- [x] unchanged rerun no-op
- [x] changed winner row creates immutable observation
- [x] keep identity/materialization/publication boundaries
- [x] add CLI entrypoint without breaking staging CLI

## Milestone C — Verification and closure

- [x] deterministic multi-page test
- [x] unchanged rerun test
- [x] changed row test
- [x] failed page/resume test
- [x] total/page mismatch tests
- [x] duplicate/conflicting key tests
- [x] policy denial before network
- [x] credential absent from persistence/errors
- [x] address/contact absent from persistence
- [x] zero-result bounded scope test
- [x] existing NEC staging regression
- [x] full Python verification
- [x] web verification
- [x] Alembic roundtrip
- [x] inspect clean-v0 diff
- [x] update feeder maturity to L3
- [x] record live fetch as NOT_RUN when key remains unavailable

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

Official contract review on 2026-08-31:

- data.go.kr catalog `15000864` and the exact
  `WinnerInfoInqireService2/getWinnerInfoInqire` operation were reviewed;
- the catalog documents required `sgId`/`sgTypecode`, provider pagination,
  `huboid`, a 10,000-request development allowance, reviewed operational access and
  이용허락범위 제한 없음;
- the provider address field is intentionally omitted from the connector record and all
  persisted observation data.

Implementation:

```text
074b14e P0 docs: define NEC local winner L3 plan
43d251a P0: add resumable NEC local winner L3
```

Observed local verification:

```text
NEC targeted pytest: 19 passed, 1 warning
full pytest: 215 passed, 4 warnings in 55.43s
ruff: PASS
mypy: Success, 51 source files
packages.verification.quality: passed=true
apps/web lint: PASS
apps/web typecheck: PASS
apps/web tests: 2 passed
apps/web build: PASS
```

`make verify` itself is runner-unavailable on this Windows host because GNU Make is not
installed. Every underlying Makefile verification command was executed directly; this is
not recorded as a Make runner pass.

Alembic was verified against a fresh explicit temporary SQLite database:

```text
fresh upgrade -> 0004 (head)
downgrade -1 -> 0003
upgrade head -> 0004 (head)
```

Clean-v0 audit from `0dec62f` through implementation HEAD `43d251a`:

```text
SqlAlchemyRepository class definitions: 1
apps.api.repository imports: 0
parallel raw observation/payload stores: 0
generic crawler/framework additions: 0
materialization or API changes: 0
git diff --check: PASS
```

`NEC_API_KEY` is absent on this host, so a live winner fetch remains `NOT_RUN`. The
deterministic transport tests exercised pagination and redaction without persisting the
credential or provider address. Local commits were not pushed, so no CI run exists for
these commits. The latest remote baseline workflow was blocked before repository steps by
the GitHub account billing/spending limit and is not a CI pass.

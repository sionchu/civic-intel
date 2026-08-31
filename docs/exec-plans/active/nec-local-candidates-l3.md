# NEC local election candidate L3

Status: in progress.

## Objective

Promote the Central Election Commission local-election candidate source from L2
single-pull staging to L3 persistent full enumeration on the canonical batch foundation.

The bounded source universe is one unfiltered local-election scope:

```text
(sgId, sgTypecode)
```

This plan does not enumerate preliminary candidates, broaden the supported election types,
schedule synchronization, infer election outcomes, create Persons, or add a generic batch
framework.

## Priority decision

This is the next P0/P1 L3 slice because the feeder already has a reviewed official connector,
stable `huboid` row identity, exact election scope, privacy-minimized parsing and deterministic
L2 staging. The remaining maturity gap is complete pagination, persistent run/checkpoint state,
resume and immutable observations. OpenDART and NKIS remain L2 but require broader provider-
universe decisions before their complete bounded scope is equally clear.

## Governing source contract

Official sources reviewed on 2026-08-31:

```text
catalog: https://www.data.go.kr/data/15000908/openapi.do
endpoint: https://apis.data.go.kr/9760000/PofelcddInfoInqireService/getPofelcddRegistSttusInfoInqire
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

L3 enumeration must not use optional `sdName`, `sggName` or `jdName` filters. Coverage requires
the requested and provider-returned page/size, stable total count, exact expected rows, page
fingerprints and unique `huboid` coverage.

Official conditions:

- free access;
- development auto-approval and operational review approval;
- development traffic allowance of 10,000 requests;
- license: 이용허락범위 제한 없음.

## Semantics and minimization

One observation represents one official candidate-registration row in one election/type scope.
It may retain candidate identity, jurisdiction, party, ballot number, public job, submitted
education/careers and registration status.

The provider address, gender, age, provider classification IDs and raw row are excluded. Job,
education and career strings retain `candidate_submitted_election_disclosure` semantics and are
not independently verified biography facts. Registration status is the source's disclosed
status; candidate enumeration alone does not infer `WINNER`, `NOT_WINNER` or current office.

Exact `huboid` identity hints do not authorize cross-lane Person merge, materialization or direct
publication.

## Baseline

```text
origin/master: a56e7a665ce6de5bd12b11c75cbdc57ed4f40ffa
local starting HEAD: a236f35
Alembic head: 0004
existing NEC targeted tests: 19 passed, 1 cache warning
full pytest: 230 passed, 4 warnings
ruff: PASS
mypy: PASS, 51 source files
quality: passed=true
web lint/typecheck/tests/build: PASS
live NEC key: unavailable on this host; live fetch is NOT_RUN
make verify: runner unavailable because GNU Make is absent
```

## Milestone A — Contract and connector hardening

- [x] read governing repository documents and batch skill
- [x] inspect current candidate connector, stager and winner L3 implementation
- [x] verify the current official catalog and endpoint
- [x] verify access, license and traffic conditions
- [x] confirm unfiltered `(sgId, sgTypecode)` bounded scope
- [x] confirm `huboid` provider row key
- [ ] update SourcePolicy review evidence for candidate and winner APIs
- [ ] define privacy-minimized persistent candidate fields
- [ ] preserve existing candidate/winner review staging behavior

## Milestone B — Candidate L3 enumeration

- [ ] define feeder, scope key, semantic scope and source contract
- [ ] reject province/district/party-filtered enumeration
- [ ] full pagination from page 1
- [ ] validate requested and provider-returned page/size
- [ ] validate stable total count and expected pages
- [ ] validate exact expected page row counts
- [ ] validate row election id/type consistency
- [ ] detect duplicate page content
- [ ] detect duplicate/conflicting `huboid`
- [ ] persist SourceRun/SourceCheckpoint/FeederObservation
- [ ] commit each page and checkpoint atomically
- [ ] support PARTIAL and resume
- [ ] unchanged rerun no-op
- [ ] changed candidate row creates immutable observation
- [ ] keep identity/materialization/publication boundaries
- [ ] extend the existing CLI without breaking staging or winner enumeration

## Milestone C — Verification and closure

- [ ] deterministic multi-page test
- [ ] unchanged rerun test
- [ ] changed row test
- [ ] failed page/resume test
- [ ] atomic checkpoint failure test
- [ ] total/page/row mismatch tests
- [ ] duplicate/conflicting key tests
- [ ] policy denial before network/run
- [ ] credential absent from persistence/errors
- [ ] address/gender/age absent from persistence
- [ ] zero-result bounded scope test
- [ ] existing NEC staging and winner L3 regressions
- [ ] full Python verification
- [ ] web verification
- [ ] Alembic roundtrip
- [ ] inspect clean-v0 diff
- [ ] update feeder maturity to L3
- [ ] record live fetch as NOT_RUN when key remains unavailable

## Stop condition

Stop when the candidate roster for one unfiltered `(sgId, sgTypecode)` scope has:

1. complete deterministic pagination and unique `huboid` coverage;
2. persistent run/checkpoint/observation state;
3. atomic resume and idempotent immutable version behavior;
4. exact identity hints without address, gender or age persistence;
5. candidate-submitted and registration semantics preserved without outcome inference;
6. existing review staging and winner L3 behavior preserved;
7. full local verification and migration roundtrip completed;
8. no Person creation, materialization bypass, second repository/raw store or generic framework.

## Evidence

Implementation and final verification evidence will be recorded as milestones complete.

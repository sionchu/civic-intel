# NEC local election candidate L3

Status: completed — stop condition met locally on 2026-08-31.

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
- [x] update SourcePolicy review evidence for candidate and winner APIs
- [x] define privacy-minimized persistent candidate fields
- [x] preserve existing candidate/winner review staging behavior

## Milestone B — Candidate L3 enumeration

- [x] define feeder, scope key, semantic scope and source contract
- [x] reject province/district/party-filtered enumeration
- [x] full pagination from page 1
- [x] validate requested and provider-returned page/size
- [x] validate stable total count and expected pages
- [x] validate exact expected page row counts
- [x] validate row election id/type consistency
- [x] detect duplicate page content
- [x] detect duplicate/conflicting `huboid`
- [x] persist SourceRun/SourceCheckpoint/FeederObservation
- [x] commit each page and checkpoint atomically
- [x] support PARTIAL and resume
- [x] unchanged rerun no-op
- [x] changed candidate row creates immutable observation
- [x] keep identity/materialization/publication boundaries
- [x] extend the existing CLI without breaking staging or winner enumeration

## Milestone C — Verification and closure

- [x] deterministic multi-page test
- [x] unchanged rerun test
- [x] changed row test
- [x] failed page/resume test
- [x] atomic checkpoint failure test
- [x] total/page/row mismatch tests
- [x] duplicate/conflicting key tests
- [x] policy denial before network/run
- [x] credential absent from persistence/errors
- [x] address/gender/age absent from persistence
- [x] zero-result bounded scope test
- [x] existing NEC staging and winner L3 regressions
- [x] full Python verification
- [x] web verification
- [x] Alembic roundtrip
- [x] inspect clean-v0 diff
- [x] update feeder maturity to L3
- [x] record live fetch as NOT_RUN when key remains unavailable

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

Official contract review on 2026-08-31 confirmed the candidate catalog `15000908`, exact
`PofelcddInfoInqireService/getPofelcddRegistSttusInfoInqire` operation, required
`sgId`/`sgTypecode`, provider pagination, `huboid`, free access, development auto-approval,
operational review approval, a 10,000-request development allowance and 이용허락범위 제한 없음.

Implementation:

```text
5cee6a7 P0 docs: define NEC local candidate L3 plan
3e9a393 P0: add resumable NEC local candidate L3
```

Observed local verification:

```text
NEC candidate/staging/winner targeted pytest: 32 passed, 1 cache warning
full pytest: 243 passed, 4 warnings in 59.20s
ruff: All checks passed
mypy: Success, 51 source files
packages.verification.quality: passed=true
apps/web lint: PASS
apps/web typecheck: PASS
apps/web tests: 2 passed
apps/web build: PASS
```

`make verify` itself remains runner-unavailable because GNU Make is not installed on this
Windows host. Every underlying Makefile verification command was executed directly; this is not
recorded as a Make runner pass.

Migration verification:

```text
Alembic heads: 0004 (head)
tests/test_migrations.py: 1 passed
fresh upgrade -> 0004
downgrade 0004 -> 0003 -> 0002 -> 0001
re-upgrade -> 0004 while preserving a populated Person row
```

No migration was added because candidate L3 reuses the canonical 0004
SourceRun/SourceCheckpoint/FeederObservation schema.

Clean-v0 audit from starting HEAD `a236f35` through implementation HEAD `3e9a393`:

```text
SqlAlchemyRepository class definitions: 1
apps.api.repository imports: 0
schema migration changes: 0
parallel raw observation/payload stores: 0
generic crawler/framework additions: 0
Person/materialization/publication path changes: 0
dependency manifest changes: 0
git diff --check: PASS
```

`NEC_API_KEY` is absent on this host, so live candidate enumeration remains `NOT_RUN`. The
deterministic transport tests exercised full pagination, persistence, resume and redaction. Local
commits are not pushed, so no CI pass is claimed.

## Next Best Action

Define the bounded provider universe for an OpenDART executive-status L3 feeder before writing
enumeration code. The existing source is L2 and has strong filing/corporation anchors, but a
complete L3 scope must first pin the corporation-code set, fiscal/report period and provider
coverage rules rather than treating one `corp_code` pull as full enumeration.

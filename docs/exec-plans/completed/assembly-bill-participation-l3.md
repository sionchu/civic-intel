# National Assembly bill participation L3

Status: completed — stop condition met locally on 2026-08-31.

## Objective

Promote the National Assembly bill-participation feeder from L2 in-memory full-term staging
to L3 persistent full enumeration on the canonical batch foundation.

The bounded source universe is exactly one unfiltered National Assembly term:

```text
assembly_age
```

This plan does not fetch bill-detail HTML, infer proposal reasons, calculate performance or
faction scores, create a second bill database, or add a generic batch framework.

## Priority decision

This is the next P0/P1 L3 slice because the current feeder already has a reviewed official API,
an unfiltered full-term scanner, stable `BILL_ID` row identity, exact proposer member-code
fields and deterministic coverage checks. Its remaining maturity gap is persistent
run/checkpoint/resume and immutable record observations. Closing that gap directly supports
the existing exact representative/co-sponsorship semantics without a schema change.

## Governing source contract

Official sources reviewed on 2026-08-31:

```text
catalog: https://www.data.go.kr/data/15125946/openapi.do
endpoint: https://open.assembly.go.kr/portal/openapi/nzmimeepazxkubdpn
```

Required bounded input:

```text
AGE
```

Pagination:

```text
pIndex
pSize
list_total_count
```

Stable provider record key:

```text
BILL_ID
```

Exact participation fields:

```text
RST_MONA_CD
PUBL_MONA_CD
```

L3 enumeration must not use bill, committee, result or proposer filters. The official response
does not expose a trusted provider-side page echo, so coverage is established from the requested
page contract, stable total count, exact expected row count, page fingerprints, unique
`BILL_ID` coverage and complete role-code parsing.

Official conditions:

- free access;
- development auto-approval and operational review approval;
- provider-controlled traffic allowance;
- license: 이용허락범위 제한 없음.

## Semantics and minimization

One observation represents one official member-proposed bill row in one Assembly term. It may
retain bill identity/title/date/committee/result, exact representative/co-proposer member codes
and the official detail link. Display-name proposer lists and summary text are not required for
exact code-first participation and are omitted from the persistent normalized record.

`RST_MONA_CD` establishes representative-proposer participation and `PUBL_MONA_CD` establishes
co-proposer participation only when every row in the bounded term has both fields present and
parseable. A complete L3 scan does not make participation a performance, influence, alliance or
faction claim.

The observation is a multi-person legislative event record. It carries exact member-code hints
but does not authorize Person creation, name matching, cross-Person merging or direct
publication.

## Baseline

```text
origin/master: a56e7a665ce6de5bd12b11c75cbdc57ed4f40ffa
local starting HEAD: 295b7f27a785dbb8d2fa3b46a6fb61d0272be5b5
Alembic head: 0004
existing legislative targeted tests: 17 passed, 1 cache warning
live Assembly key: unavailable on this host; live fetch is NOT_RUN
```

## Milestone A — Contract and connector hardening

- [x] read governing repository documents and batch skill
- [x] inspect current connector, stager, tests and maturity matrix
- [x] verify current official catalog and endpoint existence
- [x] verify access, license and review conditions
- [x] confirm unfiltered `AGE` bounded scope
- [x] confirm `BILL_ID` provider row key
- [x] update SourcePolicy review evidence
- [x] define privacy-minimized persistent normalized fields
- [x] preserve existing exact in-memory staging behavior

## Milestone B — Bill participation L3 enumeration

- [x] define feeder, scope key, semantic scope and source contract
- [x] reject all filtered or non-first-page enumeration
- [x] full pagination from page 1
- [x] validate stable total count and expected pages
- [x] validate exact expected page row counts
- [x] validate row `AGE` against the bounded scope
- [x] require complete parseable role-code fields
- [x] detect duplicate page content
- [x] detect duplicate/conflicting `BILL_ID`
- [x] persist SourceRun/SourceCheckpoint/FeederObservation
- [x] commit page and checkpoint atomically
- [x] support PARTIAL and resume
- [x] unchanged rerun no-op
- [x] changed bill row creates immutable observation
- [x] keep multi-person event and publication boundaries
- [x] add CLI entrypoint without breaking review staging

## Milestone C — Verification and closure

- [x] deterministic multi-page test
- [x] unchanged rerun test
- [x] changed row test
- [x] failed page/resume test
- [x] atomic checkpoint failure test
- [x] total/page/row mismatch tests
- [x] duplicate/conflicting bill tests
- [x] wrong-term and incomplete role-code tests
- [x] policy denial before network/run
- [x] credential absent from persistence/errors
- [x] display-name proposer text absent from persistence
- [x] zero-result bounded scope test
- [x] existing legislative staging regression
- [x] full Python verification
- [x] web verification
- [x] Alembic roundtrip
- [x] inspect clean-v0 diff
- [x] update feeder maturity to L3
- [x] record live fetch as NOT_RUN when key remains unavailable

## Stop condition

Stop when one unfiltered National Assembly term has:

1. complete deterministic bill pagination and unique `BILL_ID` coverage;
2. complete code-first representative/co-proposer field coverage;
3. persistent run/checkpoint/observation state;
4. atomic resume and idempotent immutable version behavior;
5. existing exact review staging preserved;
6. full local verification and migration roundtrip completed;
7. no bill-detail scraping, name fallback, second repository/raw store, generic framework,
   materialization bypass or unsupported performance/faction semantics.

## Evidence

Official contract review on 2026-08-31:

- data.go.kr catalog `15125946` identifies the National Assembly Secretariat dataset, free
  access, 이용허락범위 제한 없음, development auto-approval, operational review approval and
  provider-controlled traffic;
- the exact `nzmimeepazxkubdpn` endpoint returned HTTP 200 with the official `ERROR-300`
  missing-required-parameter response when probed without a credential, confirming the current
  endpoint without performing a data fetch;
- `ASSEMBLY_API_KEY` is absent on this host, so live bill enumeration remains `NOT_RUN`.

Implementation:

```text
b0eaebe P0 docs: define Assembly bill participation L3 plan
81404d7 P0: add resumable Assembly bill participation L3
```

Observed local verification after the final implementation:

```text
legislative targeted pytest: 32 passed, 1 cache warning
full pytest: 230 passed, 4 warnings in 57.56s
ruff: All checks passed
mypy: Success, 51 source files
packages.verification.quality: passed=true
apps/web lint: PASS
apps/web typecheck: PASS
apps/web tests: 2 passed
apps/web build: PASS
```

The four full-suite warnings are the existing Starlette/httpx deprecation, two SQLite datetime
adapter deprecations and the workspace pytest-cache access warning.

`make verify` itself is runner-unavailable because GNU Make is not installed on this Windows
host. Every underlying Makefile verification command was executed directly; this is not recorded
as a Make runner pass.

Alembic was verified against a fresh explicit temporary SQLite database:

```text
fresh upgrade -> 0004 (head)
downgrade -1 -> 0003
upgrade head -> 0004 (head)
```

Clean-v0 audit from starting HEAD `295b7f2` through implementation HEAD `81404d7`:

```text
SqlAlchemyRepository class definitions: 1
apps.api.repository imports: 0
parallel raw observation/payload stores: 0
generic crawler/framework additions: 0
materialization/API/persistence changes: 0
dependency manifest changes: 0
git diff --check: PASS
```

The latest remote `master` workflow remains run `33327647910` for SHA `a56e7a6`. Its verify job
has no executed steps and the GitHub annotation states that account payments failed or the
spending limit must be increased. No GitHub check exists for the unpushed local implementation
commits, so no CI pass is claimed.

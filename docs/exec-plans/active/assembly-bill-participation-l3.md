# National Assembly bill participation L3

Status: active — official contract and local baseline verified on 2026-08-31.

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
- [ ] update SourcePolicy review evidence
- [ ] define privacy-minimized persistent normalized fields
- [ ] preserve existing exact in-memory staging behavior

## Milestone B — Bill participation L3 enumeration

- [ ] define feeder, scope key, semantic scope and source contract
- [ ] reject all filtered or non-first-page enumeration
- [ ] full pagination from page 1
- [ ] validate stable total count and expected pages
- [ ] validate exact expected page row counts
- [ ] validate row `AGE` against the bounded scope
- [ ] require complete parseable role-code fields
- [ ] detect duplicate page content
- [ ] detect duplicate/conflicting `BILL_ID`
- [ ] persist SourceRun/SourceCheckpoint/FeederObservation
- [ ] commit page and checkpoint atomically
- [ ] support PARTIAL and resume
- [ ] unchanged rerun no-op
- [ ] changed bill row creates immutable observation
- [ ] keep multi-person event and publication boundaries
- [ ] add CLI entrypoint without breaking review staging

## Milestone C — Verification and closure

- [ ] deterministic multi-page test
- [ ] unchanged rerun test
- [ ] changed row test
- [ ] failed page/resume test
- [ ] atomic checkpoint failure test
- [ ] total/page/row mismatch tests
- [ ] duplicate/conflicting bill tests
- [ ] wrong-term and incomplete role-code tests
- [ ] policy denial before network/run
- [ ] credential absent from persistence/errors
- [ ] display-name proposer text absent from persistence
- [ ] zero-result bounded scope test
- [ ] existing legislative staging regression
- [ ] full Python verification
- [ ] web verification
- [ ] Alembic roundtrip
- [ ] inspect clean-v0 diff
- [ ] update feeder maturity to L3
- [ ] record live fetch as NOT_RUN when key remains unavailable

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

Update with commands and observed results during implementation.

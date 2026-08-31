# NEC Local Winner Feeder

## Scope

The L3 feeder enumerates every official winner row for one exact local-election scope:

```text
(sgId, sgTypecode)
```

Supported local election type codes remain:

```text
3  시·도지사
4  구·시·군의 장
5  시·도의회의원
6  구·시·군의회의원
10 교육의원
11 교육감
```

Optional province, district and party filters are rejected in L3 mode. They remain available
to the existing reviewed single-pull staging path.

## Official contract

Reviewed on 2026-08-31:

- catalog: `https://www.data.go.kr/data/15000864/openapi.do`
- endpoint:
  `https://apis.data.go.kr/9760000/WinnerInfoInqireService2/getWinnerInfoInqire`
- authentication: public-data portal `serviceKey`, injected only at request time
- pagination: `pageNo`, `numOfRows`, `totalCount`
- bounded inputs: `sgId`, `sgTypecode`
- optional filters: `sdName`, `sggName`
- provider record key: `huboid`
- license: 이용허락범위 제한 없음
- development traffic: 10,000 requests
- operational use: review approval

The catalog states that final winner data is transferred and validated after an election and
normally becomes available within two months. A successful zero-row run therefore proves only
that the requested current provider scope was empty, not that the election had no winner.

## Privacy and disclosure semantics

The official response contains a public address. Civic Intel discards it before normalization.
The following also remain excluded because they are unnecessary for identity and election-result
provenance:

```text
gender
age
jobId
eduId
raw provider row
serviceKey
```

Allowed normalized fields are limited to:

```text
huboid / candidate_id
sgId / election_id
sgTypecode / election_type
official election type name
name and Hanja alias
birth date
province / municipality / district
party and candidate number
public job
submitted education and careers
WINNER outcome
votes and vote rate
```

Job, education and career strings preserve
`candidate_submitted_election_disclosure` semantics. They are not independently verified
biography facts.

## Identity boundary

The exact observation identity hint contains:

```json
{
  "canonical_name": "홍길동",
  "aliases": ["洪吉童"],
  "birth_date": "1970-01-02",
  "external_ids": {
    "nec_huboid": "100000000"
  }
}
```

`huboid` is the official row key inside the bounded election scope. It is not permission for a
name-only or cross-lane automatic Person merge. Existing materialization/publication gates remain
authoritative.

## L3 persistence

The scope key is:

```text
{sgId}:{sgTypecode}
```

For every page, the enumerator validates:

- requested and provider-returned page/size;
- stable `totalCount` and expected page count;
- exact expected row count;
- row election id/type consistency;
- duplicate or conflicting `huboid`;
- duplicate page fingerprint;
- final unique-record count.

The page Source/Snapshot/Observations and checkpoint commit in one repository transaction.
Failed later pages produce `PARTIAL`; resume begins after the last committed page. An unchanged
rerun is an observation no-op, while a changed normalized winner row creates a new immutable
version.

## Runtime boundary

The CLI entrypoint remains `civic-stage-local-election`.

```text
--enumerate-winners
--resume
--database-url
```

L3 mode requires an unfiltered winner scope and a migrated database. It does not schedule runs,
silently migrate, persist credentials or retain raw response bodies.

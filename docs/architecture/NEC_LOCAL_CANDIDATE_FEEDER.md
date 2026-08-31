# NEC Local Candidate Feeder

## Scope

The L3 feeder enumerates every official candidate-registration row for one exact
local-election scope:

```text
(sgId, sgTypecode)
```

Supported local-election type codes remain `3`, `4`, `5`, `6`, `10` and `11` as documented
for the winner feeder. Optional province, district and party filters are rejected in L3 mode.
They remain available to the reviewed single-pull staging path.

## Official contract

Reviewed on 2026-08-31:

- catalog: `https://www.data.go.kr/data/15000908/openapi.do`
- endpoint:
  `https://apis.data.go.kr/9760000/PofelcddInfoInqireService/getPofelcddRegistSttusInfoInqire`
- authentication: public-data portal `serviceKey`, injected only at request time
- pagination: `pageNo`, `numOfRows`, `totalCount`
- bounded inputs: `sgId`, `sgTypecode`
- optional filters: `sdName`, `sggName`, `jdName`
- provider record key: `huboid`
- license: 이용허락범위 제한 없음
- development traffic: 10,000 requests
- operational use: review approval

## Privacy and disclosure semantics

The provider address is discarded before normalization. Gender, age, provider classification
IDs, raw rows and credentials are also unnecessary and excluded.

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
registration status
```

Job, education and career strings retain
`candidate_submitted_election_disclosure` semantics. Registration status records exactly what
the official candidate source disclosed. Candidate enumeration does not infer winner status,
current office, biography verification, ideology, influence or appointment probability.

## Identity boundary

The observation may retain exact `canonical_name`, Hanja alias, birth date and
`nec_huboid`. The provider key is an exact source identity anchor inside the bounded election
scope. It is not permission for name-only or cross-lane Person merge, materialization or direct
publication.

## L3 persistence

The feeder is `nec_local_election_candidates`, the semantic scope is
`local_election_candidacy`, and the scope key is:

```text
{sgId}:{sgTypecode}
```

For every page, the enumerator validates:

- requested and provider-returned page/size;
- stable `totalCount` and expected page count;
- exact expected row count;
- row election id/type consistency;
- required registration status;
- duplicate or conflicting `huboid`;
- duplicate page fingerprint;
- final unique-record count.

Page Source/Snapshot/Observations and checkpoint state commit in one repository transaction.
Failed later pages produce `PARTIAL`; resume begins after the last committed page. Unchanged
reruns are observation no-ops, while a changed normalized registration row creates a new
immutable version.

## Runtime boundary

The existing `civic-stage-local-election` entrypoint adds:

```text
--enumerate-candidates
--resume
--database-url
```

`--resume` without an explicit enumeration mode keeps the prior winner-resume behavior. L3 mode
requires an unfiltered scope and a migrated database. It does not schedule runs, migrate schema,
persist credentials, retain raw response bodies or create Persons.

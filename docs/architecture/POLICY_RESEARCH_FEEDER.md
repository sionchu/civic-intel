# Policy Research Feeder

## Purpose

Civic Intel uses NKIS research-output metadata to discover policy researchers and recurring
research domains that may feed commissions, ministries, Presidential Office roles, elected
office and other public appointments.

The core semantic split is mandatory:

```text
ResearchOutput
  !=
ResearchCareer
```

Authorship/responsibility on a report does not automatically prove employment at the report's
publishing institution.

## Official source

NKIS Open API provides research outputs from 26 government-funded economic/humanities/social
science research institutions. The research-report list endpoint is:

`https://nkis.re.kr/nkisApi/search/ReportList.do`

The reviewed list contract includes:

- `OTP_ID`: research-report ID
- `OTP_SEQ`: sequence
- `OTP_HAN_NM`: report title
- `INCHARGE_NM`: responsible researcher
- `PUBAGC`: publishing institution
- `PBL_YY`: publication year
- large/middle standard classification fields
- `ORG_LINK`: original-item link

The API requires an issued `serviceKey` after application/review.

## SourcePolicy boundary

V0 permits authorized API fetch and normalized metadata storage only.

Fail closed for:

- abstract/fulltext storage
- sending NKIS content to AI
- excerpt display
- commercial reuse

The site exposes abstracts and original links in detailed APIs, but those rights are not
assumed from API availability alone.

## ResearchOutput

A staged research output preserves:

- NKIS output ID/sequence
- title
- responsible-researcher source text
- publishing institution
- publication year
- standard classifications
- original link

`PUBAGC` is a property of the output. It is **not** automatically mapped to the person's
employer.

## Person discovery

Only an unambiguous single-person `INCHARGE_NM` may create an `IdentityCandidate`.

Examples:

```text
김연구       -> candidate may be created
박정책 외 2인 -> no person candidate
김정책, 이연구 -> no person candidate
연구원       -> no person candidate
```

The candidate uses:

- `canonical_name = INCHARGE_NM`
- `office = 연구책임자(해당 연구성과)`
- `organization = None`
- NKIS output ID/year/publisher as identity/discovery anchors

A separate institute official biography or appointment source is required to create a
`ResearchCareer` employment/leadership FACT.

## Reported research topics

Do not create a stable research-domain characterization from one report.

V0 derives a `repeated topic` only when the same NKIS middle/large classification appears in
at least two separate outputs. The result is a derived descriptor with source output count,
not a quality score or personality inference.

```text
1 report in AI industry policy
 -> no repeated-topic output

2+ reports in AI industry policy
 -> derived recurring research topic candidate
```

## Career-path integration

```text
NKIS ResearchOutput
 -> Researcher IdentityCandidate
 -> original-source identity verification
 -> institute official profile / appointment record
 -> ResearchCareerEpisode
 -> commission / ministry / campaign / elected-office links
 -> AppointmentPath / TalentPoolEntry
 -> Public Official Profiler
```

This supports descriptive routes such as:

- government-funded institute researcher -> government commission -> ministry/Presidential Office
- institute president -> high public appointment
- ministry official -> policy institute leadership -> government return
- policy researcher -> party/campaign -> elected office

Historical frequency remains descriptive and is never appointment probability.

## Quality rules

- authorship/responsibility != employment
- publishing institution != current employer
- one report != recurring research specialty
- report count != research quality
- download/citation metrics != automatic expertise score
- ambiguous author text never creates multiple guessed people
- no abstract/fulltext AI processing in V0

## Current implementation

- credential-safe `ReportList.do` connector
- review-only metadata parser
- safe single-responsible-researcher candidate staging
- repeated-topic derivation requiring at least two outputs
- offline deterministic fixtures/tests
- no automatic DB upsert/publication
- no institute staff crawling

The next employment-verification lane should use official institute staff/leadership pages or
appointment releases and must reuse the same Person identity rather than create a second
researcher registry.

# Policy Research Feeder

## Purpose

Civic Intel uses NKIS research-output metadata to discover policy researchers and recurring
research-domain candidates that may feed commissions, ministries, Presidential Office roles,
elected office and other public appointments.

The core semantic split is mandatory:

```text
ResearchOutput
  !=
ResearchCareer
```

Research responsibility on a report does not automatically prove employment at the report's
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
김연구        -> candidate may be created
박정책 외 2인 -> no person candidate
김정책, 이연구 -> no person candidate
연구원        -> no person candidate
```

The candidate uses:

- `canonical_name = INCHARGE_NM`
- `office = 연구책임자(해당 연구성과)`
- `organization = None`
- NKIS output ID/year/publisher as identity/discovery anchors

A separate institute official biography or appointment source is required to create a
`ResearchCareer` employment/leadership FACT.

## Reported research topics

Do not create a stable research-domain characterization from one report or from unrelated
researchers on the same search page.

V0 derives a `repeated topic` review candidate only when:

- `INCHARGE_NM` is an unambiguous single-person label;
- the same researcher label is paired with the same `PUBAGC` output publisher;
- the same NKIS middle/large classification appears in at least two **distinct** output IDs;
- duplicate delivery of the same output ID/sequence is collapsed first.

Even then, this is **not yet a resolved Person expertise FACT**. Same-name people can still
exist. The result remains `IDENTITY_UNRESOLVED` until Identity Resolution and the separate
employment/career lane confirm the person.

```text
김연구 + 테스트연구원 + AI정책 output A
김연구 + 테스트연구원 + AI정책 output B
 -> repeated-topic candidate within staged outputs
 -> Person expertise FACT: not yet

김연구 + output A
이연구 + output B
 -> no combined repeated-person topic
```

The count is scoped to the outputs staged in the current collection window. It is not an
exact lifetime publication count unless complete source coverage is separately established.

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

## Institute-profile source gate (KDI pilot, 2026-09-13)

The employment-verification lane is separate from NKIS output metadata. The first reviewed
candidate is the official [KDI researcher directory](https://www.kdi.re.kr/introduce/expert),
which is an institute profile source listed within the [NKIS institution directory](https://nkis.re.kr/org.do).
The inspected KDI surface includes the researcher-role views, the [organization tree](https://www.kdi.re.kr/introduce/org)
with department-level staff selection, and official director/history pages.

The rendered researcher views provide Korean and Romanized names, department/current title and
research-topic text. This is useful bounded employment and identity evidence, but the inspected
routes do not publish a complete staff/researcher universe, total coverage statement, documented
page/cursor contract, effective-date/as-of field, stable profile record key or correction and
republication semantics. The visible `extp=2` role view is a second directory view, not a
declared historical or complete-version contract. A name, department or title is therefore not
a stable identity key.

KDI's [Open API](https://www.kdi.re.kr/share/openAPI) is a separately approved, API-key-gated
publication-metadata interface; it is not a staff or employment API. KDI's
[copyright policy](https://www.kdi.re.kr/servicePolicy/copyright) states that KDI works use
공공누리 제3유형 (출처표시+변경금지), while the inspected pages do not state a
profile-data-specific right to store, normalize or republish derivative staff records. API or
page availability is not treated as permission.

Decision:

- NKIS `ResearchOutput` remains `L2 SINGLE_PULL` metadata-only and does not gain an employment
  inference from KDI's directory.
- The KDI automated profile path remains `L0 RESEARCHED; BLOCKED`; no live adapter, staff
  crawler, L3 enumeration or automatic Person materialization is authorized.
- A finite KDI profile/appointment packet may support a human-assisted L1/L2 lane only after a
  source-specific storage/normalization/redistribution decision, an exact page or document
  manifest, dated capture scope, deterministic field mapping and reviewer comparison are all
  recorded. Original profile/document sources and any analyst-normalized representation must
  remain separate Sources and snapshots; later bytes or reviewed corrections create new
  immutable observations rather than overwriting prior values.
- Any future identity bridge must use an official identity anchor or explicit official career or
  biography continuity. Name-only linking is prohibited, and an NKIS/KDI row or local join key
  is never a canonical Person ID. The existing Claim/Evidence/Source/SourcePolicy path remains
  the publication boundary; no second researcher registry or speculative career schema is added.

## Quality rules

- research responsibility != employment
- publishing institution != current employer
- one report != recurring research specialty
- same-name grouping != resolved identity
- staged-output count != lifetime output count
- report count != research quality
- download/citation metrics != automatic expertise score
- ambiguous researcher text never creates multiple guessed people
- no abstract/fulltext AI processing in V0

## Current implementation

- credential-safe `ReportList.do` connector
- review-only metadata parser
- safe single-responsible-researcher candidate staging
- repeated-topic review candidate requiring two distinct outputs within the same
  researcher-label + publisher group
- offline deterministic fixtures/tests
- no automatic DB upsert/publication
- no institute staff crawling

The next employment-verification lane should use official institute staff/leadership pages or
appointment releases and must reuse the same Person identity rather than create a second
researcher registry.

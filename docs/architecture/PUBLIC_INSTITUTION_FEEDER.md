# Public Institution Feeder

## Purpose

Civic Intel uses ALIO to explain career paths through public corporations, quasi-government
institutions and other designated public institutions without flattening them into one
`공기업` label or inferring political patronage.

The fixture path remains deterministic and review-only. The item 4 live path now adds bounded
current-roster enumeration:

```text
ALIO item 4 institution directory
 -> provider-ranked current disclosure for every institution
 -> institution classification
 -> executive / governance disclosure
 -> FeederObservation / IdentityCandidate
 -> Institutional Governance / CareerEpisode projection
 -> AppointmentPath / TalentPoolEntry
 -> Public Official Profiler
```

## Source boundary

ALIO is the official public-institution management disclosure system. Relevant disclosure
items include:

- item 4: executive status (`임원현황`)
- item 6-1: executive recruitment notice (`임원 모집공고`)
- item 7-1: retired employee/executive reemployment (`퇴직 임·직원 재취업 현황`)
- item 10: executive annual compensation (`임원 연봉`)
- board/governance and other institutional disclosures where separately reviewed

The official ALIO copyright policy permits free use of ALIO-owned works and public data,
including commercial use, subject to protected third-party rights exclusions. The reviewed
SourcePolicy permits the source-specific item 4 adapter to fetch and store normalized metadata.
Full report HTML, excerpts and AI transmission remain disabled by data minimization.

## Item 4 L3 source contract

The bounded L3 universe is the unfiltered item 4 (`reportFormRootNo=20305`) institution
directory and exactly one provider-ranked current disclosure (`rnum=1`) per returned `apbaId`.
The directory total must equal its complete row set and `apbaId` values must be unique.

The official report list is page-based with `pageNo`, `currPage`, `unitPage`, `totalCount` and
`totalPage`. Current-roster enumeration requests page 1 and validates the provider page size,
total-page calculation, exact expected row count, institution/report identity and current rank.
Historical disclosure pages are outside this scope.

The report page itself supplies the exact `/upload/disclosure/.../doc.html` path. The connector
follows only that embedded path; it does not derive or crawl report locations.

## Institution classification

Preserve the statutory/designated category as a dated attribute:

- `PUBLIC_CORPORATION`
- `QUASI_GOVERNMENT`
- `OTHER_PUBLIC_INSTITUTION`

Raw ALIO detail such as `공기업(준시장형)` or `준정부기관(위탁집행형)` is retained next to
the normalized category. Classification can change over time and must not overwrite history.

## Executive disclosure

ALIO executive-status reports can expose:

- position
- name
- role/title
- term start/end
- major prior careers as reported in the disclosure
- formal selection procedure
- selection-rule/legal basis
- disclosure/as-of date

Supported person-scope roles:

- institution head
- standing auditor/audit commissioner
- standing director
- non-standing director
- non-standing auditor

These roles are public-governance positions. Ordinary employees do not enter this feeder.

The current report exposes no stable executive-person identifier. L3 therefore uses
`disclosureNo:one-based executive table ordinal` only as a disclosure-row observation key.
It is not an external Person identity. Automatic Person creation/linking/merging is not enabled;
the existing deterministic materialization gate returns `REVIEW_REQUIRED` for ALIO observations.

### Selection-procedure rule

The disclosed procedure is valuable evidence. Preserve it exactly as governance data:

```text
임원추천위원회 추천
 -> 공공기관운영위원회 심의/의결
 -> 장관 제청
 -> 대통령 임명
```

or institution-specific procedures where applicable.

Do **not** replace that chain with a generic `정부가 임명함`, `낙하산`, or `정권 인사`
assertion. Political influence requires separate evidence and remains CLAIM/INFERENCE.

### Reported-career rule

ALIO `주요경력` establishes that the institution publicly disclosed those career entries.
It does not independently verify every prior career. The profiler may use the entries as
discovery anchors and verify important feeder episodes against their original sources.

## Executive compensation

ALIO item 10 often reports compensation by role category such as:

- 상임기관장
- 상임감사
- 상임이사 / 상임임원 평균
- 비상임이사

Therefore V0 models compensation as an **institution + role-category + fiscal-year**
disclosure. It does not attach a role-category annual amount to a named individual unless a
future source explicitly supports person-level attribution.

The value is official disclosed compensation/annual-pay information, not personal wealth.

## Reemployment disclosure

ALIO item 7-1 is separate from the Government Public Ethics Committee employment review.

```text
ALIO 7-1
 -> actual disclosed retirement / reemployment event

Public Ethics Committee
 -> legal employment-review decision
```

Never merge the two events.

Item 7-1 may include ordinary employees. Civic Intel may preserve organization-level
reemployment metadata needed for governance analysis, but **only executive rows may create a
Person/IdentityCandidate in this feeder**. Ordinary employee names are discarded before
staging output.

A reemployment disclosure does not by itself prove wrongdoing, preferential treatment or a
violation of post-employment rules.

## Privacy / roster boundary

Source reports can contain disclosure staff contacts and general institution address/phone
information. They are not needed for appointment-path analysis and are discarded.

Do not emit:

- general employee roster
- source-report writer/supervisor contact information
- personal phone/email/address
- ordinary employee reemployment identity
- inferred political affiliation from board membership
- inferred union membership from institution-level labor disclosure

## Implementation boundary

- normalized ALIO-shaped fixture staging remains supported
- reviewed source-specific live item 4 fetch and metadata-only storage
- institution classification parser
- executive-status parser and IdentityCandidate staging
- complete current item 4 institution enumeration
- SourceRun / SourceCheckpoint / FeederObservation persistence and resume
- role-category compensation staging
- executive-only reemployment identity staging
- no automatic Person creation/merge or publication
- no generic ALIO crawler
- no board-minutes NLP or political-patronage model

# Public Institution Feeder

## Purpose

Civic Intel uses ALIO to explain career paths through public corporations, quasi-government
institutions and other designated public institutions without flattening them into one
`공기업` label or inferring political patronage.

The first implementation is deterministic and staging-only:

```text
ALIO institution disclosure
 -> institution classification
 -> executive / governance disclosure
 -> IdentityCandidate
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

The public-data portal's ALIO-based general public-institution dataset is free and marked
`이용허락범위 제한 없음`. The V0 SourcePolicy still disables live report fetching until a
source-specific live adapter is reviewed; normalized metadata staging is allowed.

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

## First implementation boundary

- normalized ALIO-shaped fixtures only
- reviewed SourcePolicy with live fetch disabled
- institution classification parser
- executive-status parser and IdentityCandidate staging
- role-category compensation staging
- executive-only reemployment identity staging
- no DB upsert/publication
- no generic ALIO crawler
- no board-minutes NLP or political-patronage model

The next live adapter should target one stable ALIO report/data export and reuse these
semantics rather than introduce a second public-institution model.

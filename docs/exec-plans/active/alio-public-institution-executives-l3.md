# ALIO public-institution executives L3

Status: active — implementation pending.

## Objective

Promote the existing fixture-only ALIO public-institution executive lane from L1
`CONTRACT_STAGED` to L3 `FULL_ENUMERATION` on the canonical batch foundation.

The bounded universe is:

```text
ALIO item 4 institution directory without institution/type filters
  x
the provider-ranked current item 4 disclosure (`rnum = 1`) for every returned institution
```

This plan does not enumerate historical item 4 reports, collect ordinary employees, ingest
executive compensation or reemployment, schedule synchronization, publish claims, create a
generic disclosure runner, or add a second persistence path.

## Priority and actual baseline maturity

Five feeders are already L3 in the current code and passed their current persistent-enumerator
regressions:

1. National Assembly members
2. Gwanbo personnel notices
3. NEC local elected-office winners
4. National Assembly bill participation
5. NEC local election candidates

ALIO is the next P0 because it already has a reviewed public-interest boundary,
`AlioInstitutionRecord` / `AlioExecutiveRecord` contracts, deterministic fixture parsers,
identity staging and privacy tests. Actual code is still L1: `can_fetch=False`, no live
connector, no SourceRun, no SourceCheckpoint and no FeederObservation path.

## Governing official contract

Official ALIO surfaces reviewed on 2026-08-31:

```text
item catalog: https://www.alio.go.kr/item/itemList.do
item 4 directory: https://www.alio.go.kr/item/itemOrganList.do?reportFormRootNo=20305
copyright policy: https://www.alio.go.kr/notice/copyright.do
robots policy: https://www.alio.go.kr/robots.txt
```

The official item page identifies item 4 as `임원현황`, a current/susi report, and its own
JavaScript exposes the exact structured-disclosure calls:

```text
POST /item/itemOrganListSusi.json
POST /item/itemReportListSusi.json
GET  /item/itemReport.do?seq={disclosureNo}&disclosureNo={disclosureNo}
GET  the exact /upload/disclosure/.../doc.html path embedded by itemReport.do
```

This is an ALIO structured-disclosure adapter, not a claim that ALIO publishes a separately
documented public OpenAPI. No endpoint or field may be derived when the official page/response
does not expose it.

### Institution universe

The unfiltered item 4 directory request is:

```json
{"apbaType": [], "apbaId": "", "reportFormRootNo": "20305"}
```

The response supplies `totalCnt` and the complete `organList`. The institution identifier is
`apbaId`; permitted directory fields are `apbaId`, `apbaNa`, `apbaType` and `typeNa`.
`totalCnt` must equal the row count and every `apbaId` must be unique.

### Current disclosure and pagination

For each exact directory row the official page sends:

```json
{
  "pageNo": 1,
  "apbaId": "...",
  "apbaType": "...",
  "reportFormRootNo": "20305"
}
```

The response exposes `page.currPage`, `page.unitPage`, `page.totalCount`, `page.totalPage` and a
ranked result list. The bounded current-roster contract requires page 1, page-size 10, a result
with `rnum = 1`, matching `apbaId`, `reportFormNo = 20305`, `reportGbn = Y`, and a unique
`disclosureNo`. Historical pages are outside this plan's universe; their totals are validated
only to prove that page 1 is a coherent provider page and that the current row exists.

### Executive fields and record identity

The current report HTML exposes these existing-contract fields:

```text
직위
성명
직책
임기 시작일 / 종료일
주요경력
선임절차
선임절차규정
기준일
```

Gender, disclosure-author/supervisor identities, departments, phone numbers, attachments and
raw HTML are excluded. ALIO exposes no stable executive-person identifier in this contract.
The observation provider record key is therefore the disclosure-bound source row key:

```text
{disclosureNo}:{one-based executive table ordinal}
```

It identifies one row in one immutable disclosure. It is not an external Person ID and cannot
authorize AUTO_CREATE, AUTO_LINK or cross-Person merge.

### Use conditions

The current ALIO copyright policy says ALIO-owned works may be reused without separate
permission and public data may be freely used, including commercially, subject to protected
third-party rights exclusions. `/robots.txt` allows all paths. No request-rate limit is
published, so the implementation remains sequential and source-bounded.

SourcePolicy permits fetch and normalized metadata storage. Fulltext, excerpts and AI
transmission remain disabled because the report contains unnecessary disclosure-staff contacts
and the L3 contract needs only normalized executive metadata.

## Baseline

```text
branch: master
local/origin HEAD: 173ed8a47ded963ed9907368a3fe5daefc4a4b0f
tracked tree: clean
Alembic head: 0004
five L3 targeted tests: 55 passed, 1 pytest-cache warning
existing ALIO tests: 7 passed, 1 pytest-cache warning
actual ALIO maturity: L1 CONTRACT_STAGED
live contract probes: official item/directory/report/document/copyright/robots surfaces returned 200
```

## Milestone A — Connector and parser

- [ ] update SourcePolicy from the current official terms review
- [ ] preserve existing fixture parser/stager contracts and tests
- [ ] add the exact unfiltered item 4 directory request
- [ ] validate directory total and unique `apbaId`
- [ ] add the exact current-report page request
- [ ] validate page number, size, totals, result rank and report/institution identifiers
- [ ] follow only the exact report-document path embedded by the official report page
- [ ] parse only existing `AlioExecutiveRecord` fields from item 4 executive tables
- [ ] fail closed on malformed, masked or unsupported executive rows
- [ ] exclude gender, contacts, staff identities, attachments and raw HTML

## Milestone B — Current-roster L3 enumeration

- [ ] define feeder, scope key, semantic scope and source contract
- [ ] reject institution/type filters and non-current report selection
- [ ] enumerate every unique institution returned by the item 4 directory
- [ ] use `disclosureNo:ordinal` only as a disclosure-row provider key
- [ ] detect duplicate/conflicting provider rows and disclosure reuse
- [ ] persist SourceRun/SourceCheckpoint/FeederObservation
- [ ] commit each institution and checkpoint atomically
- [ ] support PARTIAL and resume with directory fingerprint validation
- [ ] unchanged rerun no-op
- [ ] changed row creates an immutable observation version
- [ ] keep existing staging output valid
- [ ] keep ALIO materialization on the existing unsupported-feeder REVIEW_REQUIRED branch
- [ ] add a source-specific CLI entrypoint without a generic runner

## Milestone C — Verification and closure

- [ ] deterministic multi-institution full-scope test
- [ ] directory total/duplicate identifier tests
- [ ] current report page/size/total/rank mismatch tests
- [ ] duplicate/conflicting row and disclosure tests
- [ ] unchanged rerun and immutable changed-row tests
- [ ] partial failure, resume and atomic-checkpoint tests
- [ ] policy denial before network/run
- [ ] contact/staff/raw HTML exclusion tests
- [ ] materialization REVIEW_REQUIRED and no-Person test
- [ ] existing ALIO staging regression
- [ ] full Python verification
- [ ] Ruff and mypy
- [ ] quality report
- [ ] web verification
- [ ] Alembic upgrade/downgrade/re-upgrade roundtrip
- [ ] clean-v0 audit
- [ ] update maturity to L3
- [ ] close plan with actual evidence

## Stop condition

Stop when the unfiltered ALIO item 4 current executive roster has:

1. exact official directory/report/document contracts with no guessed endpoint or field;
2. complete unique-institution coverage and validated current-report page semantics;
3. persistent run/checkpoint/observation state with atomic resume and idempotent versions;
4. disclosure-bound row keys that are never treated as provider Person identities;
5. existing deterministic materialization behavior placing ALIO observations in
   REVIEW_REQUIRED without automatic Person creation or merge;
6. private/contact/staff fields and raw report HTML absent from persistence;
7. existing ALIO fixture staging preserved;
8. full local verification and Alembic roundtrip completed;
9. no migration, second repository, raw truth store, generic framework or publication bypass.

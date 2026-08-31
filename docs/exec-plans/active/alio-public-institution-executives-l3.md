# ALIO public-institution executives L3

Status: completed — stop condition met locally on 2026-08-31.

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

- [x] update SourcePolicy from the current official terms review
- [x] preserve existing fixture parser/stager contracts and tests
- [x] add the exact unfiltered item 4 directory request
- [x] validate directory total and unique `apbaId`
- [x] add the exact current-report page request
- [x] validate page number, size, totals, result rank and report/institution identifiers
- [x] follow only the exact report-document path embedded by the official report page
- [x] parse only existing `AlioExecutiveRecord` fields from item 4 executive tables
- [x] fail closed on malformed, masked or unsupported executive rows
- [x] exclude gender, contacts, staff identities, attachments and raw HTML

## Milestone B — Current-roster L3 enumeration

- [x] define feeder, scope key, semantic scope and source contract
- [x] reject institution/type filters and non-current report selection
- [x] enumerate every unique institution returned by the item 4 directory
- [x] use `disclosureNo:ordinal` only as a disclosure-row provider key
- [x] detect duplicate/conflicting provider rows and disclosure reuse
- [x] persist SourceRun/SourceCheckpoint/FeederObservation
- [x] commit each institution and checkpoint atomically
- [x] support PARTIAL and resume with directory fingerprint validation
- [x] unchanged rerun no-op
- [x] changed row creates an immutable observation version
- [x] keep existing staging output valid
- [x] keep ALIO materialization on the existing unsupported-feeder REVIEW_REQUIRED branch
- [x] add a source-specific CLI entrypoint without a generic runner

## Milestone C — Verification and closure

- [x] deterministic multi-institution full-scope test
- [x] directory total/duplicate identifier tests
- [x] current report page/size/total/rank mismatch tests
- [x] duplicate/conflicting row and disclosure tests
- [x] unchanged rerun and immutable changed-row tests
- [x] partial failure, resume and atomic-checkpoint tests
- [x] policy denial before network/run
- [x] contact/staff/raw HTML exclusion tests
- [x] materialization REVIEW_REQUIRED and no-Person test
- [x] existing ALIO staging regression
- [x] full Python verification
- [x] Ruff and mypy
- [x] quality report
- [x] web verification
- [x] Alembic upgrade/downgrade/re-upgrade roundtrip
- [x] clean-v0 audit
- [x] update maturity to L3
- [x] close plan with actual evidence

## Evidence

Official live contract review on 2026-08-31:

```text
item catalog/item 4 page: HTTP 200
copyright policy: HTTP 200
robots.txt: HTTP 200, User-agent * / Allow /
unfiltered item 4 directory total: 355 institutions
sample institution: C0847
sample report history: 13 reports, 2 provider pages
provider-ranked current disclosure: 2026020303111469
sample current report: 7 supported executive rows
report form: 20305
```

The live probe exercised one institution through the production connector. A 355-institution
live persistence run was not executed because ALIO publishes no request-rate limit; complete
enumeration, coverage, atomicity, resume and idempotency were exercised with deterministic
multi-institution transports.

Implementation:

```text
333218d P0 docs: define ALIO executives L3 plan
28f62e6 P0: add resumable ALIO executives L3
```

Observed local verification:

```text
five pre-existing L3 feeder regressions: 55 passed, 1 pytest-cache warning
ALIO L1/L3 targeted tests: 21 passed, 1 pytest-cache warning
full pytest: 257 passed, 4 warnings in 55.49s
ruff check: All checks passed
mypy: Success, 51 source files
packages.verification.quality: passed=true
apps/web lint: PASS
apps/web typecheck: PASS
apps/web tests: 2 passed
apps/web build: PASS
```

`make verify` itself is runner-unavailable because GNU Make is not installed on this Windows
host. Every command in the Makefile's verify path was executed directly. Repository-wide
`ruff format --check` remains non-passing on 47 pre-existing files; all four Python files
touched by this implementation were formatted and pass targeted format-check.

Migration verification:

```text
Alembic heads: 0004 (head)
tests/test_migrations.py: 1 passed
fresh upgrade -> 0004
downgrade 0004 -> 0003 -> 0002 -> 0001
re-upgrade -> 0004 while preserving a populated Person row
```

No migration was added because ALIO L3 reuses the canonical
SourceRun/SourceCheckpoint/FeederObservation and review-item schema through revision `0004`.

Clean-v0 audit from implementation baseline `333218d` through `28f62e6`:

```text
SqlAlchemyRepository class definitions: 1
apps.api.repository imports: 0
parallel raw observation/payload stores: 0
generic crawler/framework additions: 0
materialization policy changes: 0
migration changes: 0
new dependency changes: 0
git diff --check: PASS
```

ALIO observations carry no stable provider Person ID. The exact existing materialization gate
returns `REVIEW_REQUIRED / UNSUPPORTED_FEEDER`; the regression proves zero automatic Persons are
created and an OPEN IdentityReviewItem is persisted.

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

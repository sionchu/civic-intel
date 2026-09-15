# ALIO Item 12 MONEY v0

Status: completed — `L2 SINGLE_PULL` bounded three-institution proof on 2026-09-14 and approved
staging observation rehearsal on 2026-09-15; the Claim-gated read-only projection still has no
live organization Claim input; L3 was not attempted.

## Objective

Prove the second Derived Intelligence primitive, `MONEY`, over the official ALIO item 12
`기관장 업무추진비` disclosure without inventing a Person attribution, a generic financial model
or a public Claim path that the current domain cannot express.

The slice is:

```text
ALIO item 12 directory/report/document
 -> typed institution + role-scope + fiscal-year aggregate
 -> Source / SourceSnapshot / FeederObservation
 -> deterministic year-over-year MONEY projection
```

The projection is descriptive evidence-derived output. It does not become a `FACT`, publish a
Claim, or imply waste, corruption, personal spending or institutional performance.

## Baseline and governing boundary

- Initial `HEAD` and `origin/master`: `1af5f7ca0a76a5683415d9241c07066d5166bf90`.
- Worktree branch: `codex/change-discovery-plan`; Alembic head: `0004`.
- Existing `SourcePolicy`, `Source`, `SourceSnapshot`, `SourceRun`, `SourceCheckpoint` and
  `FeederObservation` are the only persistence foundation used here.
- At this plan's baseline, `Claim.person_id` was mandatory and the API had no organization-scoped
  Claim/Evidence route. The Item 12 MONEY projection therefore carried
  `publication_status: BLOCKED` and no Claim IDs; the follow-on subject extension is documented
  in `organization-claim-publication-v0.md`.
- `ReviewedPersonBundle`, Asset contracts, person materialization, a parallel organization-claim
  table, a generic expense framework, raw attachment storage and a generic ALIO crawler are
  outside scope.

## Official source contract

The source was reviewed against the [ALIO item catalog](https://www.alio.go.kr/item/itemList.do),
the [item 12 institution directory](https://www.alio.go.kr/item/itemOrganList.do?reportFormRootNo=20701),
current report pages and the [ALIO copyright policy](https://www.alio.go.kr/notice/copyright.do).

### Universe and collection boundary

- Item identity is `기관장 업무추진비`, `reportFormRootNo=20701`.
- The official page posts an unfiltered request to `/item/itemOrganListJung.json` with empty
  `apbaType`, `jidtDptm`, `area`, `apbaId` and `quart` filters.
- The 2026-09-14 response declared `totalCnt=355`, returned 355 rows and 355 unique `apbaId`
  values. Four rows had a submission reference but no current `disclosureNo` and `files="@"`.
- The implementation uses only the reviewed known-positive codes `C0019`, `C0129` and `C0908`.
  The 355-row directory is validated as the source pointer inventory, not treated as an annual
  financial-row universe.

### Report, rows and locators

- A selected report is requested with exactly `apbaId`, `reportFormRootNo`, `disclosureNo`,
  `nowYear` and `nowQuarter`.
- The report page exposes the exact `/upload/disclosure/.../doc.html` path and a numeric
  `submission_no`; the connector follows that path only.
- The report table exposes `연도`, `업무추진비 집행금액`, `집행상세내역`, `(단위: 천원)`,
  `기준일` and `제출일`. The three proof institutions expose five annual rows for 2021–2025;
  selected rows use `.xls`/`.xlsx`, while recognized `.pdf`/`.hwp` names from unrelated directory
  rows are retained as attachment locator metadata only and their bytes are not fetched.
- `apbaId` is the ALIO institution namespace. `disclosureNo` is the current report identity.
  `submissionNo` identifies the submission used in the document/attachment locator. None is a
  canonical Person authority.

### Identity, version and corrections

The candidate normalized row key is:

```text
{disclosureNo}:{fiscal_year}
```

It is accepted only after exact directory/report identity, numeric disclosure/submission values,
and duplicate fiscal-year rejection. Filename and table ordinal are locators, not permanent keys.
The provider does not publish a correction/replacement/tombstone chain for annual rows. A changed
normalized value is consequently a new immutable observation version; the worker never labels it
as a provider correction or silently selects a latest value. Explicit no-current rows are kept as
source missingness and are never converted to zero.

### Rights and minimization

The reviewed ALIO policy permits fetch and normalized metadata storage for the source-bounded
lanes, including commercial use for ALIO-owned/public data subject to third-party rights. It
denies fulltext, excerpt and AI transmission in this repository. No attachment bytes, report
HTML, writer/supervisor/confirmer names, department, phone or email are persisted.

## Implementation

- `packages/connectors/alio_disclosures.py` adds the Item 12 directory/report connector, typed
  directory and aggregate-row contracts, strict unit/date/table parsing and exact embedded
  document resolution. The existing ALIO policy ID is reused and minimally widened to cover
  Item 12.
- `workers/alio_business_expense.py` adds an explicit allowlisted, sequential bounded worker with
  shared source-page commits, checkpoint metadata, source/run failure states and unchanged/new
  observation version behavior. It does not materialize identities.
- `packages/rendering/money_projection.py` adds the deterministic method
  `money.alio-head-expense-yoy.v1`. It compares two fiscal years for one institution and role
  scope, computes integer KRW absolute delta and a two-decimal percent only when the earlier
  amount is nonzero. A zero baseline preserves the absolute delta and emits no percent.
- `pyproject.toml` exposes `civic-stage-alio-money` as the source-specific entry point.
- No domain class, SQLAlchemy row, Alembic migration, dependency or public route was added.

## Acceptance and verification

The source-specific regression file `tests/test_alio_item12_money.py` covers directory count and
identity, five annual rows, `천원` normalization, recognized document metadata and selected-row
spreadsheet gating, malformed unit/amount/duplicate-year/institution cases, explicit no-data,
policy-minimized persistence, no Person/Claim/review link, idempotent rerun, changed immutable
version, exact provenance, deterministic MONEY output, zero baseline and the absent public
organization route.

Executed targeted evidence:

```text
pytest tests/test_alio_item12_money.py tests/test_alio_public_institutions.py tests/test_batch_alio_executives.py
40 passed
ruff check packages/connectors/alio_disclosures.py workers/alio_business_expense.py packages/rendering/money_projection.py tests/test_alio_item12_money.py
passed
mypy packages/connectors/alio_disclosures.py workers/alio_business_expense.py packages/rendering/money_projection.py
Success: no issues found
```

Milestone verification:

```text
pytest -o addopts='' -q: 310 passed, 4 warnings
ruff check apps packages workers tests: passed
mypy packages workers apps/api: success for 55 source files
packages.verification.quality: passed; all Golden Set checks true
Alembic upgrade -> downgrade base -> upgrade head: PASS
npm --prefix apps/web run lint: passed
npm --prefix apps/web run typecheck: passed
npm --prefix apps/web test: 5 passed
npm --prefix apps/web run build: passed; /, /_not-found, /admin/review and /people/[id] generated
Markdown relative-link check: 68 links, 0 broken
make verify: runner unavailable because GNU Make is not installed on this Windows host
```

Executed bounded live proof in ignored `alio_item12_live.db` after Alembic `upgrade head`:

```text
first run  ac60cd8b-55ab-4410-91cb-1cc1c6379512  SUCCESS  3 institutions / 15 records
second run a430b5ea-857e-45d8-8b31-34a43d950d60 SUCCESS  3 institutions / 15 records
```

Database QA after the two runs reported one Item 12 scope with 15 observations, four Sources,
four metadata-only SourceSnapshots, zero People, zero Claims, run counters `(15,15,0)` then
`(15,0,15)`, and zero contact-string matches in snapshots or observations. The live C0908
2024→2025 projection produced an absolute delta of `-2,162,000 KRW` and `-14.39%` with
publication status `BLOCKED`.

## Approved staging observation rehearsal (2026-09-15)

The first approved live attempt failed closed after parsing the 355-row directory because
unselected institutions advertised `.pdf`/`.hwp` attachments. It created one failed `SourceRun`
but no Source, SourceSnapshot or FeederObservation, and no checkpoint; no partial recovery was
needed. The minimal source-boundary fix was committed as `d06b0cc6f7c8d0313a1973a1dbafb02b0f83d20a`.

After that fix, the worker ran through a private Railway PostgreSQL tunnel and completed the
allowlist `C0019`, `C0129`, `C0908` with run
`40ba451d-4d57-4f18-bbdb-122c516ebfde`, `SUCCESS`, three institutions and 15 unique annual
records. The live staging result has four Sources (directory plus three reports), four
metadata-only SourceSnapshots, one checkpoint at cursor `3`, and two SourceRuns including the
earlier failed run. The successful run recorded `(records_seen, observations_created,
observations_unchanged) = (15, 15, 0)`.

Read-only QA against staging confirmed Alembic head `0006`, 15 target observations and 15 distinct
`{disclosureNo}:{fiscal_year}` keys, three report snapshots, zero fulltext snapshots, empty
identity hints, zero orphan observations, zero unsafe source URLs and zero Claim subject-XOR or
ClaimEvidence provenance mismatches. People, Organizations, Claims and ClaimEvidence remain zero.
The local API read smoke against the staging connection returned `/health 200`, `/ready 200`,
`/people 200` with zero rows and unknown Organization `404`. The reviewed Claim importer was not
run because no existing canonical Organization binding was present; no Organization was created
from an ALIO row.

The temporary Railway SSH key was removed after the run, Railway reported no registered keys, and
the local private/public key files were deleted. No provider plan, new resource, schema migration,
database reset/drop or public API/database exposure was performed.

## Maturity decision

The Item 12 lane remains `L2 SINGLE_PULL` for the explicit three-institution bounded proof. The
connector, parser, shared persistence, exact provenance and unchanged rerun are demonstrated by
local regressions and the live staging observation rehearsal. It is not L3: the full 355-institution
annual-row scope, long-term correction/replacement semantics and operational sync contract have
not been established or selected. The staging result is observation-only; it does not create
canonical Organizations, Claims or public FACTs. A separate operator-approved local C0908 runtime
slice exercises the Claim-backed route with two annual Claims; this is not a shipped or public
coverage claim.

## Not executed

No full-directory annual-row enumeration, attachment download, XLS/XLSX bulk ingestion, Person
lookup/materialization, automatic organization binding, generic financial abstraction, generic
crawler or scheduled sync was added in this Item 12 slice. Its bounded worker still publishes no
Claim or public FACT; the separate reviewed C0908 runtime binding is an operator-approved local
validation only.

## Next concrete action

Record one manually reviewed binding from an ALIO institution code to an existing canonical
Organization before running the reviewed two-year Claim importer; do not create the Organization
from the provider row.

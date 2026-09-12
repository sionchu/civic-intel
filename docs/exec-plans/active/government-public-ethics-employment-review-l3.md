# Government Public Ethics Committee retired-public-official employment review L3

Status: source-contract review complete - L1 retained; L3 promotion blocked as of 2026-09-12.

Methodology follow-up (2026-09-12): the source acquisition playbook in
`docs/architecture/FEEDER_SOURCE_COVERAGE.md` separates this automated-L3 stop condition from
a conditional rights-approved human-assisted packet path. Existing maturity remains L1;
no packet importer exists. Anonymous rows stay observations, not fabricated person-linked events.

## Objective

Evaluate the official Government Public Ethics Committee / Ministry of Personnel Management
(MPM) retired-public-official employment-review publication lane and promote it to source-bounded
L3 only if the official contract proves complete coverage, stable record identity, correction and
version semantics, permitted automated access and policy-compatible storage.

This is a source-contract gate, not person-by-person enrichment. It does not add a generic
crawler, a second employment-review model, a PDF archive, an automatic Person merge or a new
database abstraction.

## Decision

Do not implement a live connector or L3 enumerator at this checkpoint. The existing offline
`EmploymentReviewEvent` contract and deterministic fixture parser remain unchanged. The lane
stays at `L1 CONTRACT_STAGED`; no L3 maturity claim is made.

The official publications prove that a useful decision-result lane exists, but they do not yet
prove the source contract needed to make a repeated full enumeration safe and reproducible:

1. the MPM board count is a count of mixed posts, not a typed result-record universe;
2. the published result PDF uses a packet-local ordinal rather than a provider case identifier;
3. the publication date, committee date and per-row employment dates have different meanings;
4. the provider exposes no documented correction/version/replacement relationship for a result
   row or attachment; and
5. MPM's policy requires prior agreement for materials without a Public Use (KOGL) mark, while
   the inspected result attachment has no item-level reuse grant on its detail page.

## Baseline

Verified on 2026-09-12 before this documentation change:

```text
repository: sionchu/civic-intel
branch: master
HEAD: 64ebba32f4ad2b44e1b5fa85c547cbd560729f9f
origin/master: 64ebba32f4ad2b44e1b5fa85c547cbd560729f9f
tracked tree: clean
Alembic head: 0004
L3 feeders: National Assembly roster, Gwanbo personnel, NEC winners,
  Assembly bill participation, NEC candidates, ALIO executives, OpenDART executives
CleanEye: L0 RESEARCHED; BLOCKED
retired-public-official employment review: L1 CONTRACT_STAGED; live adapter absent
```

Existing code to preserve:

- `EmploymentReviewEvent` in `packages/domain/contracts.py`;
- `EmploymentReviewDecision` in `packages/domain/enums.py`;
- `RetiredOfficialEmploymentReviewRecord` and `parse_employment_review_rows` in
  `packages/connectors/civil_service_records.py`;
- deterministic staging in `workers/civil_service.py`;
- `SourcePolicy`, `Source`, `SourceSnapshot`, `SourceRun`, `SourceCheckpoint` and
  `FeederObservation` as the only future batch persistence path; and
- the canonical `SqlAlchemyRepository` transaction and Claim/Evidence publication gates.

## Official surfaces reviewed

### MPM result board

Official lane:

```text
https://www.mpm.go.kr/mpm/info/infoEthics/BizEthicsBoard/?mode=list&boardId=bbs_0000000000000123&category=%EC%B7%A8%EC%97%85
```

The current `취업` category exposes 125 board posts over 9 pages at 15 posts per page. The
page-size selector also exposes 25, 35 and 45. The list contains monthly employment-review
results, annual employment-history disclosure, forms, outage notices and other ethics notices.
The board therefore does not provide a typed, result-only universe; title/category semantics
would be needed to select packets.

The list is server-rendered HTML with a hidden GET form and page links whose visible `pageIdx`
links do not carry the full board/category state. The site JavaScript submits the preserved
hidden state through `jnitBoardPage(n)`. A collector would need to preserve the exact filter and
page-size state and validate the provider total on every run.

The board detail page exposes a stable-looking post identifier (`cntId`) and an attachment
reference (`FILE_...` plus a storage filename) in its download handler. The detail metadata is
limited to title, author, created date, view count, attachment name and content; no revision,
correction, withdrawal or as-of field is published.

The official RSS feed is a discovery aid, but its item links point to `/board/board.do`, which is
disallowed by the current MPM `robots.txt`, and it is not a complete historical archive. It is
not used as an L3 coverage contract.

### PETI result index

Official lane:

```text
https://www.peti.go.kr/emJdgNdHist.do
```

The page exposes 315 mixed result/history posts over 32 pages. The visible grid combines
employment-review results, 업무취급승인 results, 업무내역서 results and annual employment-history
disclosure. Its inline page code calls an internal POST endpoint named
`/getEmJdgNdHistList.do` with first/last page, sort, search and CSRF/session parameters. The
detail flow posts a provider work-item number (`bwtNo`) to `/getEmJdgNdHistDetail.do`.

This is useful evidence that PETI has provider-side post identifiers and a bounded UI list, but
the endpoint is not published as an API with a stable schema, authentication/session contract,
rate limit or historical coverage guarantee. A direct non-browser request made during this
review returned the site's session-expired response. No session or CSRF value is retained.

The PETI detail page renders attachments through a RAONKUpload view component and a separate
attachment-list request. It did not expose a stable public row-level data contract for the
employment-review table.

## Contract gate

| Required L3 dimension | Observed official contract | Decision |
|---|---|---|
| Official universe | MPM has 125 mixed `취업` posts; PETI has 315 mixed result/history posts | Insufficient: result packets are not provider-typed in the index |
| Pagination and coverage | MPM has deterministic page counts but requires hidden filter state; PETI uses internal AJAX pagination | Insufficient: no documented full-history/bounded result contract |
| Stable record identity | MPM post/attachment identifiers exist; PDF rows use only packet-local `연번`; PETI exposes post-level `bwtNo` | Blocked: no provider case/row identifier or row-stability statement |
| Attachment format | Monthly MPM result is a machine-readable PDF; current sample is 4 pages and 94 rows; historical posts can bundle multiple PDFs; forms also use HWP | Partial: no stable CSV/JSON row schema, and packet boundaries vary |
| Date semantics | PDF distinguishes the 2026-08-27 publication date, the 2026-08-21 committee date, retirement date and planned employment date | Blocked: no per-row `review_date` mapping for `EmploymentReviewEvent` |
| Correction/version semantics | Detail pages show created date and attachment, but no updated/version/correction/replacement relation | Blocked: a content hash detects bytes, not provider correction lineage |
| Use conditions | MPM permits free use for marked KOGL materials and asks users to obtain prior agreement for unmarked materials; the inspected attachment has no item-level KOGL grant; PETI footer says all rights reserved | Blocked for normalized automated reuse without a route/attachment permission decision |
| Automated collection | MPM list/file GET routes are not disallowed by the observed robots entries; `/flexer/` viewer and `/board/board.do` are disallowed; PETI result calls require browser session/CSRF context | Partial: no published route-level request pacing, API or storage contract |
| Meaning and minimization | PDF states committee decision results and separately notes that actual employment is distinct; names are not present in the inspected result table | Pass for semantics only; identity-specific materialization remains unavailable |

### Attachment field shape observed

The rendered August 2026 MPM PDF contains these table columns:

```text
연번
퇴직 당시 소속
직위(직급)
퇴직일
취업(예정) 기관(직위)
일자
심사결과
결정사유
```

The packet includes an explanatory decision-type table and a note that the result is a review
result, separate from whether employment actually occurred. The row table does not contain a
person name, a provider case number or a source-issued row version. Its ordinal resets per
packet. The July 2026 packet used the same broad layout with a different row count, confirming
that the packet is a publication unit rather than a stable case-record schema.

The historical MPM post for 2015 bundles six monthly PDFs under one board post and was posted
with a later board date than the covered review period. This shows that board `created date`
cannot be used as the underlying decision period or a universal `review_date`.

## Rights and automation boundary

The official MPM policy is:

```text
https://www.mpm.go.kr/mpm/useinfo/copyrightPolicy/
```

It states that site-owned works may be freely used when the conditions apply, that KOGL-marked
materials must follow the mark, and that materials without a KOGL mark require prior agreement
with the responsible staff. The MPM result detail exposes the PDF filename and download control,
but no item-level KOGL mark or attachment license. The official PETI page also carries an
all-rights-reserved footer. The Korea policy-briefing text license cannot be assumed to cover
the separate MPM attachment.

The observed MPM `robots.txt` is:

```text
User-agent: *
Disallow: /search/
Disallow: /flexer/
Disallow: /board/board.do
```

This leaves the MPM HTML list and direct file route technically reachable in the observed probe,
but technical reachability is not permission to store or republish the attachment. The PETI
internal JSON call is likewise not an advertised public API merely because the public page
invokes it.

## Reuse boundary if the gate later passes

Only after the source owner publishes or grants the missing contract may the automated L3
implementation milestone start. A separate bounded packet need not satisfy full-universe gates,
but still requires packet-specific rights, provenance and deterministic review. L3 must:

- use the existing `EmploymentReviewEvent` semantics and no parallel event abstraction;
- start every fetch with `SourcePolicy` and persist the source-level `SourceSnapshot`;
- persist `SourceRun`, `SourceCheckpoint` and `FeederObservation` atomically through the existing
  repository;
- require a provider case/row identifier, or an explicit source statement that the derived key
  is stable across corrections, before using a `provider_record_key`;
- retain only policy-permitted normalized fields and exact snapshot provenance;
- keep unpublished names masked/absent and route every identity to review, with zero automatic
  Person creation/linking/merging; and
- prove bounded full coverage, resumable checkpoints, unchanged reruns, changed immutable
  observations and multi-page offline regression before claiming L3.

The default key must not be invented as `cntId:attachment:row ordinal` while the provider has not
confirmed row identity and correction semantics. That shape may be used as a temporary
snapshot-local diagnostic key only, never as an L3 identity contract.

## Evidence

Observed repository and test evidence:

```text
git fetch --prune origin master
  origin/master remained 64ebba32f4ad2b44e1b5fa85c547cbd560729f9f
git rev-parse HEAD
  64ebba32f4ad2b44e1b5fa85c547cbd560729f9f
git status --short --branch
  ## master...origin/master (before this documentation change)
git ls-remote origin refs/heads/master
  64ebba32f4ad2b44e1b5fa85c547cbd560729f9f
pytest tests/test_civil_service_feeder.py -q
  10 passed
.venv\Scripts\python.exe -m pytest -q --disable-warnings
  266 collected tests reached [100%] and exited 0
.venv\Scripts\python.exe -m ruff check packages workers apps tests
  All checks passed
.venv\Scripts\python.exe -m mypy packages workers apps/api
  Success: no issues found in 51 source files
.venv\Scripts\python.exe -m packages.verification.quality
  passed: true; failures: []
npm --prefix apps/web run lint
npm --prefix apps/web run typecheck
npm --prefix apps/web run test
npm --prefix apps/web run build
  all exited 0; UI tests 2 passed; production build completed
```

Source probes:

- MPM `취업` list and current August 2026 detail page: post pagination, attachment reference,
  publication metadata and mixed-post universe.
- MPM August and July 2026 result PDFs: visual table review and local text extraction; August
  packet has 4 pages and 94 numbered rows.
- PETI result index and detail page: mixed 315-post grid, internal list/detail route and
  attachment component.
- MPM `robots.txt`: current disallowed paths recorded above.
- MPM copyright policy: item-level KOGL mark or prior agreement requirement recorded above.

## Not executed

- no live source connector, PDF parser, worker, migration or scheduled job was added;
- no production or full-history collection was attempted;
- no source attachment was copied into the repository; and
- no L3 `SourceRun` or `SourceCheckpoint` was created for this lane;
- `make verify` was not invoked because GNU Make is unavailable in this Windows environment;
  the equivalent verification commands were run directly above.

## Stop condition

Keep this plan blocked at L1 until all of the following are supplied by the official source or
an explicitly authorized public-data contract:

1. a typed and complete result universe with a documented historical boundary and backfill rule;
2. deterministic page/cursor coverage with a provider total or equivalent completeness proof;
3. a stable case/row identifier, or an explicit source rule that makes a derived key stable;
4. per-row review-date semantics and correction, replacement, withdrawal and version behavior;
5. a machine-readable row contract or written permission to parse and store the PDF fields;
6. route-level request pacing, failure behavior and automated-access permission; and
7. permitted normalized fields, snapshot retention and reuse terms compatible with SourcePolicy.

## Next Best Action

Obtain an official MPM/PETI source-owner response or published data contract covering the seven
stop-condition items. Reopen implementation only after that response is recorded; otherwise
leave this lane at L1 and keep the existing offline civil-service fixture path as the only
implemented employment-review behavior.

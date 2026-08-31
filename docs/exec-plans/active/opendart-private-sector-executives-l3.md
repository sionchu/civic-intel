# OpenDART disclosed executives L3

Status: completed — stop condition met locally on 2026-08-31.

## Objective

Promote the existing OpenDART executive-status lane from L2 `SINGLE_PULL` to source-bounded
L3 `FULL_ENUMERATION`:

```text
OpenDART corp-code master
 -> every corporation in one exact business-year/report-code scope
 -> executive-status response or official no-data response
 -> SourceRun / SourceCheckpoint
 -> immutable FeederObservation
```

This plan does not enumerate employee status or compensation, create a generic crawler or
framework, schedule synchronization, publish claims, or automatically create/link/merge a
Person.

## Baseline

Verified on 2026-08-31:

```text
branch: master
local/origin HEAD: f6bfadd13bf49d97272424b1849f9418b72496bf
tracked tree: clean
Alembic head: 0004
existing OpenDART maturity: L2 SINGLE_PULL
```

The repository has six source-specific L3 feeders:

1. National Assembly members
2. Gwanbo personnel notices
3. NEC local elected-office winners
4. National Assembly bill participation
5. NEC local-election candidates
6. ALIO public-institution executives

CleanEye local-public-institution executives remain `L0 RESEARCHED; BLOCKED` and are outside
this plan.

Existing OpenDART artifacts to preserve:

- `OpenDartCorporateConnector`
- `DartExecutiveRecord`
- `OpenDartCorporateStager`
- credential-minimized discovery URLs
- compensation-as-enrichment-only semantics
- employee-status exclusion
- canonical `SqlAlchemyRepository.commit_source_page()` transaction
- deterministic unsupported-feeder materialization decision

## Official source contract

Reviewed on 2026-08-31 from the official OpenDART development guide and terms.

### Corporation universe

```text
GET https://opendart.fss.or.kr/api/corpCode.xml
```

The credentialed endpoint returns one ZIP file containing XML for the current complete set of
OpenDART disclosure-subject companies. Its documented fields are:

```text
corp_code      8-digit disclosing-company identifier
corp_name      formal company name
corp_eng_name  formal English company name
stock_code     6-digit security code when listed; blank otherwise
modify_date    company-overview last-change date, YYYYMMDD
```

The master has no page/cursor request parameters. L3 captures one master, validates non-empty
unique corporation codes, sorts deterministically by `corp_code`, fingerprints the complete
normalized universe and then walks every corporation exactly once.

`corp_code` identifies a company. It is never a Person identifier or merge authority.

### Executive status

```text
GET https://opendart.fss.or.kr/api/exctvSttus.json
```

Required request fields:

```text
crtfc_key  credential, outbound request only
corp_code  exact 8-digit company identifier
bsns_year  four-digit business year; official coverage starts in 2015
reprt_code 11013 first quarter
           11012 half year
           11014 third quarter
           11011 annual report
```

The endpoint has no pagination fields. One company/scope response returns its complete `list`,
or official status `013` when no data exists. An `013` response is successful coverage of that
company for the requested scope and advances the checkpoint with zero observations.

Documented executive fields include receipt number, corporation class/code/name, name, gender,
birth year/month, position, registered status, full-time status, responsibility, reported main
career, largest-shareholder relation, tenure, tenure end and settlement date.

The normalized storage boundary excludes gender and any provider field not needed for corporate
governance provenance. Stored metadata is limited to:

```text
corp-code master identifier/name/stock code/modify date
explicit business year and report code
rcept_no and source-row ordinal
name and disclosed birth year/month
position / registered status / full-time status / responsibility
reported main career and largest-shareholder relation
tenure text / tenure end / settlement date
```

No raw ZIP, raw XML, raw JSON, API key, contacts, employee rows or compensation rows enter a
snapshot, observation, checkpoint, run receipt or error summary.

### Filing and identity semantics

`rcept_no` is the documented 14-digit receipt number and filing-view pointer. It identifies a
filing, not a Person. The deterministic observation key is:

```text
{corp_code}:{rcept_no}:{one-based row ordinal within that receipt}
```

That key identifies a disclosure row only. Name + company + position, birth year/month,
`corp_code`, `rcept_no` or their combination cannot authorize automatic Person creation,
linking or merge. Materialization remains `REVIEW_REQUIRED` with zero automatic Persons.

The API is extracted from company-submitted periodic reports. OpenDART states that it does not
guarantee the accuracy or completeness of the extracted information; `rcept_no` remains the
pointer to the underlying filing. Reported main career is attributed disclosure text, not an
independently verified CareerEpisode.

### Terms and request limit

The official terms require an approved member/API key, prohibit key sharing, state that the
service is generally free, and allow the provider to change per-account usage allowances.
Official API error `020` generally occurs above 20,000 requests, but the guide says a different
limit may apply.

The API/program copyright belongs to the Financial Supervisory Service; otherwise copyright
and public-data matters follow applicable copyright and public-data law. Current SourcePolicy
therefore permits credentialed fetch and normalized metadata storage only. Fulltext, excerpts,
AI transmission and commercialization remain fail-closed.

## L3 scope and coverage

One run scope is exactly:

```text
all_corporations:{bsns_year}:{reprt_code}
```

There is no implicit “latest” year or report. A run captures the current corp-code master and
must process every unique company in that fingerprinted universe. The company ordinal is the
checkpoint cursor. The checkpoint retains only bounded aggregate coverage metadata and the
universe fingerprint; it does not become a second company-master store.

Resume is allowed only when the newly fetched master has the same fingerprint and total. If the
master changes before resume, fail closed and start a new full scope rather than silently mixing
universes. The normal request ceiling makes multi-run resume expected; scheduling and adaptive
quota management remain L4.

## Milestone A — Baseline and source gate

- [x] reread governing architecture, DB, identity, batch and corporate documents
- [x] verify local/origin HEAD and clean baseline
- [x] verify the six current L3 enumerator implementations
- [x] verify current OpenDART L2 connector/stager tests
- [x] verify official corp-code master contract
- [x] verify official executive-status fields and report scopes
- [x] verify no-pagination/no-data semantics
- [x] verify receipt-number semantics, terms and request-limit language
- [x] fix the policy-minimized metadata and identity boundary

## Milestone B — Smallest coherent implementation

- [x] add a source-specific corp-code master connector/parser
- [x] retain the existing executive-status connector and staging behavior
- [x] support official `013` no-data coverage
- [x] add one OpenDART executive enumerator for an explicit year/report scope
- [x] reuse SourceRun/SourceCheckpoint/FeederObservation and `commit_source_page()`
- [x] validate complete corporation coverage and resume fingerprint
- [x] create immutable disclosure-row observations
- [x] keep every materialization decision in `REVIEW_REQUIRED`
- [x] add no schema, dependency or generic framework

## Milestone C — Verification and closure

- [x] targeted full-scope, rerun, immutable-change, partial/resume and policy tests
- [x] credential/private/employee/compensation exclusion tests
- [x] existing corporate single-pull tests remain green
- [x] full pytest, Ruff, mypy, quality and web verification
- [x] Alembic fresh upgrade/downgrade/re-upgrade roundtrip
- [x] evaluate the live-probe gate; credential absent, so no live API request was made
- [x] clean-v0 audit
- [x] prepare one coherent implementation/plan-closure commit for push
- [x] update maturity to L3 and close this plan after all local gates pass

## Implementation evidence

The source-specific implementation adds:

```text
OpenDartCorpCodeConnector
OpenDartExecutiveEnumerator
tests/test_batch_opendart_executives.py
```

The corp-code connector validates the exact credentialed ZIP/XML contract, non-empty universe,
8-digit unique `corp_code`, optional 6-digit `stock_code`, modification date and deterministic
sort. The enumerator reuses the existing executive connector and canonical repository page
transaction. It commits each company response atomically with its company-ordinal checkpoint,
including official `013` no-data responses.

Offline acceptance coverage proves:

```text
complete multi-company universe
provider no-data coverage
stable disclosure-row keys
unchanged rerun idempotency
changed-row immutable version
partial failure and resume
universe-change fail closed
checkpoint atomicity
duplicate/mismatched company fail closed
policy and missing-credential block before network/run
credential/gender/private/employee/compensation exclusion
REVIEW_REQUIRED materialization with zero Persons
```

Observed local verification:

```text
targeted seven-L3/OpenDART suite: 87 passed, 1 cache warning
full pytest: 266 passed, 4 warnings in 99.07s
ruff check: All checks passed
mypy: Success, 51 source files
packages.verification.quality: passed=true
apps/web lint: PASS
apps/web typecheck: PASS
apps/web tests: 2 passed
apps/web build: PASS
changed-file Ruff format check: PASS, 3 files
```

`make verify` remains runner-unavailable because GNU Make is not installed on this Windows host;
the underlying canonical commands were executed directly. Repository-wide Ruff format check
remains non-passing on 41 pre-existing files. This implementation formats every touched Python
file.

Migration verification used a new temporary SQLite database:

```text
Alembic heads: 0004 (head)
fresh upgrade -> 0004
downgrade 0004 -> 0003 -> 0002 -> 0001 -> base
re-upgrade -> 0004
tests/test_migrations.py: 1 passed
schema/migration changes in this milestone: 0
```

The environment exposed no `DART_API_KEY`; therefore no credentialed live API request or full
live enumeration was made. Missing-credential regression proves the connector fails before
network access. Official documentation inspection and deterministic mock transport are the live
contract and executable acceptance evidence for this milestone.

Clean-v0 audit:

```text
SqlAlchemyRepository class definitions: 1
apps.api repository imports: 0
parallel raw observation/payload stores: 0
schema/migration changes: 0
dependency changes: 0
materialization-gate changes: 0
generic crawler/framework additions: 0
forbidden infrastructure additions: 0
git diff --check: PASS
```

## Stop condition

Stop only when one exact business-year/report-code scope can process every company in a stable
corp-code master, treat no-data responses as covered companies, persist atomic checkpointed
observations, resume safely, prove idempotent/immutable behavior offline, and isolate all Person
materialization to review.

If the official contract, terms or request limit does not permit that source-bounded design,
close as blocked without guessing an endpoint or field.

The permitted branch is the observed result. The complete bounded scope, persistence, resume,
immutability and review isolation pass locally, so this plan closes at L3.

## Next Best Action

Promote the official Government Public Ethics Committee retired-public-official employment-
review lane from L1 by first fixing its exact published universe, decision-record identifier,
coverage/version semantics and permitted structured access contract.

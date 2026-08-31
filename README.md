# Civic Intel V0

Evidence-grounded public-official intelligence with policy-first ingestion and fully
traceable publication.

The offline baseline is Golden Set 001: the ten people in the official 2026-08-30
personnel briefing. Runtime API reads are SQLAlchemy-backed. Opt-in live-capable official
connectors are available for National Assembly member identity, legislative activity,
Central Election Commission local-election candidates/winners, NKIS policy-research
metadata, selected OpenDART corporate disclosures, and the ALIO item 4 current executive
roster; Golden tests remain fully offline.

## Setup

Requires Python 3.11+ (3.12 recommended) and Node.js 20+.

```bash
python -m pip install -e ".[dev]"
npm --prefix apps/web install
python -m alembic upgrade head
```

Copy `.env.example` to `.env` for local overrides. It contains placeholders only.

`CIVIC_BOOTSTRAP_MODE=runtime` is the normal mode. Runtime startup checks that Alembic is
at the current schema head and fails clearly if the database is missing or stale; it never
creates tables or seeds Golden Set 001. `CIVIC_BOOTSTRAP_MODE=golden` is reserved for an
explicit disposable development/test database and seeds only an empty migrated database.

## Commands

```bash
make test          # Python unit, integration, golden, and API tests
make lint          # Python lint
make typecheck     # Python typecheck
make quality       # deterministic golden quality report
make migrate       # apply Alembic migrations
make api-dev       # FastAPI at http://localhost:8000
make web-dev       # Next.js at http://localhost:3000
make web-verify    # web lint, typecheck, tests, production build
make verify        # all required checks
```

On Windows without `make`, run the commands shown in `Makefile` directly.

## Career facets

People are not assigned one permanent occupation type. Legislative, local-elected,
academic, corporate, civic/nonprofit, public-service, legal, military and diplomatic
history can coexist as time-bounded evidence-backed facets of the same person. See
`docs/architecture/CAREER_FACETS.md` for the canonical rules.

## National Assembly member connector

`OpenAssemblyMemberConnector` targets the official National Assembly Secretariat member
information Open API. Normal live use requires an `ASSEMBLY_API_KEY`; the key is injected
only into the outbound request and is never embedded in discovered/source URLs or stored
metadata.

For a review-only identity staging pass after installing the project:

```bash
ASSEMBLY_API_KEY=... civic-stage-assembly --name "홍길동" --page-size 10
```

The staging command emits identity-safe JSON candidates only. It does not write the
database, publish claims, or expose raw provider rows. Korean name, optional Hanja/English
aliases, birth date, current party, district, committee text, election metadata, and the
National Assembly member code are used as identity anchors for the existing resolver.

## Legislative activity staging

`OpenAssemblyBillConnector` uses the official `의원 발의법률안` dataset and scans the full
Assembly term for exact code-first participation when source coverage is complete:

```bash
ASSEMBLY_API_KEY=... civic-stage-legislative \
  --name "홍길동" --member-code "MONA_CD_VALUE" --age 22 \
  --page-size 1000 --max-pages 100
```

The same unfiltered term can be persisted with run/checkpoint/resume receipts after the target
database is migrated:

```bash
ASSEMBLY_API_KEY=... civic-stage-legislative \
  --age 22 --page-size 1000 --enumerate-bills \
  --database-url sqlite:///civic-intel.db
```

Use `--resume` with the same age and page size after a partial run. Persistent observations are
multi-person bill events keyed by `BILL_ID`; they do not create Persons or publish claims.

The exact scanner does not use the `PROPOSER` name filter. It fetches every expected page for
that Assembly and matches the reviewed identity by `MONA_CD` using:

- `RST_MONA_CD` for representative proposers, including comma-separated joint leads;
- `PUBL_MONA_CD` for co-proposers, with reviewed semicolon-separated codes.

Exact representative/co-sponsored counts are emitted only when pagination is complete,
source totals are stable, unique `BILL_ID` count matches the source total, no duplicate-page
anomaly exists, and both role-code fields are present/parseable on every bill row. Missing or
malformed code fields leave both exact counts unresolved rather than falling back to names.
Raw processing results such as `대안반영폐기`, `원안가결`, and `수정가결` remain distinct;
bill counts are descriptive and never a performance score or faction signal.

As of the 2026-08-30 review, the verified Open Assembly structured APIs do not provide full
`제안이유`/주요내용 text. Public datasets with those texts obtain them from
`likms.assembly.go.kr` bill-detail HTML. Issue #13 prohibits that HTML scraping, so Civic
Intel reports the proposal-reason source lane as `BLOCKED_NO_VERIFIED_STRUCTURED_SOURCE`
instead of inventing a `BPMBILLSUMMARY` connector or generating content from bill titles.

## Local elected-official staging

`NecCandidateConnector` and `NecWinnerConnector` use official Central Election Commission
candidate/winner APIs. Supported local-election scopes are governors, city/county/district
heads, metropolitan/provincial councilors, municipal/county/district councilors, historical
education councilors, and superintendents of education.

```bash
NEC_API_KEY=... civic-stage-local-election \
  --election-id 20260603 --type 4 --province "경기도" --district "테스트시"
```

The review output keeps NEC candidate ID, name/Hanja, birth date, election jurisdiction,
party, candidate number, public occupation, education/career strings and election outcome.
Candidate address is discarded before staging. Candidate-submitted education/career remains
explicitly labelled as submitted election-record data rather than independently verified
biographical FACT. A candidate absent from a partial winner page is `UNKNOWN`, not
silently classified as a losing candidate.

## Policy-research staging

`NkisResearchReportConnector` uses the official NKIS research-report Open API and requires an
issued `NKIS_API_KEY` for live requests.

```bash
NKIS_API_KEY=... civic-stage-policy-research \
  --publisher "산업연구원" --year-begin 2024 --year-end 2026
```

The output stages research-report metadata and a researcher candidate only when
`INCHARGE_NM` is an unambiguous single person. The NKIS publishing institution is retained
as an output property but is **not** assigned as that person's employer. Institute
employment/leadership requires a separate official institute profile or appointment source.
A repeated-topic review candidate requires at least two distinct staged outputs with the
same unambiguous researcher label, publisher and classification; it remains identity-
unresolved until normal Identity Resolution succeeds. NKIS abstract/fulltext storage, AI
use, excerpt display and commercial reuse remain disabled in V0 unless separately reviewed.

## Private-sector senior staging

`OpenDartCorporateConnector` supports selected official OpenDART disclosure APIs without
using the ordinary employee-status API for person discovery. Live requests require
`DART_API_KEY`.

```bash
DART_API_KEY=... civic-stage-corporate-dart \
  --dataset EXECUTIVE_STATUS \
  --corp-code 00123456 \
  --business-year 2026 \
  --report-code 11012
```

Supported datasets are:

- `EXECUTIVE_STATUS`
- `DIRECTOR_COMPENSATION_V2`
- `TOP_COMPENSATION_V2`
- `OFFICER_MAJOR_HOLDER_OWNERSHIP`

Executive-status rows may create senior-person candidates. Compensation is enrichment only
and never creates a Person by itself because the statutory top-compensation feed can include
non-executive employees. Officer/major-holder ownership is a dated securities disclosure,
not total wealth, effective company control, political influence or an automatic conflict of
interest. The OpenDART receipt number remains the pointer to the underlying company filing.

Senior CTO/research-center/business-unit leaders who do not appear as DART executives can
enter through a separately reviewed **company official profile** lane. That lane has no
generic crawler: the exact company domain must already have a reviewed SourcePolicy reference,
and ordinary employees fail closed.

OpenDART allows credentialed metadata retrieval under its service terms; V0 keeps fulltext,
AI use, excerpt display and commercial reuse disabled pending deployment-specific review.
No scheduled synchronization is enabled yet.

## ALIO public-institution executives

`AlioExecutiveDisclosureConnector` uses the exact institution, current-report and report-
document surfaces exposed by the official ALIO item 4 page. The L3 scope is every institution
in the unfiltered item 4 directory and the provider-ranked current disclosure for each one.

```bash
civic-stage-public-institutions --database-url sqlite:///civic-intel.db
```

Use `--resume` only after a partial run. The worker is sequential because ALIO publishes no
request-rate limit. It stores normalized executive metadata and exact snapshot provenance but
not raw report HTML, gender, disclosure-staff identities or phone numbers.

ALIO does not expose a stable executive-person identifier on this surface. The persisted
`disclosureNo:row-ordinal` key identifies a disclosure row only, so materialization remains on
the existing `REVIEW_REQUIRED` path and does not automatically create or merge Persons.

## Safety and source rights

All collection flows require a SourcePolicy. Golden Set 001 contains manually reviewed
metadata and short excerpts only; its policies are discovery-only or blocked, so tests
cannot fetch them. Official connectors are opt-in and credential-gated; tests mock all
network responses. Staging is review-only and does not mutate the canonical DB. The generic
HTTP connector remains dormant. The model has no private-family or precise-residence
publication fields. Workers cannot publish claims.

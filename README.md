# Civic Intel V0

Evidence-grounded public-official intelligence with policy-first ingestion and fully
traceable publication.

The offline baseline is Golden Set 001: the ten people in the official 2026-08-30
personnel briefing. Runtime API reads are SQLAlchemy-backed. Opt-in live-capable official
connectors are available for National Assembly member identity, legislative activity,
Central Election Commission local-election candidates/winners, and NKIS policy-research
metadata; Golden tests remain fully offline.

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

`OpenAssemblyBillConnector` uses the official `의원 발의법률안` dataset and stages bill
metadata without writing the canonical database:

```bash
ASSEMBLY_API_KEY=... civic-stage-legislative \
  --name "홍길동" --member-code "MONA_CD_VALUE" --age 22 --page-size 100
```

The output preserves bill ID/title, proposal date, committee, processing result,
representative proposer and co-proposers. Exact representative-sponsored counts are emitted
only when the filtered result has complete page coverage. Complete co-sponsorship counts are
left unresolved in this stage because the representative-proposer search endpoint alone does
not establish full co-sponsor coverage. No faction/계파 classification is produced.

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

The reviewed National Assembly and NEC SourcePolicies permit policy-approved fetch/metadata
use. NKIS is metadata-only with stricter rights. No scheduled synchronization is enabled yet.

## Safety and source rights

All collection flows require a SourcePolicy. Golden Set 001 contains manually reviewed
metadata and short excerpts only; its policies are discovery-only or blocked, so tests
cannot fetch them. Official connectors are opt-in and credential-gated; tests mock all
network responses. Staging is review-only and does not mutate the canonical DB. The generic
HTTP connector remains dormant. The model has no private-family or precise-residence
publication fields. Workers cannot publish claims.

# Civic Intel V0

Evidence-grounded public-official intelligence with policy-first ingestion and fully
traceable publication.

The offline baseline is Golden Set 001: the ten people in the official 2026-08-30
personnel briefing. Runtime API reads are SQLAlchemy-backed. One opt-in live-capable
official connector is available for National Assembly member information; Golden tests
remain fully offline.

## Setup

Requires Python 3.11+ (3.12 recommended) and Node.js 20+.

```bash
python -m pip install -e ".[dev]"
npm --prefix apps/web install
python -m alembic upgrade head
```

Copy `.env.example` to `.env` for local overrides. It contains placeholders only.

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

For lower-level connector inspection:

```bash
ASSEMBLY_API_KEY=... python - <<'PY'
from packages.connectors import OpenAssemblyMemberConnector

connector = OpenAssemblyMemberConnector(name="홍길동", page_size=10)
document = connector.fetch(connector.discover()[0])
for member in connector.parse_members(document):
    print(member)
PY
```

The reviewed SourcePolicy permits fetch/metadata use under the official dataset's
unrestricted-use license, but V0 deliberately does not retain raw API response fulltext
or send it to AI because member rows may include contact fields unnecessary for identity
resolution. No scheduled synchronization is enabled yet.

## Safety and source rights

All collection flows require a SourcePolicy. Golden Set 001 contains manually reviewed
metadata and short excerpts only; its policies are discovery-only or blocked, so tests
cannot fetch them. The National Assembly connector is opt-in and credential-gated; tests
mock all network responses. Staging is review-only and does not mutate the canonical DB.
The generic HTTP connector remains dormant. The model has no private-family or
precise-residence publication fields. Workers cannot publish claims.

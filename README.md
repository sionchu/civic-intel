# Civic Intel V0

Evidence-grounded public-official intelligence with policy-first ingestion and fully
traceable publication.

The offline baseline is Golden Set 001: the ten people in the official 2026-08-30
personnel briefing. Runtime API reads are SQLAlchemy-backed. No live connector is enabled.

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

## Safety and source rights

All collection flows require a SourcePolicy. Golden Set 001 contains manually reviewed
metadata and short excerpts only; its policies are discovery-only or blocked, so tests
cannot fetch them. The generic HTTP connector remains dormant and no live connector is
enabled. The model has no private-family or precise-residence publication fields.
Workers cannot publish claims.

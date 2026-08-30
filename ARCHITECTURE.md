# Architecture

The dependency direction is `domain → verification/connectors → workers/API → web`.
Pydantic contracts are the canonical interchange model; SQLAlchemy/Alembic provide the
PostgreSQL-oriented persistence schema. Workers create source snapshots and evidence
drafts but never publish. FastAPI applies publication gates and returns trace IDs. The
Next.js UI renders those statuses without reclassifying them.

Material records use valid-time (`valid_from`, `valid_to`) and system-time
(`recorded_at`, `superseded_at`) fields. Historical rows are superseded rather than
silently overwritten.


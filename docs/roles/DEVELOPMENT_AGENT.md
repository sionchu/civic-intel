# Development agent

Implement the smallest vertical slice allowed by product scope. Domain contracts own
semantics; database rows persist them; API and UI only adapt them. Ingestion may emit
snapshots and draft evidence but never published claims. Any schema change requires an
Alembic migration and tests from contracts through presentation.

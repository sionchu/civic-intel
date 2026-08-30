# Repository instructions

Read `ARCHITECTURE.md`, `docs/INDEX.md`, `docs/product/V0_SCOPE.md`, the role file
matching the work, `docs/workflows/CHANGE_CONTROL.md`, and
`docs/workflows/DEFINITION_OF_DONE.md` before changing behavior.

## Non-negotiable invariants

- Preserve `rendered item → Claim → ClaimEvidence → Source → SourcePolicy`.
- Displayability and truth assertion are separate. A published UNKNOWN is an explicit
  unresolved result and must never be promoted to FACT.
- Every source-processing path starts with SourcePolicy. Technical access is not permission.
- Identity-specific output requires RESOLVED identity.
- Do not model private-family discovery or precise residence in publishable contracts.
- Workers create evidence drafts; only verification gates authorize publication.

## Change discipline

- Extend canonical contracts in place; never add `v2`, `new`, or `final` alternatives.
- Add an Alembic migration for persistence changes and deterministic regression coverage.
- Keep dependencies directed from domain through verification/connectors to API/workers/UI.
- Run narrow checks while working and `make verify` before completion.

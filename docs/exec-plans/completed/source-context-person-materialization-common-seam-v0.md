# Source-context Person materialization common seam v0

Status: COMPLETED 2026-09-28.

Base: `e06cbb3`.

## Objective

Remove proven execution-level duplication between ALIO and NEC source-context Person materializers
without generalizing source-specific identity, eligibility, checkpoint or Claim semantics.

This is a maintenance slice, not a new ingestion framework. No new source, schema, migration,
public route, publication authority or operational database write is allowed.

## Proven common invariant

Both ALIO and NEC currently perform the same persistence sequence after a source-specific preflight:

1. validate an exact 64-hex receipt SHA;
2. take a source-specific PostgreSQL advisory lock plus the same four table locks;
3. recompute the source-specific preflight inside the transaction;
4. fail closed when the receipt changed;
5. return NOOP when no CREATE items remain;
6. persist one Person, PersonObservationLink, Claim and ClaimEvidence per selected packet;
7. return deterministic created counts without source fetch or publication.

Eligibility, packet construction, checkpoint coverage and predicate semantics remain source-specific.
## Owned paths

- `packages/persistence/source_context_person_materialization.py`
- `packages/persistence/alio_person_materialization.py`
- `packages/persistence/nec_person_materialization.py`
- focused ALIO/NEC tests if required
- this plan and HANDOFF closure only

## Acceptance

- no source-specific eligibility rule moves into the common module;
- existing dry-run and commit receipt payloads remain byte/semantic compatible;
- ALIO and NEC atomicity, stale-receipt, NOOP and idempotency regressions pass unchanged;
- Ruff and mypy pass for touched Python paths;
- full `make verify` passes before closure;
- final diff removes more duplicated execution machinery than it adds abstraction surface;
- no operational DB write, collection, identity resolution or Claim publication occurs.

## Follow-on, not in this slice

Repository/admin predicate branching and season defaults require separate evidence and should not be
mixed into this extraction. Gukgam 41-item Claim review and MOIS 70-item Organization review also
remain separate human/operator boundaries.

## Closure evidence

- Added one source-neutral persistence seam for receipt SHA validation, PostgreSQL locking,
  packet persistence and canonical row-to-contract conversion.
- ALIO/NEC eligibility, checkpoint coverage, identity construction and Claim predicates remain in
  their source-specific modules.
- Focused Ruff/mypy and ALIO/NEC regressions passed.
- Read-only Mac PostgreSQL dry-runs matched exact pre-change `e06cbb3` receipt SHA values for both
  ALIO and NEC against the same operational dataset.
- Full repository verification passed: `639 passed / 3 skipped`, Golden Set passed, Web `26/26`,
  and the Next standalone production build completed.
- No source fetch, operational DB write, identity resolution, Claim publication, deployment or
  schema change occurred.

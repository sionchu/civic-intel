# Collector Runtime Hardening v1

Status: ACTIVE — local verification complete; CI pending
Started: 2026-09-17
Repository baseline: `3843cccf39565db20e7c997ac8378fd2f99542f2`

## Objective

Make the existing source-specific `civic-sync assembly-roster` boundary safe to run from
source trees, installed wheels, and the production container artifact without changing the
staging environment or adding a collector service. Preserve the existing
`SourcePolicy → Source → SourceSnapshot → FeederObservation → Claim/Evidence` path.

## Scope and guardrails

- Staging rehearsal remains stopped. No staging execution, deployment, database write, Railway
  resource, domain, plan, credential, migration, or reload is part of this milestone.
- Use fixture/mock transport only; do not call the live Assembly API.
- Do not add a scheduler, cron, generic sync framework, second raw-payload store, or API-service
  acquisition credential.
- Keep `ASSEMBLY_API_KEY` in a future private acquisition boundary only; it must not be added to
  the API serving service.
- Runtime startup remains schema-readiness verification only; it never creates or migrates a
  database.

## Acceptance criteria

1. The runtime expected schema revision is a canonical `0006` contract, independent of the
   installed module's filesystem location.
2. CI/test proves the runtime contract equals the actual Alembic head.
3. Source-tree, installed-wheel, non-repository-cwd and container artifact checks reach the
   normal redacted credential boundary instead of failing on migration-path resolution.
4. Alembic/config/runtime precondition failures are classified as
   `database_or_precondition`; public receipts contain no raw exception, path, URL or secret.
5. `civic-sync assembly-roster` remains the normal periodic/fresh reconciliation command.
6. `civic-sync assembly-roster --resume` is only interrupted/partial-run recovery. A completed
   checkpoint fails closed without fetching or changing its observation manifest.
7. Partial checkpoint recovery, idempotent normal rerun, missing-key behavior and existing
   atomic page/checkpoint regressions remain green.
8. Full Python, Ruff, mypy, quality, web and CI verification is recorded. Docker is recorded as
   executed or explicitly unavailable on the verification host.

## M0 — baseline root-cause evidence

- The source-tree `python -m workers.sync assembly-roster` run against a migrated disposable
  SQLite database reached a redacted `MissingAssemblyApiKey` receipt with phase
  `source_fetch_parse_or_coverage`.
- A wheel installed into a temporary prefix and executed from outside the repository loaded
  `packages.persistence.repository` and `workers.sync` from the installed `site-packages`
  directory. The installed entrypoint was `civic-sync`.
- In the baseline wheel, `_expected_schema_revision()` resolved the migration root below
  installed `site-packages`; that `migrations` directory was absent. Alembic raised
  `alembic.util.exc.CommandError` (`Path doesn't exist ... site-packages\migrations`) before
  `SourceRun` creation. The CLI emitted `code=CommandError`, `phase=unexpected`,
  `run_id=null`, and `committed_count=0`, matching the staging rehearsal evidence.
- Docker CLI is not installed on this verification host. The required Docker artifact check is
  retained as a separate verification item and must not be represented as a pass unless run.

## M1 — runtime and CLI hardening

- Replace source-tree Alembic path discovery in `packages.persistence.repository` with the
  canonical expected revision constant `0006`.
- Add a migration-head regression that resolves `migrations` only in the test/CI repository
  context and asserts equality with the runtime constant.
- Classify Alembic `CommandError` with the existing `database_or_precondition` receipt phase.
- Clarify the `--resume` CLI help and lock completed-checkpoint behavior with a fixture-backed
  regression; retain the existing partial recovery implementation unchanged.

## M2 — artifact and verification matrix

Run and record, without live staging access:

- normal source-tree execution;
- installed wheel execution from a non-repository directory;
- disposable completed-checkpoint normal sync;
- disposable completed-checkpoint `--resume` failure;
- disposable partial-checkpoint `--resume` recovery;
- missing-key and redacted-receipt checks;
- Docker image execution if Docker becomes available;
- full project verification and CI result.

### Local result

- Source-tree `python -m workers.sync assembly-roster` against a disposable migrated SQLite
  database reached the redacted `MissingAssemblyApiKey` boundary with
  `phase=source_fetch_parse_or_coverage`.
- The rebuilt wheel was installed into a temporary prefix. From a non-repository directory,
  the installed `civic-sync` loaded `packages.persistence.repository` from `site-packages`,
  returned `expected_schema_revision=0006`, and reached the same redacted missing-key receipt.
- Fixture/mock regressions cover normal completed-checkpoint reconciliation, unchanged rerun,
  completed-checkpoint `--resume` fail-closed behavior, partial `--resume` recovery, missing
  credential handling, redaction and atomic checkpoint persistence.
- Disposable Alembic upgrade → downgrade → upgrade ended at `SCHEMA_HEAD=0006`.
- Local full verification passed: `355 passed, 1 skipped, 4 warnings`; Ruff passed; mypy passed
  for `60 source files`; Golden quality passed; web lint/typecheck/9 tests/production build
  passed; and the Railway specification TypeScript check passed.
- Docker is unavailable on the local host. The CI Verify workflow now builds the API image and
  runs the installed-entrypoint check from `/tmp`; no local Docker result is claimed.

## Future deployment shape (evaluation only)

If a future staging rehearsal is approved, evaluate a private, one-shot collector/job boundary
using the same repository/image with `DATABASE_URL` and `ASSEMBLY_API_KEY`, no public domain,
and manual invocation of `civic-sync assembly-roster`. Cron/scheduler, resource creation and
API-service credential injection remain separate decisions.

## Current checkpoint

M0 baseline reproduction, M1 runtime/CLI hardening and the local M2 matrix are complete. The
source-tree versus installed-wheel difference and exact Alembic `CommandError` path-resolution
failure are recorded above. Staging remains untouched; CI is the only remaining verification
step before closure.

## Next concrete action

Create the coherent delivery commit, push it to `origin/master`, and record the CI Verify result
including the container entrypoint regression.

# HANDOFF

## Objective

Continue `sionchu/civic-intel` from the current `master` and decide whether the Government Public
Ethics Committee / MPM retired-public-official employment-review feeder can safely reach L3.

## Scope

Source-contract validation only: official universe, pagination/coverage, record identity,
attachments, date and correction semantics, use conditions and automated collection. Do not do
person-by-person enrichment or add parallel persistence abstractions.

## Acceptance criteria

- latest `master` is confirmed before work;
- governing repository and batch-ingestion documents are read;
- the seven existing L3 feeders and CleanEye blocked baseline are preserved;
- the official employment-review source is either implemented through the canonical batch path or
  its exact blockers are documented; and
- observed tests and non-executed work are separated.

## Completed

- Confirmed `HEAD` and `origin/master` at `64ebba32f4ad2b44e1b5fa85c547cbd560729f9f`.
- Reconstructed the existing offline employment-review parser/stager and canonical batch
  persistence boundary.
- Reviewed current MPM board, MPM attachments, PETI result index/detail flow, robots and MPM
  copyright policy.
- Determined that the source contract is insufficient for L3; no live code or migration was
  added.
- Added the source-gate ExecPlan at
  `docs/exec-plans/active/government-public-ethics-employment-review-l3.md`.

## Current checkpoint

The lane remains `L1 CONTRACT_STAGED; L3 promotion blocked`. The MPM `취업` category is a mixed
125-post, 9-page board; PETI is a mixed 315-post, 32-page result index. MPM result PDFs expose
packet-local numbered rows without a provider case identifier or per-row review date. Correction
and reuse terms are not sufficient for automated normalized storage.

## Decisions and reasons

- Keep `EmploymentReviewEvent`, `SourceRun`, `SourceCheckpoint` and `FeederObservation` as the
  only future implementation path.
- Do not use `cntId:attachment:row ordinal` as an L3 identity until the provider confirms row
  stability across corrections.
- Do not treat technical reachability, the PETI internal AJAX call or the MPM RSS feed as a
  permission or complete source contract.
- Keep CleanEye at `L0 RESEARCHED; BLOCKED`.

## Verification evidence

- `git fetch --prune origin master`: remote remained at the expected SHA.
- Final read-only `git ls-remote origin refs/heads/master` also returned
  `64ebba32f4ad2b44e1b5fa85c547cbd560729f9f`; a later fetch refresh could not write
  `.git/FETCH_HEAD`, so no local ref update was needed.
- `pytest tests/test_civil_service_feeder.py -q`: `10 passed`.
- `.venv\Scripts\python.exe -m pytest -q --disable-warnings`: 266 collected tests reached
  `[100%]` and exited 0.
- `.venv\Scripts\python.exe -m ruff check packages workers apps tests`: passed.
- `.venv\Scripts\python.exe -m mypy packages workers apps/api`: no issues in 51 source files.
- `.venv\Scripts\python.exe -m packages.verification.quality`: all quality checks passed.
- `npm --prefix apps/web run lint`, `typecheck`, `test`, and `build`: all exited 0; the UI
  test suite passed 2 tests and the production build completed.
- MPM August and July result PDFs were rendered and visually inspected; the August packet has
  four pages and 94 numbered rows.

## Not executed

- no live employment-review enumerator or parser;
- no database migration or batch run;
- `make verify` itself was not executable because GNU Make is unavailable in this Windows
  environment; its lint, typecheck, test, quality and web verification commands were run
  directly with the project runtimes.

## Blockers

The official source must provide or authorize a typed complete result universe, stable case/row
identity, per-row date semantics, correction/version behavior, machine-readable or licensed
attachment use, request pacing and storage/reuse terms.

## Modified files

- `HANDOFF.md`
- `docs/INDEX.md`
- `docs/architecture/BATCH_INGESTION.md`
- `docs/architecture/CLEANEYE_LOCAL_PUBLIC_INSTITUTION_FEEDER.md`
- `docs/architecture/FEEDER_SOURCE_COVERAGE.md`
- `docs/exec-plans/active/batch-ingestion-l3.md`
- `docs/exec-plans/active/cleaneye-local-public-institution-executives-l3.md`
- `docs/exec-plans/active/government-public-ethics-employment-review-l3.md`
- `docs/exec-plans/active/opendart-private-sector-executives-l3.md`

## Next concrete action

Obtain the official MPM/PETI source-owner contract response. If it covers every stop condition,
implement one source-specific connector on the existing batch foundation; otherwise retain L1
and do not add a live feeder.

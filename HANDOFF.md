# HANDOFF

## Objective

Improve Civic Intel acquisition methodology using OpenWatch/opengirok as references, not feeders.

## Scope

Architecture-only audit: official composition, document normalization, information requests,
bounded human review, field provenance, identity, corrections and ogk tooling. No ingestion.

## Acceptance criteria

Six acquisition modes with rights/provenance/identity/version/QA gates; distinguish L3 automation
blocks from conditional human-assisted L1/L2 utility; preserve actual code/maturity and verify DoD.

## Completed

- Fetched latest master; baseline local/origin HEAD matched
  `2332755777e94eef398831646fe3dc7507d5a6bb`; worktree was clean.
- Read governing documents and actual Source/Policy/Snapshot/Observation/Run/Claim contracts,
  shared repository transaction, materialization and EmploymentReviewEvent requirements.
- Inspected official OpenWatch field dictionaries, information-request methodology, information
  center's bounded citizen project, localcouncil catalog/correction notes and ogk code at
  `7d2295323a8970b2d7a9a60c10fb9665638bf1a1`.
- Integrated the playbook into existing FEEDER_SOURCE_COVERAGE.md; no parallel document.
- Updated batch/product semantics and three historical source-gate pointers to avoid implying
  that all L1/L2 work requires an automated full-universe contract.

## Current checkpoint

Methodology audit complete. MPM remains L1 CONTRACT_STAGED with L3 blocked; assets and CleanEye
remain L0 RESEARCHED; BLOCKED. Seven existing L3 rows are unchanged. Conditional human-assisted
paths are designed, not implemented or exercised.

## Decisions and reasons

- Field authority and time matter more than the aggregator's brand; retain official origin and
  analyst-normalized representation separately.
- L2 human-assisted status requires a permitted reproducible packet import with fixtures,
  human comparison, provenance, shared persistence and idempotency proof, not a download.
- Unknown/missing/refused/not-held states stay distinct; own dataset IDs are not Person authority.
- No new source-mode enum, schema, importer, dependency, raw store or per-person main path.
- Current HttpUrl, per-domain policy and single-snapshot constraints are explicit design gates.
- ogk's request inventory/status/attachment stages are useful references; its remote upload,
  database and account workflow are not adopted. Code MIT does not license response data.
- Exact dataset rights differ: the localcouncil catalog/project notice has noncommercial terms;
  do not substitute OpenWatch's general data license.

## Verification evidence

Executed locally on 2026-09-12:

- `.venv\Scripts\python.exe -m pytest -o addopts='' -q`: 266 passed, 4 warnings, 88.69s.
- `.venv\Scripts\python.exe -m ruff check apps packages workers tests`: passed.
- `.venv\Scripts\python.exe -m mypy packages workers apps/api`: 51 files, no issues.
- `.venv\Scripts\python.exe -m packages.verification.quality`: all Golden Set checks passed.
- `npm --prefix apps/web run lint`, `typecheck`, `test`, `build`: passed; 2 tests.
- PowerShell assertions: six mode headings present, local Markdown targets exist, diff is
  documentation-only, seven L3 matrix rows exactly equal the baseline.
- `git diff --check`: passed. Final diff reviewed for maturity, rights and implementation drift.
- GNU Make unavailable; Makefile constituent commands were executed directly.
  Local evidence only, not GitHub CI. Existing deprecation/parent-lockfile warnings remain.

## Not executed

No fresh dataset QA/download, official response retrieval, request submission, provider contact,
ogk install/login/run, schema change, migration, importer or Person creation.
Firecrawl CLI was unavailable; standard web/read-only HTTP tools inspected public methodology
and source code instead. chatgpt2codex reported no registered civic project; local tools used.

## Blockers

Future packet use still requires exact acquisition/storage permission and representable origin
provenance. A human review cannot supply absent identity or dates. L3 gates remain unchanged.

## Modified files

FEEDER_SOURCE_COVERAGE.md (playbook), BATCH_INGESTION.md, V0_SCOPE.md, INDEX.md,
asset/CleanEye source-gate documents, the three active source-gate plans and this HANDOFF.
No product code, tests, dataset files or dependency manifests changed.

## Next concrete action

Run one human-assisted L1 pilot for a single MPM result packet: first record packet-specific
rights and fixed page/row provenance, then deterministic anonymous-row extraction and human
comparison; do not create Persons, invent review dates or claim L3.

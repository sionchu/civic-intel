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
  `7b3c98e85575e603b6bb6449d9796fa83aedc3bb`; worktree was clean.
- Read governing documents and actual Source/Policy/Snapshot/Observation/Run/Claim contracts,
  shared repository transaction, materialization and EmploymentReviewEvent requirements.
- Inspected official OpenWatch field dictionaries, information-request methodology, information
  center's bounded citizen project, localcouncil catalog/correction notes and ogk code at
  `7d2295323a8970b2d7a9a60c10fb9665638bf1a1`.
- Integrated the playbook into existing FEEDER_SOURCE_COVERAGE.md; no parallel document.
- Updated batch/product semantics and three historical source-gate pointers to avoid implying
  that all L1/L2 work requires an automated full-universe contract.
- Ran a bounded MPM `cntId=422` rights preflight and recorded its official packet manifest plus
  the fixed `{detail URL, boardId, cntId, attachment reference, page, packet-local row}`
  provenance locator. The attachment had no item-level KOGL/reuse grant, so no bytes, fulltext or
  normalized row were persisted and the extraction/review phase did not start.
- Rechecked the official MPM organization and copyright pages; public `취업심사과` and copyright
  policy contact leads are now recorded as inquiry routes only, not as a rights grant.

## Current checkpoint

Methodology audit and the MPM single-packet rights preflight are complete. MPM remains
L1 CONTRACT_STAGED with L3 blocked; assets and CleanEye remain L0 RESEARCHED; BLOCKED. Seven
existing L3 rows are unchanged. The human-assisted path is rights-gated and was not exercised
past packet metadata/provenance recording.

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
- Public reachability and an attachment download control do not authorize packet persistence;
  an unmarked MPM attachment requires source-owner agreement before deterministic extraction or
  normalized reuse.
- The official contact routes reduce discovery uncertainty but do not satisfy the required
  packet-specific written permission or storage/republication boundary.

## Verification evidence

Executed locally on 2026-09-12:

- `.venv\Scripts\python.exe -m pytest -o addopts='' -q`: 266 passed, 4 warnings, 88.69s.
- `.venv\Scripts\python.exe -m ruff check apps packages workers tests`: passed.
- `.venv\Scripts\python.exe -m mypy packages workers apps/api`: 51 files, no issues.
- `.venv\Scripts\python.exe -m packages.verification.quality`: all Golden Set checks passed.
- `npm --prefix apps/web run lint`, `typecheck`, `test`, `build`: passed; 2 tests.
- PowerShell assertions: six mode headings present, local Markdown targets exist, diff is
  documentation-only, seven L3 matrix rows exactly equal the baseline.
- Read-only MPM probes: official `cntId=422` detail returned the packet title, publication date,
  attachment filename and `FILE_...`/storage reference; the direct attachment response was
  inspected in memory for MIME only and was not written to disk.
- `git diff --check`: passed. Final diff reviewed for maturity, rights and implementation drift.
- GNU Make unavailable; Makefile constituent commands were executed directly.
  Local evidence only, not GitHub CI. Existing deprecation/parent-lockfile warnings remain.

## Not executed

No persistent dataset download or QA, deterministic packet extraction, official response request,
provider contact, permission request/response, ogk install/login/run, schema change, migration,
importer or Person creation.
The public MPM attachment response was fetched in memory for a bounded MIME probe only and was
not retained.
Firecrawl CLI was unavailable; standard web/read-only HTTP tools inspected public methodology
and source code instead. chatgpt2codex reported no registered civic project; local tools used.

## Blockers

The selected packet still requires exact acquisition/storage permission before bytes or normalized
values can be retained. Official inquiry routes are known, but no permission request or source-owner
response exists. A human review cannot supply absent identity or dates. L3 gates remain unchanged.

## Modified files

The active MPM source-gate plan and this HANDOFF only. No product code, tests, dataset files or
dependency manifests changed.

## Next concrete action

Request written MPM permission or an explicit item-level reuse license for the recorded `cntId=422`
packet through the documented source-owner routes, then run the deterministic anonymous-row
extraction and human comparison without creating Persons, inventing review dates or claiming L3.

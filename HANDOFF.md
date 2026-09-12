# HANDOFF

## Objective and scope

Complete the employment-review source-gate publication, then evaluate National Assembly
asset disclosure as the first independent OpenWatch/opengirok curated-source lane.
Do not implement other lanes or create family/staff/donor Persons.

## Completed checkpoints

- Employment-review nine-file diff reviewed with no unrelated changes, committed as
  `1ac20dcadb8257af354b3e48a04a9a8eec6b00de` and pushed to master.
  Local HEAD, origin/master and live remote matched; worktree was clean before asset research.
- Read current governing docs and actual canonical asset contracts, SQLAlchemy tables,
  repository, materialization gate, API and tests.
- Completed OpenWatch/opengirok/Gazette reconnaissance and aggregate-only QA:
  thirteen opengirok workbooks, three recent OpenWatch asset workbooks and one member workbook.
- Added `docs/architecture/NATIONAL_ASSEMBLY_ASSET_DISCLOSURE.md`, linked source-gate plan,
  finite research helper/tests and aggregate evidence. No raw workbook or personal row saved.
- Seven existing L3 feeders preserved.

## Current decision

National Assembly asset disclosure: **L0 RESEARCHED; BLOCKED**.
Employment review: **L1 CONTRACT_STAGED; L3 promotion blocked**.
CleanEye: **L0 RESEARCHED; BLOCKED**.

Public bulk data and positive curator data-use language exist. L3 is blocked by unreconciled
release/origin coverage, inadequate disclosure/item correction semantics and an unvalidated
permitted complete machine-access route. OpenWatch's August 2024 link aliases March 2024;
its current directory includes 2026 while the asset docs and opengirok catalog stop at 2025.
Current-value zero was counted as present, not missing, in final QA. Ordinals hide repeated
contents; byte-hash churn on XLSX export is not proof of data corrections.

## Architecture decisions

- AssetDisclosure/AssetItem and their DB tables already exist, but asset persistence/
  materialization and the empty API projection are not a working feeder.
- Preserve separate Gazette origin and opengirok/OpenWatch curated Sources and policies,
  then exact snapshot provenance into Civic Intel observations and ClaimEvidence.
- Reuse SourceRun/SourceCheckpoint/FeederObservation and the shared repository if reopened.
- Prefer official assembly_mona_cd anchors; curator ID/crosswalk presence is not canonical
  Person authority. No name-only links, asset-row Person IDs or private-family materialization.
- No persistent model/migration or runtime dependency is justified at this blocked gate.
- Future votes/local-council/contribution lanes are documented only.

## Executed local verification — 2026-09-12

- `.venv\Scripts\python.exe -m ruff check apps packages workers tests docs/research`: passed.
- `.venv\Scripts\python.exe -m mypy packages workers apps/api`: passed, 51 source files.
- `.venv\Scripts\python.exe -m pytest -o addopts='' -q`: **266 passed**, 4 deprecation
  warnings, 95.46 seconds. Existing migration regressions are included.
- `.venv\Scripts\python.exe -m packages.verification.quality`: passed; exact ten-person
  Golden Set, evidence traceability, identity and privacy gates intact.
- Bundled analysis Python `-m unittest discover -s docs/research -p 'test_*.py' -v`:
  **3 passed**; zero/missing, ordinal-hidden duplicates and exact-code crosswalk.
- `npm --prefix apps/web run lint`, `typecheck`, `test`, `build`: passed;
  **2 web tests**, production build complete. Next.js noted an ignored parent pnpm lockfile;
  no parent/workspace configuration was changed.
- Finite workbook QA exited 0 for all seventeen sources; aggregate report carries source
  URLs, timestamps and hashes. Immediate 2026 row-content repeat was stable.
- `git diff --check`: passed before final staging; final staged diff audited.
- GNU Make unavailable: its constituent verify commands above were run directly.
  These are local results, not a claim of GitHub CI status.

## Not executed

No live production feeder, canonical batch ingestion, Person link, migration, provider contact,
raw-data redistribution or implementation of subsequent lanes. No full annual Gazette-PDF
reconciliation; no historical amendment-rate measurement. No generic crawler or Firecrawl
runtime dependency.

## Next concrete action

Obtain one bounded source-contract response/release specification from OpenWatch/opengirok
covering corrected per-release origin manifest and counts, disclosure/item version rules,
official-code crosswalk provenance and permitted bulk reuse. Reopen only when the source-gate
criteria are met; otherwise keep this lane blocked.

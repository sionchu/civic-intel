# National Assembly asset-disclosure source gate

## Status

2026-09-12: research complete; **L0 RESEARCHED; BLOCKED**. This is a source-gate
record, not an approved L3 implementation plan. Reopening requires the conditions below.

Methodology follow-up (2026-09-12): see the source acquisition playbook in
`docs/architecture/FEEDER_SOURCE_COVERAGE.md`. This plan's full-universe gates apply to L3;
a rights-approved official Gazette packet may separately be evaluated for human-assisted L1/L2.
No OpenWatch ingestion or packet importer is implemented; actual maturity remains L0.

## Objective and scope

First reconcile and publish the existing employment-review source-gate work. Then evaluate
one independent curated-source lane: National Assembly asset disclosures from OpenWatch,
opengirok and the original National Assembly Gazette. Do not implement other candidate lanes,
create private-family/staff/donor Persons, or build a financial framework.

## Baseline and completed work

- [x] Read current governing documents, active plans, source/identity/DB architecture, batch
  skill and actual domain/repository/API/test code before designing changes.
- [x] Review the nine-file employment-review diff; no unrelated changes. Commit
  `1ac20dcadb8257af354b3e48a04a9a8eec6b00de` pushed to master. Local HEAD,
  origin/master and live remote matched; worktree was clean before asset research.
- [x] Preserve seven L3 feeders, employment-review L1 blocked and CleanEye L0 blocked.
- [x] Inspect official curator docs, live directory, Swagger, pinned opengirok catalog,
  Google Sheet exports, origin detail and rights/access notices.
- [x] Run finite aggregate QA across thirteen opengirok and four OpenWatch workbooks.
  No raw workbook or row values saved. Zero-vs-missing and ordinal-hidden duplicates checked.
- [x] Audit existing AssetDisclosure/AssetItem contracts and tables, empty API projection
  and missing asset persistence/materialization workflow. No missing model was invented.
- [x] Document three-layer provenance, limited-family semantics, exact-code identity boundary
  and subsequent lanes as documentation only.
- [x] Revalidate the official National Assembly Gazette index with the `재산` title filter:
  61 matching publications across 7 pages, including the 2026-54, 2025-51, 2024-107 and
  2024-36 origin candidates. This confirms publication-level availability only and does not
  close row identity, correction/version or rights-route gates.

## Results and evidence

Canonical decision: [source-contract audit](../../architecture/NATIONAL_ASSEMBLY_ASSET_DISCLOSURE.md).
Measured QA: [aggregate report](../../research/assembly_asset_qa_2026-09-12.json).
Reproduction: run `assembly_asset_qa.py --include-opengirok` with the bundled analysis Python
and preinstalled openpyxl. This is opt-in finite research, not a runtime command or scheduler.
The report records individual timestamps/URLs/hashes; live mutable sources may later differ.

There is usable public bulk data and positive data-use language. The decision is not a blanket
copyright prohibition: coverage, corrected releases, stable observation reconciliation and a
reviewed automated route remain insufficient. Provider permanent IDs are not universally
required if a validated source-derived key/version strategy can meet the same semantics.

## Verification

- Research helper offline synthetic tests: 3 passed (zero/missing, duplicate ordinals,
  exact-code-only crosswalk).
- Ruff including the research helper/tests: passed.
- Mypy: no issues in 51 source files.
- Golden Set quality: passed, ten-person roster and all publication/privacy checks intact.
- Full Python and web DoD: final execution results recorded in HANDOFF.md.
- No production batch run, schema change, live feeder or Person linkage was executed.
- GNU Make unavailable; run its exact constituent targets with installed project runtimes.

## Reopening contract

Obtain a bounded provider response/release specification covering the corrected per-release
manifest (including 2024 August and 2026 origin references), Gazette reconciliation counts,
disclosure/item keys and amendment rules, official-code crosswalk provenance, and permitted
bulk access/storage/redistribution. No provider has been contacted by this task.

Only after those L3 gates pass, write an automated implementation ExecPlan for one staged slice,
then prove full bounded enumeration, transactionally committed checkpoints, resume,
idempotency/corrections, privacy and publication tests on the existing batch foundation.
Until then, stop safely without implementing another candidate feeder.

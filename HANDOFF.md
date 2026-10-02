# HANDOFF

## Objective

Reapply the approved architecture refactor and prepare the selected dedicated one-shot collector
on the Mac/SSD. The local architecture work order is complete. The owner approved the exact
one-shot Assembly acquisition and Windows source-key reuse; operational launcher validation remains.

## Scope

Preserve Evidence Core, current Organization/source reachability, UNKNOWN, admin signing/locking/
receipts, source-context identity gates and schema compatibility. Operational grant is limited
to the single current Assembly roster and allocated fresh target; no identity/publication/schedule.

## Acceptance criteria

Pure domain, application orchestration, one UoW/session, capability repositories, shared proven
acquisition lifecycle, explicit CLI effects, coherent reads, bounded context, independent review
and executed local verification. All are satisfied; details are in the final receipt.

## Completed

All five milestones in docs/exec-plans/completed/architecture-current-master.md. Eight adapters,
nine enumerators sharing SourceLifecycle, 37 CLI routes, startup readiness only, policy-first
identity, local trace/run correlation, old paths removed and full histories retained.
Separate collector proposal and Mac runtime installation are documented. Only disposable,
credential-free offline acquisition checks ran; no live collector was launched.
The approved single source key has been delivered privately from Windows to Mac without printing
its value or transferring other `.env` values.

## Current checkpoint

Branch codex/architecture-current-master, isolated architecture-current-master worktree.
Base/remote master 77e2767ab043738f00b8dd38be8d99803e5ad7bc; verified source
333aa26bda5f1110e53190f27de0c62a0f43cb30 for the installed bounded candidate; initial
architecture source 0ae6945 is retained in the earlier receipt.
Original master and its modified packages/domain/contracts.py remain untouched.
Mac bounded runtime: /Users/lee/Developer/civic-intel-collector-20261001/bounded-333aa26,
Python 3.12.14, pinned wheel. External /Volumes/data is APFS on USB 10 Gb/s. Owner node approval
resolved remote storage access; mkdir/fsync/readback/SHA/rename and SSD schema/CLI checks passed.
Fresh target mac-ssd-assembly-one-shot-333aa26 is schema 0008, mode 0600, with zero data/run rows.

## Decisions and reasons

Transform current semantics rather than replacing them from an older branch. Keep SQL rows
unchanged and schema at 0008. Dedicated immutable one-shot acquisition is the first collector
option; unrestricted LLM roles/worktrees cannot prove credential/tool isolation or writer exclusion.

## Verification evidence

python .tools/run_clean.py .tools/make/ucrt64/bin/mingw32-make.exe verify: exit 0; Ruff, mypy
(146 files), 728 Python tests, Golden quality, architecture contract, web lint/types, 26 web tests
and standalone build PASS. Four PG cases skipped there were separately executed: 4 PASS/no skips.
Fixture PG18.6 migration/dump/restore: 0008, 16 People, 10 public People, 7 published Organization
Claims; clusters stopped and temporary password files removed. Final installed wheel outside
checkout: 37 routes, safe missing-key receipt, schema readiness and Alembic round trip PASS.
Full results: docs/receipts/architecture-current-master.md. Six SQLite datetime warnings retained.
Mac: venv install/pip check, 13 manifest hashes, 0008→0007→0008 and missing-key audit PASS.
Offline sandbox: six file/network checks and installed 37-route CLI/missing-key audit PASS.
Details, commands and limits: docs/receipts/mac-collector-readiness-20261001.md.
Bounded candidate after relay integration: full make verify passed 826 Python/26 web tests (4 optional PG cases skipped;
six SQLite warnings retained), mypy 146 files, quality/architecture/build. Independent read-only
review found no defect. Mac installed CLI proved 37 routes and SUCCESS/FAILED/PARTIAL/checkpoints
on four SSD mock fixtures. Forced-stop fixture proved RUNNING/RECOVERY_REQUIRED, no automatic retry.
Pinned relay 22d32c6 passed 58 offline tests and independent review. Seven Mac egress canaries
passed. Installed canonical CLI with real HTTPX/TLS passed trusted fixtures and rejected an
untrusted certificate; no official API or OS trust change. Approved request hash b127f5f1;
single-key encrypted delivery PID57756 completed with exit 0.
Updated inputs/receipts: docs/receipts/mac-collector-bounded-20261002.md.

## Not executed

Current-branch remote CI, live source, operational DB/admin writes, publication, scheduling,
browser/visual acceptance, Docker build (unavailable), push/PR/merge, deployment or access changes.
Actual official-source DNS/TLS/API and the approved first live run.

## Blockers

No SSD/storage, source-grant or key-delivery blocker. Native sandbox compilation rejected named-host
egress; the fixed Assembly loopback relay and TLS fixtures passed. The remaining live prerequisite
is independent launcher review and exact-target sandbox/watchdog validation. Allocated ownership is not a
database-enforced shared-writer lease. Shared recurring writers remain a separate change.

## Modified files

See the receipt for source paths. Current continuation: this HANDOFF, completed architecture
plan, final receipt, docs/operations/COLLECTION_AGENT.md and Mac readiness/bounded receipts.
Assembly connector/CLI budget changes and active Mac one-shot plan are integrated.
Original history is in docs/history. Mac preparation helpers/bundle are local ignored .tools files.

## Next concrete action

Verify the fixed one-shot parent launcher, install its immutable companion and prove its tighter
exact-target profile on Mac fixtures. Then execute the already-approved single acquisition and
audit canonical status, coverage and checkpoint; never retry a forced stop automatically.

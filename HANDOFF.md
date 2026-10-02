# HANDOFF

## Objective

Reapply the approved architecture refactor and prepare the selected dedicated one-shot collector
on the Mac/SSD. The local architecture work order is complete. The owner approved the exact
one-shot Assembly acquisition and Windows source-key reuse. That run and canonical audit are complete:
299 observations, provider total 299, three snapshots, checkpoint 3, SUCCESS.

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
Separate collector preparation, immutable Mac runtime and bounded acquisition are complete.
One live run completed; coverage, provenance, privacy and zero identity/publication rows were audited.
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
Target mac-ssd-assembly-one-shot-333aa26 is schema 0008, mode 0600. SourceRun
62f4567c-fb56-403c-952d-eb768136d6c3 is SUCCESS; 299 observations, three snapshots/Sources,
checkpoint 3, zero People/Claims/Organizations. Parent launcher pin 7b004bf and SHA-256
33d50df5b38387c9ec7e7908fe168bd15e5dc10a585fc0d3d49be34520701662; wheel stays 333aa26.

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
Final launcher: 27 tests, Ruff and mypy-darwin PASS; independent read-only review pinned source.
Full gate after launcher integration passed 853 Python tests, 4 PG skips, 6 warnings and 26 web
tests. Final repeat at 7b004bf passed CANONICAL_VERIFY_EXIT=0. Tight Mac profile passed seven
canaries and actual installed CLI; real watchdog stopped/reaped its own child at 180.011s and
kept RUNNING/RECOVERY_REQUIRED in an isolated fixture. Approved live execution PID75766 exit0
in 3.44s; canonical audit PID76155 exit0. Actual provider coverage/provenance/privacy PASS.
Sanitized receipts copied byte-for-byte: docs/receipts/assembly-one-shot-live-20261002.json,
assembly-one-shot-live-audit-20261002.json and one-shot-profile-7b004bf.json.

## Not executed

Current-branch remote CI, identity materialization/admin writes, publication, scheduling,
browser/visual acceptance, Docker build (unavailable), push/PR/merge, deployment or public access changes.

## Blockers

None for the completed one-shot scope. Allocated ownership/advisory launcher lock is not a
database-enforced shared-writer lease; shared recurring writers remain a separate change.

## Modified files

See the receipt for source paths. Current continuation: this HANDOFF, completed architecture
plan, final receipt, docs/operations/COLLECTION_AGENT.md and Mac readiness/bounded receipts.
Assembly connector/CLI budgets, fixed relay, trusted parent and completed Mac plan are integrated.
Original history is in docs/history. Mac preparation helpers/bundle are local ignored .tools files.

## Next concrete action

No active collection remains. Preserve the SSD DB/key and receipts. The nonempty target guard
prevents a duplicate first run. Further collection/resume, identity work, publication or recurring
execution needs a separately scoped work order.

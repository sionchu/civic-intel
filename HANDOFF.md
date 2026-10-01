# HANDOFF

## Objective

Reapply the approved architecture refactor and prepare the selected dedicated one-shot collector
on the Mac/SSD. The local architecture work order is complete; operational setup remains partial.

## Scope

Preserve Evidence Core, current Organization/source reachability, UNKNOWN, admin signing/locking/
receipts, source-context identity gates and schema compatibility. No operational execution grant.

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

## Current checkpoint

Branch codex/architecture-current-master, isolated architecture-current-master worktree.
Base/remote master 77e2767ab043738f00b8dd38be8d99803e5ad7bc; verified source
0ae694578125a9a070053205cf790880d9e07148. Later evidence-only commits preserve that source.
Original master and its modified packages/domain/contracts.py remain untouched.
Mac runtime: /Users/lee/Developer/civic-intel-collector-20261001, Python 3.12.14, pinned wheel.
External /Volumes/data is APFS on USB 10 Gb/s; Finder writes are owner-confirmed, remote mkdir
still times out. No SSD target or operational database exists from this setup.

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

## Not executed

Current-branch remote CI, live source, operational DB/admin writes, publication, scheduling,
browser/visual acceptance, Docker build (unavailable), push/PR/merge, deployment or access changes.
SSD fsync/readback probe, live egress, numeric rate/run budgets and operational credential delivery.

## Blockers

No local architecture blocker. Mac remote SSD writes hang despite Finder writes. TCC logs show
the Commander's node requested removable-volume approval; current permission/prompt state is
unconfirmed. Permission DB read was denied and System Events timed out. Owner response pending.
A live collector still needs exact source/target/scope grant, live restrictions, rate/run budget
and sole-writer target. Shared recurring writers require a separate lease/recovery change.

## Modified files

See the receipt for source paths. Current continuation: this HANDOFF, completed architecture
plan, final receipt, docs/operations/COLLECTION_AGENT.md and the Mac readiness receipt.
Original history is in docs/history. Mac preparation helpers/bundle are local ignored .tools files.

## Next concrete action

Obtain owner response to node's removable-volume approval prompt, then recheck SSD writes and
perform the pending fsync/readback probe before allocating the collector's sole-writer target.

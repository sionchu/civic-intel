# HANDOFF

## Objective

Reapply the approved architecture refactor to latest remote master and research separate-agent
collection. The local architecture work order is complete.

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
Separate one-shot collector proposal is documented; no collector was launched.

## Current checkpoint

Branch codex/architecture-current-master, isolated architecture-current-master worktree.
Base/remote master 77e2767ab043738f00b8dd38be8d99803e5ad7bc; verified source
0ae694578125a9a070053205cf790880d9e07148. Later evidence-only commits preserve that source.
Original master and its modified packages/domain/contracts.py remain untouched.

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

## Not executed

Current-branch remote CI, live source, operational DB/admin writes, publication, scheduling,
browser/visual acceptance, Docker build (unavailable), push/PR/merge, deployment or access changes.

## Blockers

No local architecture blocker. A live collector needs an exact source/target/scope grant and
proven runtime restrictions, rate/run budget and sole-writer target. Shared recurring writers
also need a database-enforced lease/recovery change, which is outside this completed work order.

## Modified files

See the receipt for source paths. Current continuation: this HANDOFF, completed architecture
plan, final receipt and docs/operations/COLLECTION_AGENT.md. Original history is in docs/history.

## Next concrete action

Select and approve one exact collector source, dedicated target and bounded execution scope
using docs/operations/COLLECTION_AGENT.md. This operator decision is separate from the completed refactor.

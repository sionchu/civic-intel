# Mac one-shot collector preparation

Authority: owner selected dedicated one-shot collection on the Mac's external SSD and authorized
continuation. Base: 3ec9a76b0110df66fddeea3acb736c514fc52028. On 2026-10-02 the owner approved
one unfiltered current Assembly roster, the allocated SSD target and exact bounded limits.
The owner also authorized transfer of only the Windows `.codex/.env` ASSEMBLY_API_KEY to the
private Mac slot; delivery passed. No publication, identity or scheduling scope.

## Scope

Prepare one current unfiltered Assembly roster acquisition using the canonical `civic observe
assembly` dispatcher, existing connector/enumerator/SourceLifecycle and schema 0008. Add optional
source-specific request-count, minimum-interval and cooperative elapsed-fetch limits in place;
no parallel CLI/runner truth store or generic orchestration. A hard watchdog must report recovery
required on forced termination rather than fabricate a terminal SourceRun.

## Milestones

1. SSD/runtime readiness: node access owner-approved; mkdir and 8 MiB fsync/hash/rename PASS;
   SSD fixture migration round trip and isolated installed missing-key CLI PASS.
2. Bound canonical Assembly acquisition: deterministic request-count/rate/deadline tests;
   preserved policy/provenance, committed checkpoint and FAILED/PARTIAL semantics; explicit CLI
   validation before dispatch; targeted checks, independent review and `make verify`.
3. Install verified updated package on Mac; prove budget stops and sanitized receipts on SSD
   fixtures, prepare sole-writer target and precise source/target/limits request. No live call
   before the corresponding grant and isolated credential delivery.
4. Validate the source-specific parent launcher, exact request/artifact/schema/writer/key checks,
   clean child environment, exact-target sandbox and 180-second watchdog. Execute one authorized
   live acquisition, inspect actual durable status/coverage/checkpoint and record evidence.

## Ownership

MAIN: CLI adapter/parser/tests, integration, package pin, Mac commands, docs and acceptance.
source_worker child: isolated worktree; only Assembly connector and its deterministic budget
tests; no shared domain/schema/CLI edits, operational DB, source API, secrets or child spawning.
quality_reviewer: read-only final diff and evidence; no production edits or operational access.

## Verification and stop conditions

Use fake clocks/HTTPX fixtures; prove bounded success, no over-budget HTTP call, first-page
failure and post-commit partial/checkpoint behavior, credentials absent from stored errors.
Verify actual installed CLI on Mac/SSD and explicit clean environments. API timeout remains
per-request; cooperative deadline is checked at request boundaries and cannot guarantee recovery
from a stuck DB/process. Never describe it as a universal hard deadline.

Stop the live stage for missing source/target grant, key, policy, schema, egress or writer
exclusion. Preserve owner data and current source records. Update HANDOFF and durable receipts.

## Checkpoint, 2026-10-02

Milestones 1 and 2 passed. Connector work was integrated from the source_worker commit
f295437 as 72b671c; MAIN added the three optional canonical CLI flags and pre-dispatch validation.
Independent read-only review found no concrete defect and confirmed the cooperative deadline
limit. Targeted combined checks passed. Full clean-environment `make verify`: Ruff, mypy
(146 files), 768 Python tests, Golden quality, architecture contract, web lint/types,
26 web tests and standalone build passed; four optional PostgreSQL cases skipped, six SQLite
datetime warnings retained. Initial full run had one Windows getpass failure because the
verification wrapper omitted USERNAME; the corrected wrapper passed that regression and the
full gate. Product code was unchanged for this environment correction.

Milestone 3 passed: immutable wheel 333aa26 installed; four SSD request-budget fixtures and
forced-stop recovery semantics passed; schema-0008 fresh sole-writer target remains empty.
Pinned fixed Assembly relay 22d32c6 passed 58 tests, independent review and seven Mac canaries.
Installed CLI with real HTTPX/TLS passed a trusted fixture and rejected an untrusted certificate.
Latest full gate after relay integration passed 826 Python/26 web tests, Ruff/mypy/quality/
architecture/build; four optional PG skips and six SQLite warnings retained. Official API was
not contacted. Approved request SHA is b127f5f10c596a78f9d370cde269a158b574e321c5502b33f29307420241b0ae.
Private single-key delivery completed with no value printed and no other environment values moved.

Milestone 4 in progress: source_worker owns only scripts/mac_assembly_one_shot.py and its tests
in isolated assembly-one-shot worktree at base 22d32c6. MAIN owns integration, request/docs,
Mac execution and sole operational writer. Reviewer remains read-only; no child receives keys
or operational tool access. Parent process receipt supplements, but never replaces, SourceRun.

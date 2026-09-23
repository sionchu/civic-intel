# Admin work playbook

Approved 2026-09-24: implement the attached Civic Intel Admin Playbook Proposal after PR143.
Baseline: 9a2c5a21e11f893172abcbfff6d71a2ad085b041. MAIN owns this worktree and shared files.
Do not modify the running admin or deferred PR75 until verified rollout. Independent review uses
provided code/config only; no operational credentials. Use Aside only for browser QA.

## Scope and gates

1. Add a contextual 업무 플레이북 to existing admin navigation, person selection, record details,
   collection lanes and committed history without replacing current workflows.
2. Generate a transient read-only work-order DRAFT from exact selected DB IDs/versions, server code
   revision and canonical role/policy references. Whole selection fails on drift/missing IDs.
   Client role/permissions/commands are not trusted. Copy/export is not dispatch or DB acceptance.
3. Preserve SourcePolicy: exports are a bounded reference manifest, not raw records, fulltext,
   normalized provider content or credentials. No task table/second raw store/migration.
4. Probe native named-role execution with isolated provided input and constrained tools. Only after
   actual loading/permission/timeout/state evidence passes may a single read-only adapter be enabled.
   If this prerequisite remains blocked, ship the useful first slice with explicit 실행 미연동 and
   record the exact blocker; do not install a new harness or weaken permissions.
5. Verify deterministic contracts/auth/selection/drift/privacy, full regression, real Aside browser
   navigation/selection/export/status/accessibility, and existing staging read-only acceptance.

## Runtime boundary

No source collection, Person registration/link/merge, Claim publication, org.go27 commit or schema
change is authorized by this task. Existing admin mutation path remains unchanged. No arbitrary
shell endpoint, user-selected filesystem path, cross-provider login or uncontrolled agent spawn.
Code tasks, source runs, review dispositions and committed DB operations remain distinct states.

## Verified checkpoint

Implemented six contextual recipes and exact selected-view request preparation. New data path is
read-only: no source content/credentials copied, no task table, dispatch or admin receipt created.
Independent restricted Codex text review found three issues: malformed Next input shapes, stale
lookup result kind/context and cached policy context. All were corrected; current tests cover
server policy revalidation and boundary tests exercise malformed requests with controlled400.
Aside browser9 checks passed for exact selection/export, input invalidation, six recipes, code-work
preparation, desktop overflow and keyboard; no page exceptions. Native viewport-resize API was not
exposed, so mobile QA is not claimed. Full-page capture failed; the viewport fallback was inspected.
Malformed Next requests return400, missing intent403 and untrusted Host404.
Local full suite565 passed/1 skipped; Ruff/mypy93 files and Golden passed. Web lint/typecheck,
26 UI tests, production build and standalone checks passed. These are local results, not CI.
Native named-role probe remains BLOCKED: selector/restrictions unverified, zero child launches.

## Preparation-slice closure — 2026-09-24

Status: COMPLETE for contextual request preparation only. Actual agent execution remains BLOCKED.
PR144 merged as `98dd4ca069c784c525996ad9ce707b86b483ccf9`; GitHub Verify35889018114
passed with565 tests/1 skipped, Web26 tests, Golden, migrations/PostgreSQL/artifact gates.
The existing private admin on3315/8315 was restarted from the merged worktree with its prior
ADMIN WRITE capability preserved. No cloud service deployment or schema change was required.
Desktop Start now uses `C:\Users\getch\civic-intel-playbook`; Open remains the same3315 URL.

Actual staging Aside verification recorded9 checks: exact two selected IDs/64-character view
versions, merged code/assigned role, no dispatch/human attestation, reference-only content,
matching Markdown, six recipes, selection invalidation, desktop no overflow and existing admin
write capability. Note edits independently invalidated the previous export. The saved viewport
screenshot was inspected. A few one-shot harness calls failed on unsupported Aside methods or
navigation timing; interactive Aside snapshots and real downloads established the final evidence.
Mobile viewport behavior remains unverified; no unauthorized browser fallback was used.

Fresh before/after read-only PostgreSQL audits at2026-09-23T16:56:05Z and17:16:19Z matched:
People299, Organizations347, Claims/Evidence5576/5576, observations4170, snapshots370;
all inspected domain fingerprints and table counts unchanged. Schema0007 and admin receipts0.
Anonymous private playbook API403; untrusted-Host private Web404. Source acquisition, real-person
registration/link/merge, Claim publication and the independent org.go27 commit were not executed.

## Next dependency

See [the blocked native execution prerequisite](../blocked/admin-agent-execution.md).
Do not call the full agent lifecycle complete because a DRAFT can be exported. Enabling a runner
requires actual named-role/tool isolation and event/timeout evidence, not another task label.

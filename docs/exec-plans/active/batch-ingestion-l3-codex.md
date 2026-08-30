# Codex entrypoint — Batch Ingestion L3

This repository is the single source of truth for the approved Civic Intel long-running task.

Codex must not rely on an external handoff prompt. Start from the current repository HEAD and
read, in order:

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. `docs/INDEX.md`
4. `docs/product/V0_SCOPE.md`
5. `docs/architecture/BATCH_INGESTION.md`
6. `docs/architecture/BATCH_INGESTION_DB.md`
7. `docs/architecture/IDENTITY_RESOLUTION.md`
8. `docs/architecture/FEEDER_SOURCE_COVERAGE.md`
9. `docs/roles/BATCH_INGESTION_AGENT.md`
10. `.agents/skills/batch-ingestion-foundation/SKILL.md`
11. `docs/exec-plans/active/batch-ingestion-l3.md`
12. `docs/workflows/CHANGE_CONTROL.md`
13. `docs/workflows/DEFINITION_OF_DONE.md`

Then inspect the actual code/tests/migrations referenced by the active ExecPlan, verify the
current HEAD/baseline, and execute the plan through its stop condition.

Do not stop after producing a plan. Do not ask for routine implementation confirmation between
milestones. Update the active ExecPlan with actual verification/commit evidence as work
progresses.

Stop only for the escalation conditions in `AGENTS.md` or when the active ExecPlan stop
condition is fully satisfied.

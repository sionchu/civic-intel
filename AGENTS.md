# Repository execution entrypoint

Start with `ARCHITECTURE.md`, `docs/INDEX.md` and the current `HANDOFF.md`. Before changing
behavior, read the active work order, `docs/product/V0_SCOPE.md`, your role document,
`docs/workflows/CHANGE_CONTROL.md` and `docs/workflows/DEFINITION_OF_DONE.md`.
The full normative rules are in [Repository rules](docs/workflows/REPOSITORY_RULES.md);
read the relevant sections before changing source, identity, persistence or publication behavior.
Historical receipts establish past execution only, not current readiness or operational state.

## Load context for the touched path

| Work | Required context |
|---|---|
| Batch/full enumeration | `docs/architecture/BATCH_INGESTION.md`, `FEEDER_SOURCE_COVERAGE.md`, `IDENTITY_RESOLUTION.md`, exact feeder contract, `.agents/skills/batch-ingestion-foundation/SKILL.md` and its referenced invariants |
| Persistence/schema | `docs/architecture/BATCH_INGESTION_DB.md`, application ports and current migrations |
| Identity/publication | Identity/source contract and `ORGANIZATION_CLAIM_PUBLICATION.md` when applicable |
| Admin | `docs/architecture/ADMIN_OPERATIONS.md`, existing preview/receipt/lock contracts |
| Web UI | Root `DESIGN.md` before edits; existing semantic tokens/components are the contract |
| Delegation | `docs/roles/ROLE_MODEL.md` and `docs/roles/MODEL_ROUTING.md` |

Architecture filenames without a directory in this table are under `docs/architecture/`.
Use only the relevant specialist skills and source documents; do not load the whole catalog.

## Invariants at every boundary

- Preserve `rendered item → Claim → ClaimEvidence → Source → SourcePolicy`. Publication and
  truth assertion are separate; published UNKNOWN stays unresolved and unasserted.
- Processing starts with SourcePolicy. Technical access is not permission. No generic crawling;
  only approved source-bounded official enumeration with permitted fields/provenance.
- `SourceSnapshot` is the only source capture. No duplicate raw truth store, credentials,
  private contacts, unnecessary addresses or provider secrets in persisted/public output.
- Identity-specific output requires resolved identity. Names, proximity, fuzzy/embedding scores
  never authorize Person merges. Automatic create/link requires its exact reviewed provider rule;
  ambiguous/cross-lane cases fail closed to review. No private-family discovery/residence contracts.
- Workers normalize and request verified materialization; they cannot bypass publication gates.
  Checkpoints advance only with committed Source/Snapshot/Observation data.
- Domain contracts own semantics; session-bound persistence adapters share one Database/UoW.
  Alembic alone changes schema. Startup checks readiness and never creates, migrates or seeds.
- Preserve Golden/reviewed regressions, current temporal contracts, human review and source rights.
  Extend canonical contracts in place; no parallel `v2/new/final` implementation or premature framework.

## Execution and completion

Preserve user changes and unrelated files. MAIN owns shared contracts, integration and HANDOFF.
Use at most three children, no recursive delegation, isolated editing worktrees and bounded tasks.
Worktrees/role labels do not isolate credentials, tools, DB writers, ports or browser sessions.
Serialize operational mutations until shared exclusion is proven. Recommendations are not human
attestations, source grants, publication approval or executed receipts. Inspect actual command effects.

For an approved multi-milestone plan: verify HEAD/baseline, implement one coherent milestone,
run targeted checks and `make verify`, inspect the final diff, commit, update evidence and continue.
Run Alembic upgrade/downgrade/upgrade for schema work. Remove dead/duplicate paths and doc drift.
Keep HANDOFF/current plans bounded and link preserved history/receipts. Release exclusions remain
specific to that release; later capabilities require their own approved scope and unchanged gates.

Stop only at meaningful cost, destructive loss, ownership transfer, weaker security/public access,
secret exposure or unresolved source rights. Routine implementation and verification proceed.

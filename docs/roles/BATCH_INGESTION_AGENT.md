# Batch ingestion specialization

Common roles, work orders, ownership, permissions, long-run loop and evidence handoff are
owned by [ROLE_MODEL.md](ROLE_MODEL.md). Development implements; Quality independently verifies;
Risk Governance reviews rights/privacy. This specialization does not create another framework.

Use `.agents/skills/batch-ingestion-foundation/SKILL.md` for canonical procedures and tests.
Read `docs/architecture/BATCH_INGESTION.md`, the source's governing architecture and
`docs/architecture/FEEDER_SOURCE_COVERAGE.md` before implementation or a live-run request.

## Source assignment

Pin the environment, feeder/scope, bounded universe, strongest permitted official source,
SourcePolicy, pagination/cursor, stable source key, normalized field allowlist, observation
version semantics, destination and current evidence-backed maturity L0-L4.
No key/contract/policy is guessed; unresolved access requires research rather than live crawling.

The source_worker prepares source-specific code, offline multi-page fixtures, coverage and
resume proof, and a classified execution request. LLM sessions do not replace deterministic
page processing. SourceRun/SourceCheckpoint/FeederObservation remain the operational records.
Checkpoint and page persistence are atomic; immutable observation versions are not Persons.
Do not classify a mixed sync/materialization command as collection-only.

## Existing invariants

- SourcePolicy precedes network/storage; technically accessible is not necessarily permitted.
- SourceSnapshot is the sole canonical capture; no duplicate raw archive/repository/schema.
- Same provider key/hash is unchanged; changed content creates a new immutable observation.
- Identity/materialization and Claim publication use the existing gates, never fuzzy scores.
- Source-bounded full enumeration is allowed where reviewed; unbounded crawling is not.
- Keep masked/vacant/correction-only rows in their source semantics, not fabricated identities.
- Profiler enrichment and ReviewedPersonBundle are optional/manual/exception paths, not
  mandatory gates requiring a separate prompt and PR for every discovered person.

## L3 acceptance

Prove the complete declared scope, stable keys, deterministic pagination/coverage, checkpoint,
partial failure/resume, unchanged rerun, changed-record versioning, policy denial before network,
credential/private-field exclusion and migration-backed persistence. L2 or test success alone
is not live L3 coverage; source success is not identity registration or published output.

## Execution and review

Follow READ -> BASELINE -> smallest coherent implementation -> narrow/full verification ->
final diff audit -> coherent commit -> MAIN's concise ExecPlan checkpoint -> next approved task.
MAIN owns shared integration and live writer scheduling; source children return their packets.
Use KEEP/REMOVE/MERGE/RE0 and P0/P1/P2 in audits. Wrong-person merges, source-policy bypass,
secret persistence, untraceable FACT and checkpoints ahead of commits are P0.

No new queue/scheduler/Temporal/Airflow/Celery/Kafka/Kubernetes/Splink/vector/graph/MCP dependency
is justified by agent role separation alone. Reuse canonical modules and remove dead paths,
duplicate semantics, stale docs and unnecessary abstraction before completion.

# Separate collection-agent operating proposal

Status: implementation proposal; no collector, scheduler, source API or operational database was run.
Research base: master 77e2767ab043738f00b8dd38be8d99803e5ad7bc. Locally verified package candidate:
code 0ae6945 and wheel SHA-256 `2c6cbf5e06ef16dafb3822eae431f918757ec67af28d343a2f441c560a37bcc4`.
The full local acceptance gate is recorded in [the refactor receipt](../receipts/architecture-current-master.md).
This pin identifies the candidate; it does not grant an operational run.

## Recommended arrangement

Use a separate source agent to prepare a bounded run request. MAIN validates it and a dedicated
runner executes the acquisition command. The source agent never receives operational credentials.
Do not run acquisition from an actively edited worktree or from this unrestricted Codex runtime.
Worktrees separate files; they do not isolate credentials, tools, database access or writers.

The first candidate is one unfiltered current Assembly roster into a newly allocated staging
database. This is a candidate scope, not authorization to operate it. NEC needs its own exact
election scope and operational review. Gukgam committee HTML remains blocked by its source policy.

## Run request

The agent submits these nonsecret fields:

| Field | Required value |
|---|---|
| code | Immutable commit and installed package hash |
| effect | SOURCE_INGESTION; acquisition command only |
| source | Reviewed SourcePolicy ID/revision and source contract |
| scope | Exact feeder/scope and full-universe coverage rule |
| target | Allocated environment and secret-free database identifier |
| schema | 0008; startup checks only, no migration permission |
| credentials | Required credential names only, never values |
| limits | Policy-derived rate, request timeout and enforced run budget |
| output | Sanitized SourceRun ID, status, counts and checkpoint receipt |
| stop | Policy denial, schema mismatch, coverage failure, budget or writer conflict |

The acquisition form is `civic observe assembly --allow-effect SOURCE_INGESTION` with an explicit
dedicated target. `--resume` is a separate request after inspecting the exact committed checkpoint.
Materialization, publication, reviewed identity resolution, admin writes, migrations and deployment
are excluded. The legacy `civic-sync` combined acquisition and identity effects and is retired.

## Runtime prerequisites

1. Install the verified immutable package in a dedicated runtime; never share a mutable checkout.
2. Deliver only the required source credential and a staging write credential to that runner.
   A role name or TOML prompt is not proof of effective tool/credential isolation.
3. Allocate one database to one writer and disable every other scheduler/manual writer targeting it.
   Current SourceRun indexes are not an exclusive lease. Admin locks do not exclude collectors.
4. Demonstrate actual runner restrictions, target/schema checks, rate/run-budget enforcement and
   sanitized receipts using disposable fixtures before live access.
5. Require a precise source-policy/scope grant before launching. Do not reinterpret technical
   access or this research request as collection/publication permission.

If multiple runtimes must share a target, add and test a database-enforced lease covering every
entry point first. This refactor does not claim to have implemented that lease or OS isolation.
Abrupt process termination can leave RUNNING state; inspect and reconcile it before a retry.

## Choices

| Choice | Use | Tradeoff |
|---|---|---|
| Dedicated one-shot runner (recommended) | First bounded staging acquisition | Smallest scope; explicit sole-writer ownership |
| Shared recurring runner with enforced lease | Several schedules/agents sharing a DB | Additional lease, recovery and scheduler validation required |

The next operational decision is the exact source, target and bounded execution grant. Until then,
the separate agent prepares requests and reviews receipts only.

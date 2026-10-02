# Separate collection-agent operating proposal

Status: owner approved the exact one-shot Assembly scope on 2026-10-02; source key delivery,
dedicated runtime, SSD writes, bounded CLI and loopback/TLS fixtures passed. An empty dedicated
SSD staging target is provisioned. Operational launcher validation remains; no live source ran. See the
[Mac readiness receipt](../receipts/mac-collector-readiness-20261001.md).
Research base: master 77e2767ab043738f00b8dd38be8d99803e5ad7bc. Installed bounded candidate:
code 333aa26 and wheel SHA-256 `f94bd36a38c886da82b226301a6191000b8f4ad94c6747bd8f76a94c9f3d9cca`.
The full local acceptance gate is recorded in [the refactor receipt](../receipts/architecture-current-master.md).
This pin identifies the candidate; it does not grant an operational run.

## Recommended arrangement

Use a separate source agent to prepare a bounded run request. MAIN validates it and a dedicated
runner executes the acquisition command. The source agent never receives operational credentials.
Do not run acquisition from an actively edited worktree or from this unrestricted Codex runtime.
Worktrees separate files; they do not isolate credentials, tools, database access or writers.

The owner approved one unfiltered current Assembly roster into the allocated fresh staging
database, with the limits in `mac-assembly-one-shot-request.json`. NEC needs its own exact
election scope and operational review. Gukgam committee HTML remains blocked by its source policy.

## Run request

The agent submits these nonsecret fields:

| Field | Required value |
|---|---|
| code | Immutable commit and installed package hash |
| effect | SOURCE_INGESTION; acquisition command only |
| source | Reviewed SourcePolicy ID, terms_checked_at and code pin; source contract |
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

The approved first request is acquisition only. The separate agent prepares source-specific
implementation and fixtures; MAIN owns the single operational execution and audits its receipt.

## Mac preparation checkpoint, 2026-10-02

The verified package and 22 pinned dependencies are installed in a dedicated Python 3.12.14 venv
under `/Users/lee/Developer/civic-intel-collector-20261001/bounded-333aa26`. Installation used a clean environment,
isolated pip and the explicit PyPI index. The code release is the pinned wheel, not a working tree.
Alembic resources are byte-identical to the pinned source; provisioning is a separate operation.

Disposable SQLite verification passed schema 0008 → 0007 → 0008, all 37 CLI routes and the
canonical missing-key receipt audit. A deny-all-network sandbox also passed six bounded
file/network checks and the actual installed CLI missing-key audit. Updated installed-CLI SSD
fixtures prove request caps, start-to-start spacing and cooperative fetch deadlines with
SUCCESS/FAILED/PARTIAL and exact committed checkpoints. A separate forced-stop fixture proved
RUNNING remains durable and requires recovery rather than automatic retry or a fabricated FAILED.
The offline profile permits no live API access and does not prove credential delivery or live TLS.

External APFS volume `/Volumes/data` is mounted and advertised writable; USB is now 10 Gb/s.
The owner approved node's removable-volume access. Remote mkdir, 8 MiB fsync/readback/SHA/rename,
SSD schema 0008→0007→0008 and installed offline CLI checks then passed. The owned SSD root
`/Volumes/data/civic-intel` is mode 0700. Fresh target `mac-ssd-assembly-one-shot-333aa26`
is a mode-0600 SQLite file at schema 0008, with zero runs, observations, People and Claims.
MAIN owns the sole one-shot writer; no scheduler targets it. This is allocated ownership, not a
shared-writer database lease. Existing SSD data and disk settings were preserved.

Native Seatbelt rejected a named-host allow rule. The pinned fixed Assembly CONNECT relay
(`22d32c6`, SHA-256 `41105315eb56979e66d4aaf6cdc2a122427084e582f0e204258b964ecf9b64ab`)
passed 58 offline tests, independent review and seven Mac file/network canaries. A real HTTPX/TLS
fixture through the installed canonical CLI passed; an untrusted certificate failed closed.
Those fixtures contacted no official API and changed no OS trust. The live child must omit the
fixture SSL_CERT_FILE and permit only its allocated loopback port and exact SQLite files.

The owner approved page size 100, maximum 8 requests, minimum start interval 1 second, fetch
budget 120 seconds and hard child stop 180 seconds. These are operating limits, not provider
permission. Windows `.codex/.env` supplied only ASSEMBLY_API_KEY via an encrypted envelope to
the private mode-0600 Mac slot; no other values were transferred or printed. Operational
launcher preflight/watchdog validation remains before the live run. The relay is bounded but
not client-authenticated; unrelated local clients could consume its capacity. DNS cannot be
cancelled within the relay. These checks are not comprehensive adversarial isolation.

# Mac SSD bounded collector, 2026-10-02

Status: SSD/runtime/budget/egress/TLS fixtures PASS; owner-approved live acquisition pending
operational launcher validation. Private source-key delivery PASS. The owner approved node
removable-volume access. All Mac commands used Remote Desktop Commander, with explicit device
1a9f82ea-a0b2-44ee-9997-4f75f2916ebe and /bin/zsh. No live source, identity materialization,
Claim publication, scheduler, deployment, push or merge ran.

## Installed inputs

- Wheel code: `333aa26bda5f1110e53190f27de0c62a0f43cb30`.
- Wheel SHA-256: `f94bd36a38c886da82b226301a6191000b8f4ad94c6747bd8f76a94c9f3d9cca`.
- Transfer: 353804 bytes; SHA-256 `64d4def849824a4b0d079a08114229fe5505fe47a60e33c8ae1ae05a2fd0a1b8`.
- Runtime: `/Users/lee/Developer/civic-intel-collector-20261001/bounded-333aa26`, 0700;
  Python 3.12.14, 22 exact runtime dependency pins, 13 verified payload hashes.
- Build used a clean Git export. All 147 packaged Python files matched the source pin
  after line-ending normalization. The first checkout build included an untracked node_modules
  Python file and failed this gate; it was not transferred or installed.
- Initial runtime/release is retained; this candidate has a separate venv and release directory.

## Executed verification

| Check | Result |
|---|---|
| clean-environment `make verify` after relay integration | Ruff, mypy 146 files, 826 Python tests, Golden quality, architecture, web lint/types, 26 web tests and build PASS; exit 0 |
| optional PostgreSQL cases in this run | Four skipped; no fresh PostgreSQL claim; six existing SQLite datetime warnings |
| source_worker narrow suite | 52 passed; final budget-only rerun 33 passed |
| independent read-only budget/CLI review | No concrete defects; cooperative deadline limitation confirmed |
| clean Git-export wheel integrity | 147 Python files matched; migration resources and dependency contract matched |
| Mac `setup-bounded.py`, PID 47268 | Exit 0; complete transfer SHA, 13 payload hashes, venv install and pip check PASS |
| Mac sandboxed `verify-budget.py`, PID 47674 | Exit 0; installed imports/37 routes/four SSD fixture cases PASS |
| Mac forced-stop fixture, PID 48589 | Exit 0; own child terminated/reaped; persisted RUNNING, zero observations, no checkpoint; RECOVERY_REQUIRED |
| Mac staging provision, PID 47930 | Exit 0; schema 0008, mode 0600; runs/observations/People/Claims all zero |
| Mac named-host sandbox compilation, PID 49013 | Compiler exit 65; HOST_FILTER_UNSUPPORTED; no source request |
| relay narrow suite and independent read-only review | 58 offline tests PASS; no concrete review defect; relay Ruff/format/mypy PASS |
| Mac egress canaries, PID 51880 | Exit 0; seven loopback/direct-egress/file-write canaries PASS; one injected fixture dial |
| Mac actual HTTPX/TLS installed CLI, PID 52573 | Exit 0; trusted fixture SUCCESS, 3 observations, checkpoint 2; default-trust negative FAILED, 0 observations, no checkpoint |
| private key delivery, PID 57756 | Exit 0; only ASSEMBLY_API_KEY transferred as encrypted envelope; mode 0600; temporary transport private key removed; secret not printed |

Initial full verification had one failure caused by the fixture wrapper omitting Windows USERNAME.
After retaining this nonsecret OS identity, the focused regression and complete gate passed.
Product code did not change for that correction. The local installed-wheel probe initially failed
at receipt/path guards; corrected fixture-only paths and fresh targets then completed with exit 0.

The Mac became unresponsive during transfer. After the owner woke it, process execution resumed
but native file writes still stalled. Transfer used the same Remote Desktop Commander command
execution path, separate owned filenames, checked offsets, fsync and complete final SHA.
Unconfirmed files were preserved; no alternate transport or disk/security setting change was used.

## Installed CLI budget proof

All data were synthetic, credential-free fixtures using HTTPX MockTransport under deny-all
networking. A direct TCP canary proved kernel permission denial. Timing used a fake clock.

| Fixture | HTTP attempts | Durable state | Observations | Committed checkpoint |
|---|---|---|---|---|
| success with spacing | 1, 2 at simulated 0s, 2s | SUCCESS | 3 | 2 |
| request cap 1 | 1 | PARTIAL | 2 | 1 |
| first response at deadline | 1 | FAILED | 0 | none |
| later response past deadline | 1, 2 | PARTIAL | 2 | 1 |

Failure CLI receipts contain COMMAND_FAILED only. Durable budget error code is
AssemblyRequestBudgetExceeded with constant summary; private fixture contacts/credential markers
were absent. No People or Claims were created. Late/unrequested pages did not advance checkpoint.
Request spacing/deadline checks cover connector fetch boundaries; they do not bound DB commit.
The forced-stop fixture deliberately retained its RUNNING SourceRun and did not rewrite status
or retry. It is isolated from the empty operational target.

Offline SSD profile SHA-256:
`1da5ddd28ebe170f16ad061483640b8ffb75acb83edff1e4a06c6841de6dba4d`.
It extends the verified earlier profile only with the new runtime receipt write directory.
These are bounded executed canaries, not comprehensive adversarial isolation or live TLS proof.

## Allocated target and live request

Target alias: `mac-ssd-assembly-one-shot-333aa26`; SQLite file
`/Volumes/data/civic-intel/staging/assembly-one-shot-333aa26.sqlite`, mode 0600, schema 0008.
MAIN owns this fresh one-shot target; no scheduler or other assigned writer targets it. There
is no shared-writer database lease. Provisioning used Alembic separately; acquisition checks head.

Owner-approved scope on 2026-10-02 is one unfiltered current Assembly member roster: feeder national_assembly_members,
scope current_member_roster, contract assembly_member_roster, provider ID MONA_CD,
SourcePolicy 11000000-0000-0000-0000-000000000001, terms_checked_at 2026-08-30T00:00:00Z.
Credential name ASSEMBLY_API_KEY only. Approved limits: page size 100, at most 8 HTTP attempts,
at least 1 second between starts, cooperative fetch budget 120 seconds and hard process stop
180 seconds with recovery inspection before retry. These numbers are an operating budget,
not provider permission. No resume/materialization/publication/scheduler scope is included.

Native Seatbelt rejected a named-host allow rule. Microsoft's
[Seatbelt backend documentation](https://github.com/microsoft/mxc/blob/main/docs/seatbelt/seatbelt-backend.md)
also describes the wildcard/localhost limitation and loopback proxy confinement. A fixed Assembly
relay companion is installed at source pin 22d32c68c804936065f7756fc917c4b1c37c7679,
11902 bytes, SHA-256 `41105315eb56979e66d4aaf6cdc2a122427084e582f0e204258b964ecf9b64ab`.
The seven Mac canaries passed with profile SHA-256
`5b24f6c15a82cf43fbac09bcb3a218dc64563ac088e6a3b8bb81a7efbc0b522f`.
They used a TCP echo fixture, not the official API. The separate TLS fixture used the actual
installed CLI and HTTPX, without MockTransport. Profile SHA-256:
`19f955bcecb88c3b53fce8fd6d4450715c952f64a1a638239077e88e3d596b62`.
The fixture CA was process-local; no OS trust changed. Omitting it made the negative fixture
fail before an HTTP request reached the fixture server. No actual source DNS/TLS/API was tested.
Live environments must not inherit this fixture CA or other source/admin/deployment credentials.

The relay permits only exact Assembly CONNECT, rejects nonpublic/mixed DNS answers, and caps
accepted connections, bytes and duration. It does not authenticate local clients and cannot
cancel blocking DNS internally. Canaries prove their executed boundaries, not comprehensive
adversarial/process isolation. The dedicated parent watchdog must bound and reap its child.

Request SHA-256: `b127f5f10c596a78f9d370cde269a158b574e321c5502b33f29307420241b0ae`.
The owner authorized reuse of the Windows `.codex/.env` key. Only the named source key was
read internally and RSA-OAEP encrypted to a temporary Mac transport key; only ciphertext crossed
tool arguments. Mac decryption wrote the existing empty private slot and removed the temporary
transport key. The key value, hash and other `.env` values were never printed. The exact request
grant is now recorded; no further scope confirmation is required. Operational launcher validation
and one bounded live run remain.

Remote receipts are in the bounded runtime's receipts directory and `/Volumes/data/civic-intel/receipts`:
setup.json, assembly-budget-333aa26.json, forced-stop-333aa26.json, staging-provision.json,
egress-333aa26.json and tls-333aa26.json.
The earlier SSD storage/schema/isolation receipts remain intact. No credential value was
requested in chat or included in an execution report or versioned artifact.

# ALIO Local Acquisition Recovery v1

Status: BLOCKED — Phase 1 fresh-backup precondition was not reached on 2026-09-18.

## Decision and boundary

Recover the ALIO item-4 acquisition from the Korean local Windows runner without changing the
Civic Intel connector, schema, Railway region, IPv6 setting, plan or serving API. The permitted
path is:

```text
local Windows runner
→ ALIO bounded HTTPS acquisition
→ Railway private SSH database tunnel
→ existing SourceRun / SourceCheckpoint / FeederObservation
→ existing Organization Claim importer
```

This recovery must not use `--resume` for the failed staging run, expose PostgreSQL publicly,
add a Railway service/domain/worker/cron, register a temporary key, add ALIO data manually,
bypass SourcePolicy or provenance, or create/link/merge Persons from ALIO executive names.

## Phase 0 — local baseline

Passed without repository or staging mutation.

- The isolated worktree was clean at
  `HEAD == origin/master == 354872e964c34d225cd598e42de44228e9a806dd`.
- Aside REPL opened the official item-4 page and observed title `ALIO : 공공기관 경영정보
  공개시스템`, heading `임원현황`, an unfiltered institution directory with `Total 355`, and
  current disclosure links. This is browser reachability evidence only; it does not change the
  source contract or authorize publication.
- The required local `httpx` request to
  `https://alio.go.kr/item/itemOrganList.do?reportFormRootNo=20305` returned HTTP `200`.

## Phase 1 — private tunnel precondition

Blocked before backup, restore, tunnel database reads or any staging acquisition write.

- The existing local key
  `C:\Users\getch\.ssh\civic-intel-staging-006b07144fbc479caa930d5546c6e458` was tried with
  the existing Postgres SSH service instance and was rejected as
  `Permission denied (publickey,keyboard-interactive)`.
- Railway's supported
  `railway connect postgres --project ... --environment ... --tunnel-only --port 55432`
  process exited `1`, opened no listener, emitted no usable local connection detail, and was
  stopped/cleaned up. The exact temporary probe logs were deleted.
- The Railway account's read-only key listing contains only the pre-existing `dev.new` key.
  Its corresponding private key is not available to this local runner. No key was generated,
  registered, modified or removed during this recovery attempt.

Because the private tunnel could not be established, the fresh logical backup/restore gate was
not claimed, no tunnel pre-write counts were asserted, and Phases 2–8 were not run. The prior
staging state remains the last recorded state: schema `0006`, People `299`, Organizations `1`,
Claims `1496`, ALIO item-4 observations `0`, checkpoints `0`, one failed ALIO SourceRun, and
C0908 Item-12 `5` observations/`2` Claims.

## Reopen condition

Make the private key corresponding to the already-registered `dev.new` Railway key available to
the approved local runner without registering a new key. Then repeat the fresh backup/restore
proof before opening the tunnel, run a new normal bounded enumeration without `--resume`, and
continue to the existing importer gates only after a successful complete checkpoint.

## Safety result

- No staging database write, reset, reload or schema change occurred in this recovery attempt.
- No Railway resource, domain, plan, region, IPv6 setting or serving API credential changed.
- No task-owned tunnel log, connection URL, secret, dump or temporary key was retained.

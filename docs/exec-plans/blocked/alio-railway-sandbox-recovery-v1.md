# ALIO Railway Sandbox Recovery v1

Status: BLOCKED — item-4 Organization Claim dry-run timed out without a receipt on
2026-09-18. No Organization Claim commit or public ALIO acceptance was performed.

## Decision and boundary

Use exactly one private-network Railway Sandbox as a temporary acquisition boundary for the
already-implemented ALIO item-4 lane. Keep the serving API, Web service, PostgreSQL resource,
schema, domain, plan and production unchanged. The Sandbox is not a permanent collector, worker,
cron or public service. The ALIO path remains:

```text
official ALIO item-4 directory
→ SourcePolicy / Source / SourceSnapshot / FeederObservation
→ bounded Organization Claim importer
```

ALIO executive names do not create or merge canonical Persons. No raw HTML, attachments,
contacts, provider payloads, credentials or full database URLs are retained in receipts or
documentation. `--resume` is not used for the failed or incomplete acquisition run.

## Phase 0 — source and topology preflight

Completed read-only.

- Repository source revision: `112763b87ecc5ac5fbf66b395360d78cd9a87c0f`; the isolated
  worktree was clean before the operation.
- Aside opened the official ALIO item-4 page and observed `임원현황`, an unfiltered directory
  total of `355`, and current disclosure links. This is source reachability evidence, not a
  publication grant.
- The exact bounded connector reached `alio.go.kr`, used source contract
  `alio_item_4_institution_directory`, and parsed `355` directory rows.
- Existing staging deployment IDs remained API `76ec8f69-8874-4fbb-a67c-eeda55d0fd19`, Web
  `8fad7294-d590-4aee-9381-71c5f3bfca6f`, and PostgreSQL
  `172ec443-e3cc-44bb-a5c1-195f54f86824`. No serving deployment was issued by this plan.

## Phase 1 — disposable private Sandbox

Completed and cleaned up.

- Exactly one Sandbox was created with the approved private-network and five-minute idle timeout
  settings: `a300391a-81a0-4b96-8495-be017988a396`, region `us-west2`.
- It cloned the public repository at the exact source revision above and installed the existing
  package in `/work/venv`. No new repository service, domain, SSH key or scheduler was created.
- The Sandbox was destroyed by exact ID after the blocked gate. A final `sandbox list` returned
  an empty list; no Sandbox remains running.

## Phase 2 — logical backup and disposable restore

Passed before the acquisition write.

- Railway-managed PITR was unavailable on the current plan and was not upgraded.
- A private `pg_dump --format=custom --no-owner` was created outside the repository. Size was
  `351017` bytes and SHA-256 was
  `33da5af9bd84ac8d0309432ca48baeb8a4f9aad0ba8a302c15245a7e2118f47f`.
- It restored successfully to a separate loopback-only disposable PostgreSQL target on port
  `55440`; dump duration was `18s` and restore duration was `1s`.
- Restore checks passed: schema `0006`, People `299`, Organizations `1`, Claims `1496`,
  ClaimEvidence `1496`, subject-XOR violations `0`, and C0908 item-12 `5` observations / `2`
  Claims. The dump and restore cluster were removed inside the Sandbox.

## Phase 3 — bounded item-4 enumeration

Passed for observation staging; publication did not open automatically.

- The normal command was run with the Sandbox `DATABASE_URL` and no `--resume`:

  ```text
  /work/venv/bin/python -m workers.public_institutions --database-url "$DATABASE_URL"
  ```

- An initial client timeout left run `560c8e62-6d3c-427e-b96d-c5353e1e7927` incomplete with
  `1346` records/observations and `RUNNING` status. It was not resumed.
- A fresh normal execution completed successfully:
  - run `e57f88d4-953b-4de5-bf1c-13fa4b3e43db`
  - status `SUCCESS`
  - institution checkpoint `355/355`
  - `institutions_committed=355`
  - `unique_records=3798`
  - `records_seen=3799`
  - `observations_created=2453`
  - `observations_unchanged=1346`
- The resulting read-only database state had `3799` item-4 observations, one complete
  checkpoint and one successful item-4 SourceRun. The stale incomplete run remains an
  operational history row and is not an importer input.

## Phase 4 — Organization Claim dry-run gate

Blocked and fail-closed.

- The no-commit importer was invoked with the existing bounded command:

  ```text
  /work/venv/bin/python -m workers.alio_current_executive_claim_import --database-url "$DATABASE_URL"
  ```

- The command performed no `--commit`. Foreground/detached receipt-capture attempts did not
  produce a JSON receipt. The final file-captured process remained in a PostgreSQL socket poll
  for about `2408s`; it had no exit file while running, its receipt file remained `0` bytes and
  its error file remained `0` bytes. It was then terminated by exact PID inside the disposable
  Sandbox, producing exit `143`.
- Because the required `DRY_RUN` receipt was never produced, no Organization Claim importer
  commit, idempotency rerun or public ALIO route acceptance is claimed.
- Post-timeout read-only checks remained: schema `0006`, resolved People `299`, Organizations
  `1`, Claims `1496`, ClaimEvidence `1496`, and C0908 item-12 `5` observations / `2` Claims.
  The item-4 observations/checkpoint are the only accepted staging delta.

## Safety and reopen condition

- No Person was created, linked or merged from an ALIO name.
- No API/Web deployment, PostgreSQL resource, volume, domain, plan, schema migration or public
  database exposure was performed by this recovery.
- The temporary Sandbox was destroyed and no running Sandbox remains. No secret, full
  `DATABASE_URL`, raw provider payload, HTML or attachment was retained.

Reopen only with a bounded fix or operator-approved execution path for the importer preflight
that produces a redacted `DRY_RUN` receipt within an explicit operational budget. Do not run
`--commit`, public ALIO acceptance or a scheduler until that receipt is available and reviewed.

## Verification record

- Railway read-only status after cleanup showed the existing three-service topology and the same
  API/Web/PostgreSQL deployment IDs listed in Phase 0; `sandbox list` returned `[]`.
- Root checkout, unrelated user changes and other worktrees were preserved. This isolated
  worktree contains documentation only for this recovery result.

## Next concrete action

Profile and fix the existing ALIO Organization Claim dry-run's sequential database access in a
local/disposable test first, then repeat only the no-commit receipt gate before any staging
Organization Claim publication.

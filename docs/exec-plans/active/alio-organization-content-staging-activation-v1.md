# ALIO Organization Content Staging Activation v1

Status: BLOCKED — staging activation stopped before ALIO observation acquisition on 2026-09-18.

## Objective

Activate the already-implemented ALIO item-4 Organization and executive content lane in the
existing `civic-intel-staging` environment. The lane must remain bounded by the existing
`SourcePolicy → Source → SourceSnapshot → FeederObservation → Claim/Evidence` path, and ALIO
executive names must not create or merge canonical Persons.

## Scope and guardrails

- Use only the existing `civic-intel-staging/staging` `api`, `web` and `postgres` services.
- No new service, resource, volume, domain, plan, cron, permanent worker, migration, schema
  change, production change or API-serving acquisition credential.
- No ALIO dry-run or commit is permitted without a fresh successful complete item-4
  enumeration and checkpoint.
- No raw report HTML, attachments, contacts, provider payloads or secrets enter the repository,
  receipt, public response or persistent observation.
- A failed acquisition is not a successful empty result and must not be resumed as if it were a
  complete checkpoint.

## Baseline

- Activation source revision: `ca1ff36e5dd6cebab018b3bdc1c4e7e4c160d410`.
- The existing implementation plan is complete; this plan records its separate staging
  activation operation.
- Existing staging topology: project `civic-intel-staging`, environment `staging`, services
  `web`, `api`, `postgres`; expected schema revision `0006`.
- Before activation, read-only counts were People `299`, Organizations `1`, Claims `1496`,
  organization Claims `2`, ALIO item-4 observations `0`, checkpoints `0`, and runs `0`.
- The existing C0908 Item-12 reviewed binding/MONEY path had `5` observations and `2` Claims.
- The API had no `ASSEMBLY_API_KEY`, `NEC_API_KEY` or `DART_API_KEY` variable.

## Phase 1 — existing-service deployment and read preflight

Completed without schema or topology change.

- API deployment `76ec8f69-8874-4fbb-a67c-eeda55d0fd19`: `SUCCESS`.
- Web deployment `8fad7294-d590-4aee-9381-71c5f3bfca6f`: `SUCCESS`.
- Postgres deployment `172ec443-e3cc-44bb-a5c1-195f54f86824`: unchanged and `SUCCESS`.
- The API and Web images were uploaded from an exact archive of the activation revision. The
  Railway metadata field `commitHash` is null for these local-archive uploads; the exact source
  revision is established by the archive input, not by a fabricated Railway commit field.
- Existing Web domain `web-staging-efe2.up.railway.app`, the single `postgres-volume`, trial
  plan and three-service topology remained unchanged.
- Pre-write route smoke returned `/`, `/people` and `/organizations` HTTP `200`. API-local
  read smoke after the failed acquisition returned `/ready` `200`, `/people` `299` and
  `/organizations` `1`.

## Phase 2 — logical backup and disposable restore

Completed and passed before any ALIO acquisition attempt.

- Railway-managed backup/PITR is unavailable on the current trial plan; it was not treated as a
  blocker and no plan upgrade was made.
- A private, provider-independent logical dump was created inside the existing Postgres
  container with `pg_dump --format=custom --no-owner` and kept outside the repository.
- Dump: `350919` bytes; SHA-256
  `e5c89bb0ee9168328f86753033bbd05d91ca25b0236ee3388561d1533db19878`.
- Restore target: a separate loopback-only disposable PostgreSQL cluster on local port `55440`.
  `pg_restore --format=custom --no-owner --exit-on-error` completed in `568 ms` with zero
  restore errors.
- Restored verification matched the staging baseline: schema `0006`, People `299`,
  Organizations `1`, Claims `1496`, organization Claims `2`, subject-XOR violations `0`,
  `1496` ClaimEvidence rows with exact observations, C0908 Item-12 `5` observations/`2`
  Claims, and the representative Person/Organization reads.
- The staging database was not reset, dropped or reloaded. The dump, restore cluster, tunnel
  logs and other task-owned temporary artifacts were removed after verification; disposable
  ports `55432`, `55433` and `55440` are closed.
- Temporary activation SSH registrations were removed. The Railway key list contains only the
  pre-existing `dev.new` key; the existing local staging key and other user SSH files were
  preserved.

## Phase 3 — bounded item-4 acquisition

Stopped fail-closed after one execution; no retry and no `--resume` were performed.

- Exact command executed in the existing API container: `python -m workers.public_institutions`.
  The container's existing `DATABASE_URL` was used; no credential or URL was printed.
- The worker could not reach the official ALIO item-4 endpoint from the API service. A single
  source-bounded diagnostic request from that container returned exception type
  `ConnectTimeout` with a timeout message. The worker surfaced the bounded acquisition failure
  as `AlioRecordError` and persisted one failed operational `SourceRun` with zero observations
  and zero committed rows.
- The command produced no usable success receipt, run identifier, observation or checkpoint.
  No ALIO item-4 Claim/Evidence publication, Organization creation, Person creation or merge
  occurred.
- Post-failure read-only counts remained People `299`, Organizations `1`, Claims `1496`,
  organization Claims `2`, ALIO item-4 observations `0`, checkpoints `0`, with one failed
  ALIO run. C0908 Item-12 and Assembly content were preserved.

## Phase 4/5 — importer and public ALIO content

Not run. The importer requires a successful complete item-4 checkpoint; that precondition was
not met. Consequently no dry-run, `--commit`, Organization Claim/Evidence delta or ALIO public
content activation is claimed.

## Gate result

The ALIO implementation remains eligible for a human-assisted/operator activation path, but this
staging operation is `BLOCKED` at acquisition. The blocker is private egress/reachability from
the existing execution boundary to the official ALIO item-4 endpoint, not an empty ALIO
universe. Existing source-policy, provenance, identity and publication gates remain intact.

Reopen only after the official endpoint is reachable from an approved private acquisition
boundary. Then take a fresh backup, run a new normal bounded enumeration, require a successful
complete checkpoint, and perform the importer dry-run before any explicit commit. Do not use
`--resume` for this failed run.

## Verification record

- Repository work was isolated in `.worktrees/alio-organization-activation`; the root checkout,
  its dirty user changes and other worktrees were preserved.
- Railway read-only verification after the operation showed the same three services, domain,
  Postgres volume, plan and resource topology; no new resource or domain was created.
- No ALIO raw payload or secret was retained in local artifacts, repository files or reports.
- The implementation baseline's CI Verify was already green before this activation operation.
  On this Windows host, the Make target itself was unavailable, so its verification commands
  were run directly: Ruff passed, mypy passed for `63` source files, Python passed with
  `367 passed, 1 skipped, 4 warnings`, Golden quality passed, and Web lint, typecheck, `11`
  UI tests and standalone production build passed. `git diff --cached --check` passed before
  commit; the post-push CI Verify remains the final repository-hosted check.

## Next concrete action

Restore private reachability from the approved acquisition boundary to the official ALIO item-4 endpoint, then take a fresh backup and run one new normal bounded enumeration before any importer action.

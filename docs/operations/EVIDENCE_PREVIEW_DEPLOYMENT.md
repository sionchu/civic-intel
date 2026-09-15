# Evidence Preview deployment preparation

Status: `DEPLOYED_PREVIEW` — public Web staging verified; API and PostgreSQL remain private.

This runbook defines and records the reviewed deployment contract for Evidence Preview v1. It is
not an authorization for production exposure, production database mutation, purchase or
ownership/access change.

## Selected artifact contract

The application requires three independently managed runtime roles:

- the Next standalone server produced by `npm --prefix apps/web run build`, including its copied
  `.next/static` tree;
- the FastAPI image built from `deploy/Dockerfile.api`, with `/health` for process liveness and
  `/ready` for schema and database connectivity;
- PostgreSQL at the current Alembic head, reached only through `DATABASE_URL`.

`compose.deploy.yml` is a loopback-bound rehearsal manifest. It builds the same two application
artifacts, runs migration as a one-shot job before API startup and waits for API readiness before
starting the web service. It is not a production topology or a credential store.

OpenAI Sites is not the selected host for this milestone. Its static output or Cloudflare
Workers-compatible server contract does not directly host this repository's separate Next server,
FastAPI process and PostgreSQL database. No `.openai/hosting.json`, Site registration or deployment
resource is therefore created.

## First host target

Railway staging is the selected first host contract. Its official project model supplies private
service networking, a PostgreSQL service, pre-deploy commands and health checks for this exact
three-resource shape. `.railway/railway.ts` is the sole provider specification; deprecated
`railway.json` and `railway.toml` service files are prohibited.

The specification is deliberately fail-closed outside an environment named `staging`. It pins the
GitHub source to `sionchu/civic-intel` `master`, builds the reviewed API and web Dockerfiles, runs
Alembic before API release, keeps API/PostgreSQL without public domains, and routes server-side web
reads over Railway private DNS. It does not declare a custom or generated public domain; the
generated Web domain is an explicit provider-side approval action recorded below. API and
PostgreSQL public access remain prohibited.

On 2026-09-14 the owner-approved `civic-intel-staging` project and isolated `staging` environment
were created. A read-only Railway IaC plan against that environment produced zero diagnostics,
zero changes and zero destroys. Its only proposed actions were the safe creation of `postgres`,
private `api` and private-networked `web`. That plan was subsequently applied after approval.

The approved plan was subsequently applied. API and web are private and running in Singapore; the
corrective API revision completed Alembic through `0006` and passed `/ready`. PostgreSQL was then
migrated from `sfo` to Singapore with the explicitly approved volume move. The observed volume
state progressed from `MIGRATING` with zero replicas to `READY` with one running replica. A
post-migration read-only IaC plan returned `No changes.` with zero diagnostics. After the separate
Web-only approval, the generated service domain
`https://web-staging-efe2.up.railway.app` became `ACTIVE`; API and PostgreSQL have no public URL.

At the current checkpoint, Railway-managed PostgreSQL backups/PITR are unavailable on the current
plan; the owner-observed staging Dashboard states that backups and point-in-time recovery are
available only for Pro customers. PITR remains disabled, no backup bucket is wired, and the backup
list/schedule remain empty. The approved provider-side backup creation attempts on 2026-09-14 and
2026-09-15 both returned `UNAUTHORIZED` / `Failed to create a backup`. No Pro upgrade,
billing/plan change or new Railway resource was made; managed backup is not an M1.4 blocker.

The M1.4 backup requirement was completed with a provider-independent logical rehearsal. On
2026-09-15, a private `railway connect postgres --tunnel-only` session performed read-only
inspection and `pg_dump`; a temporary SSH key was registered for that session and removed
afterward, and Railway then reported no registered SSH keys. Staging was at application revision
`b8c1f7666c8dcd2293da90a20cda1e41944a527c`, schema head `0006`, PostgreSQL `18.6`, with 26 public
tables. The checked canonical table counts were all `0`; subject-XOR and ClaimEvidence
provenance mismatch checks were `0`, and published/MONEY counts were `0`.

The custom-format dump used `--no-owner`, was captured at `2026-09-15T00:17:52.2664981Z`, measured
`57,261` bytes, and has SHA-256
`47CE121735FB27F9DCBCA9B297A2041FE25FFAA3F3CEAB2CEBE8050F5C834CAF`. It remains in a private
temporary path outside the repository and was not committed. `pg_restore --no-owner --exit-on-error`
restored it into a loopback-only disposable PostgreSQL `18.6` database named `restore_target` in
`0.321` seconds. Schema head, table set, canonical counts, subject-XOR/provenance checks and
MONEY counts matched. Against the restored database, `/ready` returned `200`, `/health` returned
`200`, `/people` returned `200` with zero rows and an unknown Organization returned `404`.
Both source and restored staging databases were empty, so no live staging MONEY pilot row existed
to compare; the non-empty pilot result remains separately evidenced by CI/fixtures. The original
staging database was not dropped, reset, migrated or written; only read-only inspection and
`pg_dump` were performed.

## Required runtime configuration

| Role | Variable | Rule |
| --- | --- | --- |
| API/migration | `DATABASE_URL` | Railway PostgreSQL output; normalize provider `postgresql://` URLs at the process boundary to the project's `postgresql+psycopg://` dialect. |
| API | `CIVIC_BOOTSTRAP_MODE` | Must be `runtime`; production must never use Golden bootstrap. |
| web | `CIVIC_API_URL` | Server-only routable API origin; do not expose credentials or private endpoints. |
| connector jobs | provider API keys | Add only to the one bounded job that needs them; never to web runtime. |

`NEXT_PUBLIC_API_URL` is only a compatibility fallback. A deployment should use
`CIVIC_API_URL`, because Server Components do not need a browser-public API origin.

## Release order

1. [x] Record the exact application commit and take a PostgreSQL custom-format logical backup.
   The provider-managed attempt was rejected with `UNAUTHORIZED`, so the receipt above records
   the private-tunnel `pg_dump` artifact, checksum and `--no-owner` contract.
2. [x] Restore that logical backup into a disposable database and run the restored-database
   verifier/API smoke. The local loopback PostgreSQL target passed schema, table/count,
   provenance, MONEY-count and `/ready`/`/health`/`/people`/404 checks.
3. Build both images and scan the build logs for copied secrets or ignored runtime databases.
4. Run `python -m alembic upgrade head` as a one-shot migration job against the approved target.
5. Start FastAPI and require `/ready` to return 200 before routing traffic.
6. Start the standalone web server with `CIVIC_API_URL` pointing to that API.
7. [x] Run the public roster and 404 browser smoke at the deployed revision. The root rendered an
   explicit empty roster after `GET /people 200`; an unknown profile rendered `Profile not found`
   after `GET /people/<unknown> 404`. The first post-migration request briefly rendered the safe
   `SERVICE_UNAVAILABLE` state while a terminated database connection was discarded; reload
   recovered to `200`. Organization MONEY, conflict and API-unavailable cases remain covered by
   the local/CI browser and API regressions, not by this empty staging deployment.

Runtime startup checks schema head and does not migrate or seed. Canonical data loading must use an
existing source-specific worker/import command and its publication/identity gates. For the bounded
reviewed ALIO pair, the repeatable command is `python -m workers.alio_reviewed_claim_import` with an
existing canonical Organization ID, institution code, two fiscal years, database URL and explicit
`--commit`. A dry run without `--commit` is required first. Ignored local databases and Golden
fixtures are never deployment inputs.

## Rollback and recovery

Application rollback means redeploying the previously recorded image/commit while leaving the
database at a schema version understood by that image. Database downgrade is allowed only on a
restored disposable copy and only when the migration's data preconditions pass. If a production
migration or load fails, stop new writes, retain the failed run receipt, restore the pre-release
backup into a new database, verify schema/count/provenance reads, and switch the application only
after an operator reviews that evidence. Never overwrite the failed database in place.

## Observed staging verification

| Check | Observed result |
| --- | --- |
| Web public domain | `https://web-staging-efe2.up.railway.app`, Railway service domain `ACTIVE` |
| API / PostgreSQL exposure | both service URLs `null`; private Singapore services, one running replica each |
| Web root | Evidence Directory rendered; `0` resolved identities / explicit empty roster |
| Web → API success | API `GET /people 200`; Web rendered the empty result, not an outage fallback |
| Public 404 | unknown UUID rendered `Profile not found`; API `GET /people/<unknown> 404` |
| IaC drift | read-only `railway config plan` returned `Your Railway configuration is already up to date.` |
| Managed Railway backup | PITR disabled, no backup bucket wired; both approved create attempts returned `UNAUTHORIZED`; current plan Dashboard says managed backup/PITR is Pro-only; no plan or billing change |
| Logical backup receipt | Custom format, `--no-owner`; `57,261` bytes; SHA-256 `47CE121735FB27F9DCBCA9B297A2041FE25FFAA3F3CEAB2CEBE8050F5C834CAF`; captured `2026-09-15T00:17:52.2664981Z` outside repository |
| Restore rehearsal | Loopback-only disposable PostgreSQL `18.6` / `restore_target`; `pg_restore` duration `0.321s`; schema/table/count/provenance/MONEY comparison `PASS` |
| Restored API smoke | `/ready 200`, `/health 200`, `/people 200` with zero rows, unknown Organization `404` |
| Original staging mutation | No reset/drop/schema change; the separately approved bounded ALIO run wrote four Sources, four SourceSnapshots, one checkpoint and 15 observation rows only. Temporary SSH key, client binaries, disposable cluster and API process removed after proof |
| CI after logical proof | GitHub Actions `Verify` run `34913882587`, pushed commit `6d979cdbd925f94328d578c3f941cb295d815201`, `success` in `2m25s`; canonical, migration, PostgreSQL load/API, backup/restore and deployment artifact checks passed |
| Bounded ALIO staging load | Run `40ba451d-4d57-4f18-bbdb-122c516ebfde`, `SUCCESS`; allowlist `C0019,C0129,C0908`; 15 observations; two SourceRuns including the first fail-closed attempt; schema `0006`; zero People/Organizations/Claims/ClaimEvidence |
| Bounded ALIO read QA | Three distinct report snapshots; zero fulltext, empty identity hints, zero orphan observations, subject-XOR/provenance mismatch `0`; local `/health 200`, `/ready 200`, `/people 200` with zero rows and unknown Organization `404` |
| CI after ALIO boundary fix | GitHub Actions `Verify` run `34916320972`, commit `d06b0cc6f7c8d0313a1973a1dbafb02b0f83d20a`, `success`; canonical, migration, PostgreSQL load/API, backup/restore and deployment artifact checks passed |

## Approval boundary

The Web-only public domain and its browser smoke were explicitly approved and completed. API and
database public access remain prohibited. Railway-managed backup/PITR is unavailable on the current
plan and is not required for this checkpoint; the separately approved provider-independent logical
backup/restore rehearsal passed. Persistent provider backup configuration and unbounded operational
loading remain outside this checkpoint. The current deployment classification is
`DEPLOYED_PREVIEW`: staging contains observation-only ALIO data, while no canonical Person,
Organization, Claim or public FACT was loaded.

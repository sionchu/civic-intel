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

At the current checkpoint, Railway reports PostgreSQL PITR disabled and no backup bucket wired.
The approved on-demand volume-backup attempt for `pre-restore-rehearsal-2026-09-14` returned
`UNAUTHORIZED` / `Failed to create a backup`; the command was not retried. The backup list and
automatic schedule remain empty. The local host has no PostgreSQL client tools, and private SSH
inspection needs a new SSH key; no new credential, persistent backup configuration, backup snapshot,
restore, or database-content mutation was created. Data loading remains outside this deployment
checkpoint. On 2026-09-15, owner-operated OAuth login completed and the same read-only Railway
project/service/volume/backup/PITR/schedule calls succeeded. A single retry of the approved backup
creation under the fresh login still returned `UNAUTHORIZED` / `Failed to create a backup`; the
backup list remains empty and no interactive or further resource mutation was attempted. A fresh
provider-side authorization or feature-entitlement decision is required before resuming this gate.

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

1. [blocked] Record the exact application commit and take a PostgreSQL custom-format backup. The
   approved provider-side volume-backup attempt was rejected with `UNAUTHORIZED` before a snapshot
   existed.
2. Restore that backup into a disposable database and run
   `python -m packages.verification.postgresql` against the restored URL.
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
| Backup rehearsal | `railway postgres pitr backup create` returned `UNAUTHORIZED`; backup list and automatic schedule remain empty; restore not run |

## Approval boundary

The Web-only public domain and its browser smoke were explicitly approved and completed. API and
database public access remain prohibited. The backup/restore rehearsal was separately approved but
is currently blocked by the provider-side authorization response and subsequent CLI authentication
failure above; persistent backup/PITR configuration and operational data loading remain outside this
checkpoint. The current deployment classification is `DEPLOYED_PREVIEW`, with no operational data
loaded.

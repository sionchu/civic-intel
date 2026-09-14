# Evidence Preview deployment preparation

Status: `TARGET_STAGED`, not deployed.

This runbook defines the reviewed deployment contract for Evidence Preview v1. It creates no
infrastructure and authorizes no public exposure, production database mutation, purchase or
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
reads over Railway private DNS. It does not declare a custom or generated public domain. Creating
the Railway project/environment, accepting billable usage, applying the plan and generating the
web domain remain operator approval actions.

On 2026-09-14 the owner-approved `civic-intel-staging` project and isolated `staging` environment
were created. A read-only Railway IaC plan against that environment produced zero diagnostics,
zero changes and zero destroys. Its only proposed actions are the safe creation of `postgres`,
private `api` and private-networked `web`. At that review checkpoint, the plan was not applied:
no database, service, deployment, public domain or operational data existed.

The approved plan was subsequently applied. API and web are private and running in Singapore; the
corrective API revision completed Alembic through `0006` and passed `/ready`. The PostgreSQL
service and its 500 MB volume were instead created in `sfo`. A new read-only IaC plan identifies
the intended move to Singapore as `destructive`. Railway's volume contract states that this kind
of regional move migrates the volume with downtime, so it requires separate approval and has not
been applied. No public domain or operational data load exists.

At the current checkpoint, Railway reports PostgreSQL PITR disabled and no backup bucket wired.
The local host has no PostgreSQL client tools, and private SSH inspection needs a new SSH key; no
new credential, persistent backup configuration or one-off backup was created. The migration plan
remains pending explicit acknowledgement of its destructive downtime/data-loss risk.

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

1. Record the exact application commit and take a PostgreSQL custom-format backup.
2. Restore that backup into a disposable database and run
   `python -m packages.verification.postgresql` against the restored URL.
3. Build both images and scan the build logs for copied secrets or ignored runtime databases.
4. Run `python -m alembic upgrade head` as a one-shot migration job against the approved target.
5. Start FastAPI and require `/ready` to return 200 before routing traffic.
6. Start the standalone web server with `CIVIC_API_URL` pointing to that API.
7. Run the public roster, Person evidence, Organization MONEY, 404, conflict and API-unavailable
   browser smoke at the deployed revision.

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

## Approval boundary

Migrating the selected Railway staging PostgreSQL volume between regions, accepting billable usage,
creating its public web domain, changing access, or running against an operational database
requires explicit approval. Until the regional topology and deployed browser smoke are complete,
the only valid state is `TARGET_STAGED`.

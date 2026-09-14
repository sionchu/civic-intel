# Railway first deployment v0

Status: completed — private API/DB and public Web staging preview verified; data load deferred.

Date: 2026-09-14

## Objective

Deploy the verified Evidence Preview artifact to one isolated Railway `staging` environment,
keeping FastAPI and PostgreSQL private and exposing only the Next web service. Preserve the
canonical migration, publication, identity and provenance gates; a successful empty/fixture host
does not become live-data evidence.

## Why this target

Railway's current official contract provides project-scoped private networking, PostgreSQL,
pre-deploy commands, health checks, Southeast Asia placement and reviewed configuration changes.
It fits the existing two-image plus database architecture without adapting the application to a
serverless runtime. OpenAI Sites remains unsuitable for this runtime, and deprecated Railway
per-service config files are not used.

## Scope and boundary

- `.railway/railway.ts` is the single environment graph and may target only `staging`.
- Source is `sionchu/civic-intel` `master`; API and web use the existing reviewed Dockerfiles.
- PostgreSQL supplies the API `DATABASE_URL`; web reaches API only through private DNS.
- API runs `python -m alembic upgrade head` before release and must pass `/ready`.
- No provider key, local/ignored database, Golden fixture or reviewed local ALIO database is a
  deployment input.
- No production environment, public API/database endpoint, custom domain, automatic feeder,
  operational data load or source maturity change is in scope. The only public endpoint is the
  Railway-generated Web domain created after explicit approval; API and PostgreSQL remain private.

Creating resources, accepting billable usage, applying the IaC plan and generating a public web
domain are external state changes and require explicit operator approval. Before that approval the
valid state is `TARGET_STAGED`, not `DEPLOYED`.

## Execution

1. Type-check the IaC graph and pass repository verification/CI.
2. Owner authenticates the Railway CLI and creates or selects a private project with an isolated
   `staging` environment.
3. Run `railway config plan` and record the exact add/change/destroy summary. Any destroy or
   production target is a hard stop.
4. [x] After approval, apply the saved staging plan and generate a public domain only for `web`.
5. [x] Verify migration head, `/ready`, public roster, Person evidence, Organization states, 404 and
   API-unavailable behavior in the deployed browser artifact.
6. Configure and verify a database backup before any non-fixture data load. Data loading remains a
   separate reviewed operation.

## Acceptance

- Local TypeScript and repository checks pass; CI validates both Docker images and the IaC file.
- The applied plan contains exactly `postgres`, private `api` and public-domain-eligible `web` in
  `staging`, with zero destroys.
- Only the web URL is public; direct API and database public access are absent.
- The deployed SHA is recorded and every host-level smoke result is observed, not inferred.
- Deployment and data state are reported separately as empty, fixture, reviewed, live and
  published.

## Current evidence

- Official Railway documentation was reviewed on 2026-09-14. New services must use project-level
  `.railway/railway.ts`; deprecated `railway.json`/`railway.toml` cannot be selected for new
  services and reach hard cutoff on 2026-12-01.
- Railway CLI, Render CLI and Fly CLI were absent locally; GitHub reported zero repository
  environments and zero deployments.
- Railway SDK `3.11.0` and TypeScript `5.9.2` are isolated under `.railway`; `npm run check` passed.
- Contract tests for staging-only scope, Dockerfiles, migration, readiness, private API DNS and no
  declared public domain passed locally.
- GitHub Actions run `34840650378` at `a1cdacd7326c758110eb03b946e0245330bc9963`
  passed canonical verification, PostgreSQL backup/restore, both Node 22/Python Docker builds,
  Compose validation and the Railway IaC typecheck.
- The owner-operated CLI authenticated on 2026-09-14. Project `civic-intel-staging` and its
  isolated `staging` environment were created with zero services. The untouched default
  `production` environment also has zero services.
- A read-only `railway config plan` against `staging` succeeded. It proposes exactly three safe
  creates — database `postgres`, service `api`, and service `web` — with zero changes, zero
  destroys and no diagnostics. The plan was not applied; no service, database, deployment, domain
  or operational data exists.
- The first plan attempt exposed a local CLI-discovery defect: the IaC SDK invoked the process
  path stored in `process.env._` rather than the transient `npx` CLI. Explicitly pointing that
  value at the verified Railway CLI `5.54.1` produced the successful read-only plan. This is a
  local invocation detail only; no provider configuration changed.
- The approved pinned plan was applied on 2026-09-14. Railway created `postgres`, `api` and
  `web`; no public domain was generated. PostgreSQL started, but the first API pre-deploy
  migration failed because Railway supplied `postgresql://` while the project ships only the
  `psycopg` DBAPI. The provider URL is now normalized once at the repository/Alembic boundary to
  `postgresql+psycopg://`; local full verification passed before the corrective revision is pushed.
- GitHub Actions run `34845467011` at `b8c1f7666c8dcd2293da90a20cda1e41944a527c` passed the
  full verification, including PostgreSQL migration/load/restore and both deployment artifacts.
  Railway's corrective API deployment at that revision succeeded: Alembic applied `0001` through
  `0006`, and the observed `/ready` probe returned `200`. The private web service is also running;
  neither service has a public URL.
- Railway initially reported API and web in `asia-southeast1-eqsg3a`, but `postgres` and its 500 MB
  volume were in `sfo`. The explicitly approved volume migration was applied on 2026-09-14. During
  the observed move the PostgreSQL volume reported `MIGRATING` with zero replicas; it recovered
  with the volume `READY`, one running replica and the region `asia-southeast1-eqsg3a`.
- Before the requested move, Railway reported PostgreSQL PITR disabled and no backup bucket wired.
  The local host has no PostgreSQL client, and private SSH inspection would require creating an
  SSH key; neither a new credential nor a persistent backup configuration was created. No
  operational data load has been run. No PITR or one-off backup was configured.
- After migration, a read-only IaC plan returned `No changes.` with zero diagnostics. API, Web and
  PostgreSQL each report `SUCCESS` with one running replica; API and database have no public URL.
- Following the explicit approval to expose Web only, `railway domain --service web` created
  `https://web-staging-efe2.up.railway.app`. Railway reports the service domain `ACTIVE`; the
  service listing shows this URL only on `web` and keeps `api` and `postgres` at `url: null`.
- Browser smoke at the generated Web URL rendered the Evidence Directory home and an explicit
  empty roster (`0` resolved identities) after the API returned `200`. The deployed profile route
  for UUID `00000000-0000-0000-0000-000000000000` rendered `Profile not found`; the API log shows
  `GET /people/<unknown> 404`. The API log also shows the successful `GET /people 200` responses.
- The first post-migration browser request observed `SERVICE_UNAVAILABLE` while the API reused a
  database connection terminated by the approved volume move (`psycopg.errors.AdminShutdown`). A
  reload recovered to `200` without a code or configuration change; this transient recovery is
  recorded, not hidden. No operational data load has been run and the default `production`
  environment remains empty.

## Next action

Obtain explicit approval for a PostgreSQL backup/restore rehearsal, then complete it before any
operational or feeder data load; API/DB exposure remains prohibited.

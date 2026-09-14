# Railway first deployment v0

Status: active — provider contract staged; no Railway resources created.

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
  operational data load or source maturity change is in scope.

Creating resources, accepting billable usage, applying the IaC plan and generating a public web
domain are external state changes and require explicit operator approval. Before that approval the
valid state is `TARGET_STAGED`, not `DEPLOYED`.

## Execution

1. Type-check the IaC graph and pass repository verification/CI.
2. Owner authenticates the Railway CLI and creates or selects a private project with an isolated
   `staging` environment.
3. Run `railway config plan` and record the exact add/change/destroy summary. Any destroy or
   production target is a hard stop.
4. After approval, apply the saved staging plan and generate a public domain only for `web`.
5. Verify migration head, `/ready`, public roster, Person evidence, Organization states, 404 and
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
  declared public domain passed locally. No Railway account, token, project, service or database
  was accessed or created.

## Next action

Authenticate the owner-operated Railway CLI, create/select the isolated `staging` environment and
run a read-only `railway config plan` before any apply.

import { defineRailway, github, postgres, project, service } from "railway/iac";

const REGION = "asia-southeast1-eqsg3a";
const SOURCE = "sionchu/civic-intel";

export default defineRailway((ctx) => {
  const permittedEnvironment =
    ctx.isEnvironment("staging") || ctx.isEnvironment("production");
  if (!permittedEnvironment) {
    throw new Error(
      "Civic Intel Railway IaC is restricted to staging or production environments.",
    );
  }

  const database = postgres("postgres", { region: REGION });

  const api = service("api", {
    source: github(SOURCE, { branch: "master" }),
    build: {
      builder: "DOCKERFILE",
      dockerfilePath: "deploy/Dockerfile.api",
      watchPatterns: [
        "apps/api/**",
        "packages/**",
        "workers/**",
        "migrations/**",
        "deploy/Dockerfile.api",
        "pyproject.toml",
        "alembic.ini",
      ],
    },
    preDeploy: "python -m alembic upgrade head",
    healthcheck: "/ready",
    healthcheckTimeout: 120,
    replicas: { [REGION]: 1 },
    env: {
      CIVIC_BOOTSTRAP_MODE: "runtime",
      DATABASE_URL: database.env.DATABASE_URL,
      PORT: "8000",
    },
  });

  // Public domains and indexing variables are intentionally not declared here.
  // Production remains non-public/non-indexable until a separately approved launch action.
  const web = service("web", {
    source: github(SOURCE, { branch: "master" }),
    build: {
      builder: "DOCKERFILE",
      dockerfilePath: "deploy/Dockerfile.web",
      watchPatterns: ["apps/web/**", "deploy/Dockerfile.web"],
    },
    healthcheck: "/",
    healthcheckTimeout: 120,
    replicas: { [REGION]: 1 },
    env: {
      CIVIC_API_URL: "http://${{api.RAILWAY_PRIVATE_DOMAIN}}:8000",
      PORT: "3000",
    },
  });

  return project("civic-intel", { resources: [database, api, web] });
});

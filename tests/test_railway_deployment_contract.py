from pathlib import Path

ROOT = Path(__file__).parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_railway_iac_is_staging_only_and_keeps_backend_private() -> None:
    spec = read(".railway/railway.ts")

    assert 'ctx.isEnvironment("staging")' in spec
    assert 'github(SOURCE, { branch: "master" })' in spec
    assert 'postgres("postgres", { region: REGION })' in spec
    assert 'dockerfilePath: "deploy/Dockerfile.api"' in spec
    assert 'dockerfilePath: "deploy/Dockerfile.web"' in spec
    assert 'preDeploy: "python -m alembic upgrade head"' in spec
    assert 'healthcheck: "/ready"' in spec
    assert 'CIVIC_BOOTSTRAP_MODE: "runtime"' in spec
    assert 'DATABASE_URL: database.env.DATABASE_URL' in spec
    assert 'CIVIC_API_URL: "http://${{api.RAILWAY_PRIVATE_DOMAIN}}:8000"' in spec
    assert "domains:" not in spec


def test_railway_iac_uses_current_non_deprecated_sdk() -> None:
    package = read(".railway/package.json")

    assert '"railway": "3.11.0"' in package
    assert "railway.json" not in package
    assert "railway.toml" not in package

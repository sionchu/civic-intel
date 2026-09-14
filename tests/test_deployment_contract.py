from pathlib import Path

ROOT = Path(__file__).parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_container_context_excludes_secrets_runtime_data_and_build_outputs() -> None:
    ignored = set(read(".dockerignore").splitlines())

    assert {".env", ".git", ".venv", "*.db", "**/.next", "**/node_modules"} <= ignored


def test_api_and_web_images_have_separate_runtime_contracts() -> None:
    api = read("deploy/Dockerfile.api")
    web = read("deploy/Dockerfile.web")

    assert "apps.api.main:app" in api
    assert "127.0.0.1:8000/ready" in api
    assert "USER civic" in api
    assert "/build/.next/standalone" in web
    assert "node server.js" not in web
    assert 'CMD ["node", "server.js"]' in web
    assert "USER node" in web


def test_rehearsal_manifest_is_loopback_bound_and_migrates_before_api() -> None:
    compose = read("compose.deploy.yml")

    assert "POSTGRES_PASSWORD is required" in compose
    assert "DATABASE_URL is required" in compose
    assert 'command: ["python", "-m", "alembic", "upgrade", "head"]' in compose
    assert "condition: service_completed_successfully" in compose
    assert "CIVIC_BOOTSTRAP_MODE: runtime" in compose
    assert "CIVIC_API_URL: http://api:8000" in compose
    assert '"127.0.0.1:${CIVIC_API_PORT:-8000}:8000"' in compose
    assert '"127.0.0.1:${CIVIC_WEB_PORT:-3000}:3000"' in compose


def test_deployment_runbook_preserves_approval_and_sites_boundaries() -> None:
    runbook = read("docs/operations/EVIDENCE_PREVIEW_DEPLOYMENT.md")

    assert "Status: `PREPARED`, not deployed." in runbook
    assert "No `.openai/hosting.json`" in runbook
    assert "requires explicit approval" in runbook
    assert "production must never use Golden bootstrap" in runbook

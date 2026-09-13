from pathlib import Path


WORKFLOW = Path(".github/workflows/assembly-roster-observation-audit.yml")


def test_assembly_roster_audit_workflow_is_manual_and_observation_only() -> None:
    body = WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in body
    assert "pull_request:" not in body
    assert "\n  push:" not in body
    assert "secrets.ASSEMBLY_API_KEY" in body
    assert "--enumerate" in body
    assert "--materialize" not in body
    assert "--name" not in body
    assert "--party" not in body
    assert "--district" not in body
    assert '"materialization_performed": False' in body


def test_assembly_roster_audit_artifact_excludes_raw_database_and_credentials() -> None:
    body = WORKFLOW.read_text(encoding="utf-8")
    upload_block = body.split("- name: Upload observation audit", maxsplit=1)[1]

    assert "assembly-roster-run.json" in upload_block
    assert "assembly-roster-coverage.json" in upload_block
    assert "assembly-roster-audit.db" not in upload_block
    assert "ASSEMBLY_API_KEY" not in upload_block
    assert "raw" not in upload_block.casefold()

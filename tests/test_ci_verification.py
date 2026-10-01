from types import SimpleNamespace
from uuid import UUID

import pytest

from packages.verification.assembly_roster_failure_smoke import validate_failure
from packages.verification.assembly_roster_observation_audit import (
    build_report,
    current_observations,
)


def test_missing_key_smoke_requires_redacted_receipt_and_zero_effect():
    run = SimpleNamespace(
        feeder="national_assembly_members",
        scope_key="current_member_roster",
        status=SimpleNamespace(value="FAILED"),
        checkpoint_after=None,
        error_code="MissingAssemblyApiKey",
        error_summary="Assembly enumeration did not complete",
        records_seen=0,
        observations_created=0,
        observations_unchanged=0,
    )
    receipt = {
        "command": "observe assembly",
        "effect": "SOURCE_INGESTION",
        "error_code": "COMMAND_FAILED",
        "status": "FAILED",
    }
    validate_failure(receipt, exit_code=1, run=run, checkpoint=None)

    with pytest.raises(RuntimeError, match="redacted contract"):
        validate_failure(receipt | {"details": "provider detail"}, exit_code=1, run=run, checkpoint=None)
    committed_run = SimpleNamespace(**(run.__dict__ | {"records_seen": 1}))
    with pytest.raises(RuntimeError, match="committed observations"):
        validate_failure(receipt, exit_code=1, run=committed_run, checkpoint=None)


def test_roster_audit_exports_only_allowlisted_normalized_fields():
    run_id = UUID("00000000-0000-0000-0000-000000000001")
    observation = SimpleNamespace(
        provider_record_key="member-1",
        content_hash="a" * 64,
        semantic_scope="legislative_member_roster",
        id=UUID("00000000-0000-0000-0000-000000000002"),
        snapshot_id=UUID("00000000-0000-0000-0000-000000000003"),
        normalized={
            "canonical_name": "Example",
            "aliases": [],
            "party": "Party",
            "provider_payload": "must not be exported",
        },
    )
    checkpoint = SimpleNamespace(
        last_run_id=run_id,
        cursor="1",
        metadata={
            "seen_provider_hashes": {"member-1": "a" * 64},
            "list_total_count": 1,
            "expected_pages": 1,
            "source_contract": "assembly_member_roster",
        },
    )
    run = SimpleNamespace(
        id=run_id,
        status=SimpleNamespace(value="SUCCESS"),
        checkpoint_after="1",
        records_seen=1,
        observations_created=1,
        observations_unchanged=0,
    )
    receipt = {
        "effect": "SOURCE_INGESTION",
        "command": "observe assembly",
        "result": {
            "run": {"id": str(run_id), "status": "SUCCESS"},
            "unique_records": 1,
            "pages_committed": 1,
        },
    }

    report = build_report(receipt, checkpoint=checkpoint, run=run, observations=[observation])
    assert report["materialization_performed"] is False
    assert report["current_observation_count"] == 1
    assert set(report["rows"][0]) == {
        "provider_record_key",
        "observation_id",
        "snapshot_id",
        "content_hash",
        "canonical_name",
        "aliases",
        "birth_date",
        "party",
        "district",
        "reelection",
        "election_type",
        "committees",
    }
    assert "provider_payload" not in str(report)


def test_roster_audit_rejects_manifest_version_or_coverage_drift():
    item = SimpleNamespace(
        provider_record_key="member-1",
        content_hash="b" * 64,
        semantic_scope="legislative_member_roster",
    )
    with pytest.raises(RuntimeError, match="do not match"):
        current_observations([item], {"member-1": "a" * 64})

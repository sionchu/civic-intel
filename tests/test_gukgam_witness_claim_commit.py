from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from apps.api.main import create_app
from packages.domain.db import OrganizationRow, PersonObservationLinkRow, PersonRow
from tests.test_gukgam_witness import cli, insert_organization, migrated_repository, write_inputs
from workers.gukgam_witness_claim_commit import committee_organization_for
from workers.gukgam_witness_claim_commit import main as claim_main
from workers.gukgam_witness_import import main as import_main


def imported(tmp_path: Path, status: str = "HUMAN_REVIEWED"):  # type: ignore[no-untyped-def]
    repository, database_url = migrated_repository(tmp_path / "witness.db")
    packet, artifact = write_inputs(tmp_path)
    assert import_main(cli(packet, artifact, "--database-url", database_url, "--commit")) == 0
    if status != "HUMAN_REVIEWED":
        raw = json.loads(packet.read_text(encoding="utf-8"))
        raw["review_status"] = status
        packet.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    return repository, database_url, packet


def run(capsys: pytest.CaptureFixture[str], *args: str) -> dict:
    assert claim_main(list(args)) == 0
    return json.loads(capsys.readouterr().out)


def test_dry_run_requires_committee_subject_and_writes_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repository, database_url, packet = imported(tmp_path)
    capsys.readouterr()
    with pytest.raises(SystemExit):
        claim_main(["--packet", str(packet), "--database-url", database_url])
    report = run(
        capsys, "--packet", str(packet), "--database-url", database_url,
        "--create-committee-organizations",
    )
    assert report["status"] == "DRY_RUN"
    assert report["claim_count"] == 3
    assert report["packets"][0]["organization_action"] == "CREATE"
    assert report["packets"][0]["organization_name"] == "국회 합성시험위원회"
    assert report["person_materialization"] is False
    with repository.sessions() as session:
        assert session.scalar(select(func.count()).select_from(OrganizationRow)) == 0


def test_commit_needs_the_exact_plan_and_is_idempotent(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repository, database_url, packet = imported(tmp_path)
    capsys.readouterr()
    base = ["--packet", str(packet), "--database-url", database_url, "--create-committee-organizations"]
    plan = run(capsys, *base)["plan_sha256"]
    with pytest.raises(SystemExit):
        claim_main([*base, "--commit", "--expected-plan-sha256", "0" * 64])
    first = run(capsys, *base, "--commit", "--expected-plan-sha256", plan)
    assert first["status"] == "COMMITTED"
    assert first["organizations_created"] == 1
    assert first["claims_created"] == 3
    # Rerun reuses the committee Organization and the same deterministic Claims.
    second_plan = run(capsys, *base)
    assert second_plan["packets"][0]["organization_action"] == "REUSE"
    second = run(capsys, *base, "--commit", "--expected-plan-sha256", second_plan["plan_sha256"])
    assert second["claims_created"] == 0
    assert second["claims_reused"] == 3

    with repository.sessions() as session:
        assert session.scalar(select(func.count()).select_from(PersonRow)) == 0
        assert session.scalar(select(func.count()).select_from(PersonObservationLinkRow)) == 0
    committee = repository.organization(committee_organization_for("합성시험위원회").id)
    assert committee is not None and committee.name == "국회 합성시험위원회"

    with TestClient(create_app(repository)) as client:
        body = client.get("/gukgam/2026/witnesses").json()
    assert body["witness_count"] == 2
    assert body["reference_person_count"] == 1
    assert {item["subject_scope"] for item in body["items"]} == {"COMMITTEE"}
    serialized = json.dumps(body, ensure_ascii=False)
    for forbidden in ("person_id", "request_reason", "신청사유", "identity_hints"):
        assert forbidden not in serialized


def test_existing_committee_organization_is_reused_not_duplicated(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repository, database_url, packet = imported(tmp_path)
    existing = insert_organization(repository, "합성시험위원회")
    capsys.readouterr()
    report = run(capsys, "--packet", str(packet), "--database-url", database_url)
    assert report["packets"][0]["organization_action"] == "REUSE"
    assert report["packets"][0]["organization_name"] == "합성시험위원회"
    run(capsys, "--packet", str(packet), "--database-url", database_url, "--commit",
        "--expected-plan-sha256", report["plan_sha256"])
    with repository.sessions() as session:
        assert session.scalar(select(func.count()).select_from(OrganizationRow)) == 1
    assert repository.organization(existing) is not None


def test_unreviewed_or_unimported_packets_are_refused(tmp_path: Path) -> None:
    _, database_url, packet = imported(tmp_path, "REVIEW_REQUIRED")
    with pytest.raises(SystemExit):
        claim_main(["--packet", str(packet), "--database-url", database_url,
                    "--create-committee-organizations"])
    other = tmp_path / "other"
    other.mkdir()
    _, fresh_url = migrated_repository(other / "empty.db")
    packet2, _ = write_inputs(other)
    with pytest.raises(SystemExit):
        claim_main(["--packet", str(packet2), "--database-url", fresh_url,
                    "--create-committee-organizations"])


def test_source_tags_and_image_copies_follow_the_owner_rule() -> None:
    from packages.connectors.gukgam_witness_packet import (
        OWNER_COPY_LABEL,
        GukgamWitnessPacketError,
        parse_reviewed_gukgam_witness_packet,
        witness_source_tag,
    )
    from tests.test_gukgam_witness import owner_payload, payload

    assert "아직 공식 발표 아님" in OWNER_COPY_LABEL
    assert witness_source_tag("OFFICIAL_SITE", "PDF") == "#공식게시"
    assert witness_source_tag("OFFICIAL_MINUTES", "PDF") == "#공식회의록"
    assert witness_source_tag("OWNER_SUPPLIED_COPY", "HWP") == "#제공사본_HWP"
    assert witness_source_tag("OWNER_SUPPLIED_COPY", "JPG") == "#제공사본_비HWP"

    image_copy = owner_payload()
    image_copy["source"]["artifact_format"] = "JPG"
    for row in image_copy["rows"]:
        row["locator"]["page_number"] = None
    assert parse_reviewed_gukgam_witness_packet(image_copy).source.artifact_format == "JPG"

    official_image = payload()
    official_image["source"]["artifact_format"] = "JPG"
    with pytest.raises(GukgamWitnessPacketError, match="image artifacts"):
        parse_reviewed_gukgam_witness_packet(official_image)


def test_projection_exposes_the_source_tag(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repository, database_url, packet = imported(tmp_path)
    capsys.readouterr()
    base = ["--packet", str(packet), "--database-url", database_url, "--create-committee-organizations"]
    plan = run(capsys, *base)["plan_sha256"]
    run(capsys, *base, "--commit", "--expected-plan-sha256", plan)
    with TestClient(create_app(repository)) as client:
        body = client.get("/gukgam/2026/witnesses").json()
    assert {item["source_tag"] for item in body["items"]} == {"#공식게시"}

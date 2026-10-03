from __future__ import annotations

import copy
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from apps.api.main import create_app
from packages.connectors.gukgam_witness_packet import (
    GukgamWitnessPacketError,
    parse_reviewed_gukgam_witness_packet,
)
from packages.domain.contracts import Organization
from packages.domain.db import (
    FeederObservationRow,
    OrganizationRow,
    PersonObservationLinkRow,
    PersonRow,
)
from packages.persistence import SqlAlchemyRepository
from packages.rendering.gukgam_witness_claim import (
    GUKGAM_PUBLIC_WITNESS_COVERAGE,
    GUKGAM_PUBLIC_WITNESS_PROJECTION_SEMANTICS,
    SUBJECT_SCOPE_COMMITTEE,
    SUBJECT_SCOPE_TARGET_INSTITUTION,
    GukgamWitnessClaimError,
    build_gukgam_witness_claim,
)
from packages.verification.gukgam_witness_import import (
    GUKGAM_WITNESS_FEEDER,
    GukgamWitnessImportError,
    build_gukgam_witness_capture,
)
from workers.gukgam_witness_import import main

FIXTURE = Path("tests/fixtures/gukgam_2026_synthetic_witness_reviewed_packet.json")
ARTIFACT_BYTES = b"SYNTHETIC-WITNESS-LIST-FIXTURE\n"


def payload(status: str = "HUMAN_REVIEWED") -> dict:
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    raw["review_status"] = status
    return raw


def migrated_repository(database: Path) -> tuple[SqlAlchemyRepository, str]:
    database_url = f"sqlite:///{database.as_posix()}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")
    return SqlAlchemyRepository(database_url), database_url


def insert_organization(repository: SqlAlchemyRepository, name: str) -> UUID:
    organization_id = uuid4()
    now = datetime.now(UTC)
    with repository.sessions() as session:
        session.add(
            OrganizationRow(
                id=str(organization_id),
                name=name,
                valid_from=now,
                valid_to=None,
                recorded_at=now,
                superseded_at=None,
            )
        )
        session.commit()
    return organization_id


def write_inputs(tmp_path: Path, status: str = "HUMAN_REVIEWED") -> tuple[Path, Path]:
    packet = tmp_path / "packet.json"
    packet.write_text(json.dumps(payload(status), ensure_ascii=False), encoding="utf-8")
    artifact = tmp_path / "list.pdf"
    artifact.write_bytes(ARTIFACT_BYTES)
    return packet, artifact


def cli(packet: Path, artifact: Path, *extra: str) -> list[str]:
    return [
        "--packet",
        str(packet),
        "--artifact",
        str(artifact),
        "--confirm-exact-attachment-rights",
        *extra,
    ]


def test_fixture_is_review_required_and_parses() -> None:
    packet = parse_reviewed_gukgam_witness_packet(payload("REVIEW_REQUIRED"))
    assert not packet.is_human_reviewed
    assert len(packet.rows) == 3
    assert packet.record_key(packet.rows[0]) == "2026:합성시험위원회:ADOPTED-2026-09-28:1"
    assert hashlib.sha256(ARTIFACT_BYTES).hexdigest() == packet.source.attachment_sha256


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda p: p["rows"][0].update(phone="010-1234-5678"), "unsupported fields"),
        (lambda p: p["rows"][0].update(affiliation_title="a@b.co"), "contact details"),
        (lambda p: p["rows"][0].update(affiliation_title="02-123-4567"), "contact details"),
        (lambda p: p["rows"][0].update(category="피고인"), "category"),
        (lambda p: p["rows"][1].update(row_number=1), "unique and ordered"),
        (lambda p: p["rows"][1]["locator"].update(table_row=1), "locators must be unique"),
        (lambda p: p["declared_totals"].update({"증인": 3}), "declared total"),
        (lambda p: p["source"].update(page_url="https://example.com/x"), "official https"),
        (lambda p: p["source"].update(attachment_sha256="abc"), "attachment_sha256"),
        (lambda p: p["source"].update(automation_gate="OPEN"), "automation gate"),
        (lambda p: p["source"].update(list_version="a b/c"), "key-safe"),
        (lambda p: p.update(review_status="PUBLISHED"), "review_status"),
        (lambda p: p.update(person_id="x"), "unsupported fields"),
    ],
)
def test_packet_rejects_unsafe_shapes(mutate, message: str) -> None:  # type: ignore[no-untyped-def]
    raw = copy.deepcopy(payload())
    mutate(raw)
    with pytest.raises(GukgamWitnessPacketError, match=message):
        parse_reviewed_gukgam_witness_packet(raw)


def test_capture_requires_human_review_and_exact_artifact() -> None:
    with pytest.raises(GukgamWitnessImportError, match="HUMAN_REVIEWED"):
        build_gukgam_witness_capture(
            parse_reviewed_gukgam_witness_packet(payload("REVIEW_REQUIRED")),
            artifact_bytes=ARTIFACT_BYTES,
        )
    packet = parse_reviewed_gukgam_witness_packet(payload())
    with pytest.raises(GukgamWitnessImportError, match="sha256"):
        build_gukgam_witness_capture(packet, artifact_bytes=b"other")
    capture = build_gukgam_witness_capture(packet, artifact_bytes=ARTIFACT_BYTES)
    assert capture.snapshot.fulltext is None
    assert capture.snapshot.content_hash == packet.source.attachment_sha256
    assert "reviewed_packet_hash" not in capture.snapshot.metadata
    assert capture.policy.can_fetch is False
    assert capture.policy.can_show_excerpt is False
    observations = capture.observations(uuid4())
    assert [o.provider_record_key for o in observations] == [
        f"2026:합성시험위원회:ADOPTED-2026-09-28:{n}" for n in (1, 2, 3)
    ]
    assert all(o.identity_hints == {} for o in observations)


def test_worker_dry_run_is_default_and_writes_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repository, database_url = migrated_repository(tmp_path / "dry.db")
    packet, artifact = write_inputs(tmp_path)
    assert main(cli(packet, artifact, "--database-url", database_url)) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "DRY_RUN"
    assert report["witness_rows"] == 2
    assert report["reference_person_rows"] == 1
    assert report["person_materialization"] is False
    with repository.sessions() as session:
        assert session.scalar(select(func.count()).select_from(FeederObservationRow)) == 0


def test_worker_refuses_unreviewed_packet_and_missing_rights_or_database(
    tmp_path: Path,
) -> None:
    packet, artifact = write_inputs(tmp_path, "REVIEW_REQUIRED")
    with pytest.raises(SystemExit):
        main(cli(packet, artifact))
    packet, artifact = write_inputs(tmp_path)
    with pytest.raises(SystemExit):
        main(["--packet", str(packet), "--artifact", str(artifact)])
    with pytest.raises(SystemExit):
        main(cli(packet, artifact, "--commit"))
    artifact.write_bytes(b"tampered")
    with pytest.raises(SystemExit):
        main(cli(packet, artifact))


def test_worker_commit_writes_observations_only_and_is_idempotent(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repository, database_url = migrated_repository(tmp_path / "commit.db")
    packet, artifact = write_inputs(tmp_path)
    args = cli(packet, artifact, "--database-url", database_url, "--commit")
    assert main(args) == 0
    first = json.loads(capsys.readouterr().out)
    assert first["status"] == "COMMITTED"
    assert first["observations_created"] == 3
    assert main(args) == 0
    second = json.loads(capsys.readouterr().out)
    assert second["observations_created"] == 0
    assert second["observations_unchanged"] == 3

    with repository.sessions() as session:
        rows = list(session.scalars(select(FeederObservationRow)))
        assert len(rows) == 3
        assert {row.feeder for row in rows} == {GUKGAM_WITNESS_FEEDER}
        assert session.scalar(select(func.count()).select_from(PersonRow)) == 0
        assert session.scalar(select(func.count()).select_from(PersonObservationLinkRow)) == 0
        assert session.scalar(select(func.count()).select_from(OrganizationRow)) == 0


def committed_context(
    tmp_path: Path,
) -> tuple[SqlAlchemyRepository, list]:  # type: ignore[type-arg]
    repository, database_url = migrated_repository(tmp_path / "claims.db")
    packet, artifact = write_inputs(tmp_path)
    assert main(cli(packet, artifact, "--database-url", database_url, "--commit")) == 0
    scope = "2026:합성시험위원회:ADOPTED-2026-09-28"
    observations = repository.feeder_observations(GUKGAM_WITNESS_FEEDER, scope)
    return repository, sorted(observations, key=lambda o: o.provider_record_key)


def test_claim_scope_rules_and_no_reason_leak(tmp_path: Path) -> None:
    repository, observations = committed_context(tmp_path)
    committee_org = Organization(name="합성시험위원회")
    institution_org = Organization(name="합성공단")
    first, second, _third = observations
    snapshot, source, policy = _unpack(repository, first)

    claim, evidence = build_gukgam_witness_claim(
        committee_org,
        observation=first,
        snapshot=snapshot,
        source=source,
        policy=policy,
        subject_scope=SUBJECT_SCOPE_COMMITTEE,
    )
    assert claim.person_id is None
    assert claim.qualifiers["witness_name"] == "합성증인 갑"
    assert evidence.excerpt is None
    assert "신청사유" not in json.dumps(claim.model_dump(mode="json"), ensure_ascii=False)

    with pytest.raises(GukgamWitnessClaimError, match="exact committee"):
        build_gukgam_witness_claim(
            institution_org,
            observation=first,
            snapshot=snapshot,
            source=source,
            policy=policy,
            subject_scope=SUBJECT_SCOPE_COMMITTEE,
        )
    # Row 1 does not state a target institution: institution scope fails closed.
    with pytest.raises(GukgamWitnessClaimError, match="state the exact institution"):
        build_gukgam_witness_claim(
            institution_org,
            observation=first,
            snapshot=snapshot,
            source=source,
            policy=policy,
            subject_scope=SUBJECT_SCOPE_TARGET_INSTITUTION,
        )
    snapshot2, source2, policy2 = _unpack(repository, second)
    build_gukgam_witness_claim(
        institution_org,
        observation=second,
        snapshot=snapshot2,
        source=source2,
        policy=policy2,
        subject_scope=SUBJECT_SCOPE_TARGET_INSTITUTION,
    )


def _unpack(repository: SqlAlchemyRepository, observation):  # type: ignore[no-untyped-def]
    _, snapshot, source, policy = repository.feeder_observation_contexts([observation.id])[
        observation.id
    ]
    return snapshot, source, policy


def test_public_route_is_empty_without_published_claims(tmp_path: Path) -> None:
    repository, _ = committed_context(tmp_path)
    insert_organization(repository, "합성시험위원회")
    with TestClient(create_app(repository)) as client:
        payload_ = client.get("/gukgam/2026/witnesses").json()
    assert payload_["items"] == []
    assert payload_["witness_count"] == 0


def test_public_route_projects_published_claims_only(tmp_path: Path) -> None:
    repository, observations = committed_context(tmp_path)
    committee_id = insert_organization(repository, "합성시험위원회")
    institution_id = insert_organization(repository, "합성공단")
    committee = repository.organization(committee_id)
    institution = repository.organization(institution_id)
    assert committee is not None and institution is not None

    first, second, third = observations
    for organization, observation, scope in (
        (committee, first, SUBJECT_SCOPE_COMMITTEE),
        (institution, second, SUBJECT_SCOPE_TARGET_INSTITUTION),
    ):
        snapshot, source, policy = _unpack(repository, observation)
        claim, evidence = build_gukgam_witness_claim(
            organization,
            observation=observation,
            snapshot=snapshot,
            source=source,
            policy=policy,
            subject_scope=scope,
        )
        repository.import_organization_claim(organization, claim, [evidence])
    assert third.provider_record_key.endswith(":3")  # reference person stays unpublished

    with TestClient(create_app(repository)) as client:
        response = client.get("/gukgam/2026/witnesses")
    assert response.status_code == 200
    body = response.json()
    assert body["semantics"] == GUKGAM_PUBLIC_WITNESS_PROJECTION_SEMANTICS
    assert body["coverage"] == GUKGAM_PUBLIC_WITNESS_COVERAGE
    assert body["identity_semantics"] == "SOURCE_LISTED_TEXT_NO_PERSON_LINK"
    assert body["witness_count"] == 2
    assert body["reference_person_count"] == 0
    assert [i["row_number"] for i in body["items"]] == [1, 2]
    assert body["items"][0]["name"] == "합성증인 갑"
    assert body["items"][0]["affiliation_title"] == "합성기관 대표이사"
    assert body["items"][1]["subject_scope"] == "TARGET_INSTITUTION"
    assert body["items"][0]["source_url"].startswith("https://synthetic-test.na.go.kr/")
    limitations = " ".join(body["limitations"])
    assert "absence is not evidence" in limitations
    assert "not a finding of wrongdoing" in limitations
    assert "versioned" in limitations

    serialized = json.dumps(body, ensure_ascii=False)
    assert "합성참고인" not in serialized
    assert "신청사유" not in serialized
    for forbidden in ("person_id", "request_reason", "normalized", "identity_hints"):
        assert forbidden not in serialized

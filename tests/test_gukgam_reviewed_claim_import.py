from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config

from packages.connectors.gukgam_reviewed_packet import parse_reviewed_gukgam_plan_packet
from packages.domain.db import OrganizationRow
from packages.domain.enums import SourceRunStatus
from packages.persistence import SqlAlchemyRepository
from packages.rendering.gukgam_organization_binding_review import gukgam_review_key
from packages.rendering.gukgam_organization_claim import GUKGAM_AUDIT_TARGET_PREDICATE
from packages.verification.gukgam_reviewed_plan_import import (
    GUKGAM_REVIEWED_PLAN_FEEDER,
    ReviewedGukgamArtifactProof,
    build_reviewed_gukgam_plan_capture,
)
from workers.gukgam_reviewed_claim_import import (
    main,
    prepare_reviewed_gukgam_claim_import,
)

FIXTURE = Path("tests/fixtures/gukgam_2026_science_plan_reviewed_packet.json")
ARTIFACT_BYTES = b"%PDF-gukgam-reviewed-claim-import\n"
ATTACHMENT_URL = (
    "https://science.na.go.kr/cmmit/prevew/docsPreview/previewDocs.do"
    "?atchFileId=7938f3a874d5441892124093d19da1df&fileSn=2&viewType=CONTBODY"
)


def migrated_repository(database: Path) -> tuple[SqlAlchemyRepository, str]:
    database_url = f"sqlite:///{database.as_posix()}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")
    return SqlAlchemyRepository(database_url), database_url


def packet_payload() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def insert_organization(repository: SqlAlchemyRepository, name: str) -> UUID:
    organization_id = uuid4()
    timestamp = datetime.now(UTC)
    with repository.sessions() as session:
        session.add(
            OrganizationRow(
                id=str(organization_id),
                name=name,
                valid_from=timestamp,
                valid_to=None,
                recorded_at=timestamp,
                superseded_at=None,
            )
        )
        session.commit()
    return organization_id


def commit_packet(repository: SqlAlchemyRepository, raw: dict) -> str:
    packet = parse_reviewed_gukgam_plan_packet(raw)
    proof = ReviewedGukgamArtifactProof.from_bytes(
        packet,
        attachment_url=ATTACHMENT_URL,
        artifact_bytes=ARTIFACT_BYTES,
    )
    capture = build_reviewed_gukgam_plan_capture(packet, artifact=proof)
    run = repository.start_source_run(
        GUKGAM_REVIEWED_PLAN_FEEDER,
        capture.scope_key,
        metadata=capture.run_metadata,
    )
    observations = capture.observations(run.id)
    repository.commit_source_page(
        run_id=run.id,
        policy=capture.policy,
        source=capture.source,
        snapshot=capture.snapshot,
        observations=observations,
        cursor=capture.cursor,
        checkpoint_metadata=capture.checkpoint_metadata,
    )
    repository.finish_source_run(run.id, SourceRunStatus.SUCCESS)
    return gukgam_review_key(observations[0].provider_record_key, 1)


def test_reviewed_gukgam_claim_dry_run_writes_nothing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository, database_url = migrated_repository(tmp_path / "dry-run.db")
    raw = packet_payload()
    review_key = commit_packet(repository, raw)
    organization_id = insert_organization(
        repository,
        raw["schedule"][0]["audited_targets"][0],
    )
    before_runs = len(repository.source_runs(GUKGAM_REVIEWED_PLAN_FEEDER))
    before_observations = len(
        repository.feeder_observations(
            GUKGAM_REVIEWED_PLAN_FEEDER,
            "2026:과학기술정보방송통신위원회",
        )
    )

    assert main(
        [
            "--database-url",
            database_url,
            "--organization-id",
            str(organization_id),
            "--review-key",
            review_key,
        ]
    ) == 0
    receipt = json.loads(capsys.readouterr().out)

    assert receipt["status"] == "DRY_RUN"
    assert receipt["predicate"] == GUKGAM_AUDIT_TARGET_PREDICATE
    assert receipt["organization_created"] is False
    assert receipt["binding_committed"] is False
    assert receipt["claim_persisted"] is False
    assert receipt["claim_created"] is False
    assert receipt["network_fetch"] is False
    assert repository.claims(organization_id=organization_id) == []
    assert len(repository.source_runs(GUKGAM_REVIEWED_PLAN_FEEDER)) == before_runs
    assert (
        len(
            repository.feeder_observations(
                GUKGAM_REVIEWED_PLAN_FEEDER,
                "2026:과학기술정보방송통신위원회",
            )
        )
        == before_observations
    )


def test_reviewed_gukgam_claim_commit_is_exact_and_retry_reuses(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository, database_url = migrated_repository(tmp_path / "commit.db")
    raw = packet_payload()
    review_key = commit_packet(repository, raw)
    target_name = raw["schedule"][0]["audited_targets"][0]
    organization_id = insert_organization(repository, target_name)

    args = [
        "--database-url",
        database_url,
        "--organization-id",
        str(organization_id),
        "--review-key",
        review_key,
        "--commit",
    ]
    assert main(args) == 0
    first = json.loads(capsys.readouterr().out)
    assert first["status"] == "COMMITTED"
    assert first["claim_persisted"] is True
    assert first["claim_created"] is True

    claims = repository.claims(
        organization_id=organization_id,
        published_only=True,
        current_only=True,
    )
    assert len(claims) == 1
    claim = claims[0]
    assert claim.predicate == GUKGAM_AUDIT_TARGET_PREDICATE
    assert claim.subject == target_name
    assert "피감대상으로 기재되어 있다" in claim.proposition
    assert claim.qualifiers["provider_record_key"] == review_key
    assert claim.qualifiers["event_semantics"] == "OFFICIAL_PLAN_LISTING_NOT_COMPLETED_AUDIT"
    assert claim.qualifiers["audit_date"] == raw["schedule"][0]["audit_date"]
    assert claim.valid_from.date().isoformat() == raw["source"]["published_date"]

    evidence = repository.evidence_for(claim.id)
    assert len(evidence) == 1
    assert evidence[0].excerpt is None
    observation = repository.feeder_observation(evidence[0].feeder_observation_id)
    assert observation is not None
    assert evidence[0].snapshot_id == observation.snapshot_id

    assert main(args) == 0
    second = json.loads(capsys.readouterr().out)
    assert second["status"] == "REUSED"
    assert second["claim_persisted"] is True
    assert second["claim_created"] is False
    assert second["claim_id"] == first["claim_id"]
    assert len(repository.claims(organization_id=organization_id)) == 1
    assert len(repository.evidence_for(claim.id)) == 1


def test_reviewed_gukgam_claim_rejects_wrong_organization(
    tmp_path: Path,
) -> None:
    repository, _ = migrated_repository(tmp_path / "wrong-org.db")
    review_key = commit_packet(repository, packet_payload())
    wrong_id = insert_organization(repository, "다른 기관")

    with pytest.raises(ValueError, match="exact-name candidate"):
        prepare_reviewed_gukgam_claim_import(
            repository,
            organization_id=wrong_id,
            review_key=review_key,
        )


def test_reviewed_gukgam_claim_rejects_multiple_observation_versions(
    tmp_path: Path,
) -> None:
    repository, _ = migrated_repository(tmp_path / "versions.db")
    raw = packet_payload()
    review_key = commit_packet(repository, raw)
    organization_id = insert_organization(
        repository,
        raw["schedule"][0]["audited_targets"][0],
    )

    changed = packet_payload()
    changed["schedule"][0]["venue"] = "변경된 검토 장소"
    commit_packet(repository, changed)

    with pytest.raises(ValueError, match="multiple immutable observation versions"):
        prepare_reviewed_gukgam_claim_import(
            repository,
            organization_id=organization_id,
            review_key=review_key,
        )

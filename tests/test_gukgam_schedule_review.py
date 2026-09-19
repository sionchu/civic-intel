from __future__ import annotations

import json
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from apps.api.main import create_app
from packages.connectors.gukgam_reviewed_packet import parse_reviewed_gukgam_plan_packet
from packages.domain.enums import SourceRunStatus
from packages.persistence import SqlAlchemyRepository
from packages.rendering.gukgam_organization_binding_review import NO_EXACT
from packages.rendering.gukgam_schedule_review import (
    GUKGAM_SCHEDULE_REVIEW_SEMANTICS,
    GukgamScheduleReviewError,
    build_gukgam_schedule_review,
)
from packages.verification.gukgam_reviewed_plan_import import (
    GUKGAM_REVIEWED_PLAN_FEEDER,
    ReviewedGukgamArtifactProof,
    build_reviewed_gukgam_plan_capture,
)

FIXTURE = Path("tests/fixtures/gukgam_2026_science_plan_reviewed_packet.json")
ARTIFACT_BYTES = b"%PDF-review-projection-fixture\n"
ATTACHMENT_URL = (
    "https://science.na.go.kr/cmmit/prevew/docsPreview/previewDocs.do"
    "?atchFileId=7938f3a874d5441892124093d19da1df&fileSn=2&viewType=CONTBODY"
)


def migrated_repository(database: Path) -> SqlAlchemyRepository:
    database_url = f"sqlite:///{database.as_posix()}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")
    return SqlAlchemyRepository(database_url)


def packet_payload() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def commit_packet(repository: SqlAlchemyRepository, raw: dict) -> None:
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
    repository.commit_source_page(
        run_id=run.id,
        policy=capture.policy,
        source=capture.source,
        snapshot=capture.snapshot,
        observations=capture.observations(run.id),
        cursor=capture.cursor,
        checkpoint_metadata=capture.checkpoint_metadata,
    )
    repository.finish_source_run(run.id, SourceRunStatus.SUCCESS)


def current_contexts(repository: SqlAlchemyRepository):
    checkpoint = repository.source_checkpoint(
        GUKGAM_REVIEWED_PLAN_FEEDER,
        "2026:과학기술정보방송통신위원회",
    )
    assert checkpoint is not None
    attachment_hash = checkpoint.metadata["attachment_sha256"]
    observations = repository.feeder_observations(
        GUKGAM_REVIEWED_PLAN_FEEDER,
        checkpoint.scope_key,
    )
    contexts = repository.feeder_observation_contexts(item.id for item in observations)
    current = {}
    for observation in observations:
        context = contexts[observation.id]
        if context[1].content_hash != attachment_hash:
            continue
        prior = current.get(observation.provider_record_key)
        if prior is None or (observation.recorded_at, str(observation.id)) > (
            prior[0].recorded_at,
            str(prior[0].id),
        ):
            current[observation.provider_record_key] = context
    return list(current.values())


def test_review_projection_is_source_scoped_and_not_public_claim_data(
    tmp_path: Path,
) -> None:
    repository = migrated_repository(tmp_path / "review-projection.db")
    commit_packet(repository, packet_payload())

    report = build_gukgam_schedule_review(current_contexts(repository)).to_dict()

    assert report["semantics"] == GUKGAM_SCHEDULE_REVIEW_SEMANTICS
    assert report["committee_count"] == 1
    assert report["schedule_row_count"] == 8
    assert report["audited_target_mentions"] == 96
    committee = report["committees"][0]
    assert committee["committee_name"] == "과학기술정보방송통신위원회"
    assert committee["source"]["url"] == ATTACHMENT_URL
    assert committee["source"]["rights_mark"] == "KOGL_TYPE_1"
    first = committee["schedule_rows"][0]
    assert first["audit_date"] == "2026-10-06"
    assert first["audited_targets"]
    assert "canonical_organization_id" not in first
    assert "claim_id" not in first
    assert "normalized" not in first
    assert "run_id" not in first


def test_review_api_is_gated_and_uses_current_observation_versions(
    tmp_path: Path,
) -> None:
    repository = migrated_repository(tmp_path / "review-api.db")
    original = packet_payload()
    commit_packet(repository, original)

    changed = packet_payload()
    changed["schedule"][0]["venue"] = "국회 본관 검토용 변경"
    commit_packet(repository, changed)

    with TestClient(create_app(repository, enable_review_surface=True)) as client:
        response = client.get("/admin/gukgam/2026/schedule")
        binding_response = client.get(
            "/admin/gukgam/2026/organization-binding-candidates"
        )
    assert response.status_code == 200
    assert binding_response.status_code == 200
    binding = binding_response.json()
    assert binding["organization_universe_count"] == 0
    assert binding["mention_count"] == 96
    assert all(item["match_class"] == NO_EXACT for item in binding["items"])
    assert all(item["candidates"] == [] for item in binding["items"])

    payload = response.json()
    assert payload["schedule_row_count"] == 8
    rows = payload["committees"][0]["schedule_rows"]
    assert len(rows) == 8
    assert rows[0]["venue"] == "국회 본관 검토용 변경"
    assert len({row["provider_record_key"] for row in rows}) == 8

    with TestClient(create_app(repository)) as public_client:
        public_response = public_client.get("/admin/gukgam/2026/schedule")
        public_binding = public_client.get(
            "/admin/gukgam/2026/organization-binding-candidates"
        )
    assert public_response.status_code == 404
    assert public_binding.status_code == 404
    assert public_response.json()["error"]["code"] == "PUBLIC_RECORD_NOT_FOUND"
    assert public_binding.json()["error"]["code"] == "PUBLIC_RECORD_NOT_FOUND"


def test_review_projection_fails_closed_if_fulltext_or_policy_gate_changes(
    tmp_path: Path,
) -> None:
    repository = migrated_repository(tmp_path / "review-fail-closed.db")
    commit_packet(repository, packet_payload())
    context = current_contexts(repository)[0]
    observation, snapshot, source, policy = context

    with pytest.raises(GukgamScheduleReviewError, match="stored fulltext"):
        build_gukgam_schedule_review(
            [(observation, snapshot.model_copy(update={"fulltext": "forbidden"}), source, policy)]
        )

    with pytest.raises(GukgamScheduleReviewError, match="policy was weakened"):
        build_gukgam_schedule_review(
            [(observation, snapshot, source, policy.model_copy(update={"can_fetch": True}))]
        )

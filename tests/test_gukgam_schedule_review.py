from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from apps.api.main import create_app
from packages.connectors.gukgam_reviewed_packet import parse_reviewed_gukgam_plan_packet
from packages.domain.db import OrganizationRow
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


def test_binding_preflight_api_reverifies_exact_candidate_without_writes(
    tmp_path: Path,
) -> None:
    repository = migrated_repository(tmp_path / "binding-preflight-api.db")
    raw = packet_payload()
    commit_packet(repository, raw)

    counts = Counter(
        target
        for row in raw["schedule"]
        for target in row["audited_targets"]
    )
    exact_target = next(target for target, count in counts.items() if count == 1)
    organization_id = insert_organization(repository, exact_target)

    before = {
        "organizations": len(repository.organizations()),
        "claims": len(repository.claims()),
        "runs": len(repository.source_runs(GUKGAM_REVIEWED_PLAN_FEEDER)),
    }
    with TestClient(create_app(repository, enable_review_surface=True)) as client:
        candidates = client.get(
            "/admin/gukgam/2026/organization-binding-candidates"
        ).json()
        candidate = next(
            item for item in candidates["items"] if item["audited_target"] == exact_target
        )
        response = client.get(
            "/admin/gukgam/2026/organization-binding-preflight",
            params={
                "review_key": candidate["review_key"],
                "organization_id": str(organization_id),
            },
        )
        wrong = client.get(
            "/admin/gukgam/2026/organization-binding-preflight",
            params={
                "review_key": candidate["review_key"],
                "organization_id": str(uuid4()),
            },
        )

    assert response.status_code == 200
    receipt = response.json()
    assert receipt["status"] == "DRY_RUN"
    assert receipt["binding_committed"] is False
    assert receipt["claim_publication"] is False
    assert receipt["review_key"] == candidate["review_key"]
    assert receipt["occurrence"]["audited_target"] == exact_target
    assert receipt["organization"] == {
        "organization_id": str(organization_id),
        "name": exact_target,
    }
    assert receipt["provenance"]["url"] == ATTACHMENT_URL
    assert wrong.status_code == 422
    assert wrong.json()["error"]["code"] == "INVALID_INPUT"

    after = {
        "organizations": len(repository.organizations()),
        "claims": len(repository.claims()),
        "runs": len(repository.source_runs(GUKGAM_REVIEWED_PLAN_FEEDER)),
    }
    assert after == before

    with TestClient(create_app(repository)) as public_client:
        public = public_client.get(
            "/admin/gukgam/2026/organization-binding-preflight",
            params={
                "review_key": candidate["review_key"],
                "organization_id": str(organization_id),
            },
        )
    assert public.status_code == 404
    assert public.json()["error"]["code"] == "PUBLIC_RECORD_NOT_FOUND"


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

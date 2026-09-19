from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from packages.connectors.gukgam_reviewed_packet import (
    AUTOMATION_GATE,
    PACKET_SCHEMA,
    parse_reviewed_gukgam_plan_packet,
)
from packages.persistence import SqlAlchemyRepository
from packages.verification.gukgam_reviewed_plan_import import (
    EXACT_ATTACHMENT_RIGHTS,
    GUKGAM_REVIEWED_PLAN_FEEDER,
    GukgamReviewedPlanImportError,
    ReviewedGukgamArtifactProof,
    build_reviewed_gukgam_plan_capture,
    validate_reviewed_gukgam_capture_metadata,
)
from workers.gukgam_reviewed_plan_import import main

ATTACHMENT_URL = (
    "https://test.na.go.kr/cmmit/prevew/docsPreview/previewDocs.do"
    "?atchFileId=attachment-1&fileSn=2&viewType=CONTBODY"
)
ARTIFACT_BYTES = b"%PDF-reviewed-gukgam-fixture\n"


def migrated_repository(database: Path) -> SqlAlchemyRepository:
    database_url = f"sqlite:///{database.as_posix()}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")
    return SqlAlchemyRepository(database_url)


def packet_payload() -> dict:
    return {
        "schema": PACKET_SCHEMA,
        "review_status": "HUMAN_REVIEWED",
        "source": {
            "committee_name": "테스트위원회",
            "ntt_id": "123",
            "detail_url": (
                "https://test.na.go.kr/cmmit/bbs/BCMT2002/view.do"
                "?nttId=123&menuNo=2000030"
            ),
            "title": "2026년도 국정감사계획서",
            "published_date": "2026-09-15",
            "atch_file_id": "attachment-1",
            "file_sn": 2,
            "attachment_filename": "2026년도 국정감사계획서.pdf",
            "rights_mark": "KOGL_TYPE_1",
            "automation_gate": AUTOMATION_GATE,
        },
        "schedule": [
            {
                "ordinal": 1,
                "audit_date": "2026-10-06",
                "time_text": "10:00",
                "venue": "국회",
                "section": "감사일정",
                "audited_targets": ["테스트기관 A", "테스트기관 B"],
                "page_number": 3,
            },
            {
                "ordinal": 2,
                "audit_date": "2026-10-07",
                "time_text": None,
                "venue": "현장",
                "section": "감사일정",
                "audited_targets": ["테스트기관 C"],
                "page_number": 4,
            },
        ],
        "witness_rows_included": False,
    }


def write_inputs(tmp_path: Path) -> tuple[Path, Path]:
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(
        json.dumps(packet_payload(), ensure_ascii=False),
        encoding="utf-8",
    )
    artifact_path = tmp_path / "plan.pdf"
    artifact_path.write_bytes(ARTIFACT_BYTES)
    return packet_path, artifact_path


def test_capture_separates_raw_artifact_hash_from_reviewed_packet_hash() -> None:
    packet = parse_reviewed_gukgam_plan_packet(packet_payload())
    proof = ReviewedGukgamArtifactProof.from_bytes(
        packet,
        attachment_url=ATTACHMENT_URL,
        artifact_bytes=ARTIFACT_BYTES,
    )
    capture = build_reviewed_gukgam_plan_capture(packet, artifact=proof)

    raw_hash = hashlib.sha256(ARTIFACT_BYTES).hexdigest()
    assert capture.snapshot.content_hash == raw_hash
    assert capture.packet_hash == packet.content_hash
    assert capture.packet_hash != raw_hash
    assert capture.run_metadata["reviewed_packet_hash"] == packet.content_hash
    assert "reviewed_packet_hash" not in capture.snapshot.metadata
    assert capture.snapshot.metadata["content_hash_semantics"] == "RAW_ATTACHMENT_SHA256"
    assert capture.snapshot.fulltext is None
    validate_reviewed_gukgam_capture_metadata(capture.snapshot.metadata)


@pytest.mark.parametrize(
    ("attachment_url", "rights_scope", "message"),
    [
        (
            "https://example.com/file?atchFileId=attachment-1&fileSn=2",
            EXACT_ATTACHMENT_RIGHTS,
            "official committee host",
        ),
        (
            "https://test.na.go.kr/file?atchFileId=wrong&fileSn=2",
            EXACT_ATTACHMENT_RIGHTS,
            "atchFileId",
        ),
        (
            ATTACHMENT_URL,
            "PAGE_ONLY_REVIEWED",
            "exact attachment rights review",
        ),
    ],
)
def test_capture_fails_closed_on_inexact_artifact_proof(
    attachment_url: str,
    rights_scope: str,
    message: str,
) -> None:
    packet = parse_reviewed_gukgam_plan_packet(packet_payload())

    with pytest.raises(GukgamReviewedPlanImportError, match=message):
        ReviewedGukgamArtifactProof.from_bytes(
            packet,
            attachment_url=attachment_url,
            artifact_bytes=ARTIFACT_BYTES,
            rights_scope=rights_scope,
        )


def test_empty_metadata_only_packet_cannot_enter_canonical_import() -> None:
    raw = packet_payload()
    raw["schedule"] = []
    packet = parse_reviewed_gukgam_plan_packet(raw)
    proof = ReviewedGukgamArtifactProof.from_bytes(
        packet,
        attachment_url=ATTACHMENT_URL,
        artifact_bytes=ARTIFACT_BYTES,
    )

    with pytest.raises(GukgamReviewedPlanImportError, match="at least one reviewed schedule row"):
        build_reviewed_gukgam_plan_capture(packet, artifact=proof)


def test_worker_dry_run_does_not_require_or_write_database(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    packet_path, artifact_path = write_inputs(tmp_path)

    assert main(
        [
            "--packet",
            str(packet_path),
            "--artifact",
            str(artifact_path),
            "--attachment-url",
            ATTACHMENT_URL,
            "--confirm-exact-attachment-rights",
        ]
    ) == 0

    receipt = json.loads(capsys.readouterr().out)
    assert receipt["status"] == "DRY_RUN"
    assert receipt["schedule_rows"] == 2
    assert receipt["audited_target_mentions"] == 3
    assert receipt["person_materialization"] is False
    assert receipt["organization_materialization"] is False
    assert receipt["claim_publication"] is False


def test_commit_persists_only_exact_source_snapshot_and_observations(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    database = tmp_path / "import.db"
    repository = migrated_repository(database)
    database_url = f"sqlite:///{database.as_posix()}"
    packet_path, artifact_path = write_inputs(tmp_path)
    args = [
        "--packet",
        str(packet_path),
        "--artifact",
        str(artifact_path),
        "--attachment-url",
        ATTACHMENT_URL,
        "--confirm-exact-attachment-rights",
        "--database-url",
        database_url,
        "--commit",
    ]

    assert main(args) == 0
    first = json.loads(capsys.readouterr().out)
    assert first["status"] == "COMMITTED"
    assert first["observations_created"] == 2
    assert first["observations_unchanged"] == 0

    observations = repository.feeder_observations(
        GUKGAM_REVIEWED_PLAN_FEEDER,
        "2026:테스트위원회",
    )
    assert len(observations) == 2
    assert observations[0].normalized["audited_targets"] == [
        "테스트기관 A",
        "테스트기관 B",
    ]
    assert observations[0].identity_hints == {}
    contexts = repository.feeder_observation_contexts(item.id for item in observations)
    assert set(contexts) == {item.id for item in observations}
    for observation, snapshot, source, policy in contexts.values():
        assert observation.snapshot_id == snapshot.id
        assert snapshot.content_hash == hashlib.sha256(ARTIFACT_BYTES).hexdigest()
        assert snapshot.fulltext is None
        assert snapshot.metadata["content_hash_semantics"] == "RAW_ATTACHMENT_SHA256"
        assert "reviewed_packet_hash" not in snapshot.metadata
        assert str(source.url) == ATTACHMENT_URL
        assert policy.can_store_metadata
        assert not policy.can_fetch
        assert not policy.can_store_fulltext
        assert not policy.can_send_to_ai
        assert not policy.can_show_excerpt
        assert not policy.can_commercialize

    run = repository.source_runs(
        GUKGAM_REVIEWED_PLAN_FEEDER,
        "2026:테스트위원회",
    )[0]
    assert run.status.value == "SUCCESS"
    assert run.metadata["reviewed_packet_hash"] == parse_reviewed_gukgam_plan_packet(
        packet_payload()
    ).content_hash
    checkpoint = repository.source_checkpoint(
        GUKGAM_REVIEWED_PLAN_FEEDER,
        "2026:테스트위원회",
    )
    assert checkpoint is not None
    assert checkpoint.metadata["attachment_sha256"] == hashlib.sha256(
        ARTIFACT_BYTES
    ).hexdigest()

    assert repository.people() == []
    assert repository.organizations() == []
    assert repository.claims() == []

    assert main(args) == 0
    second = json.loads(capsys.readouterr().out)
    assert second["observations_created"] == 0
    assert second["observations_unchanged"] == 2
    assert len(
        repository.feeder_observations(
            GUKGAM_REVIEWED_PLAN_FEEDER,
            "2026:테스트위원회",
        )
    ) == 2


def test_worker_requires_explicit_attachment_rights_confirmation(
    tmp_path: Path,
) -> None:
    packet_path, artifact_path = write_inputs(tmp_path)

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "--packet",
                str(packet_path),
                "--artifact",
                str(artifact_path),
                "--attachment-url",
                ATTACHMENT_URL,
            ]
        )

    assert exc_info.value.code == 2

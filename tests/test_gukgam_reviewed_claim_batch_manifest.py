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
from packages.verification.gukgam_reviewed_plan_import import (
    GUKGAM_REVIEWED_PLAN_FEEDER,
    ReviewedGukgamArtifactProof,
    build_reviewed_gukgam_plan_capture,
)
from workers.gukgam_reviewed_claim_batch_manifest import (
    GUKGAM_REVIEWED_CLAIM_BATCH_MANIFEST_SCHEMA,
    GUKGAM_REVIEWED_CLAIM_BATCH_MANIFEST_SEMANTICS,
    main,
    parse_reviewed_gukgam_claim_batch_manifest,
    prepare_reviewed_gukgam_claim_batch_manifest,
)
from workers.gukgam_reviewed_claim_import import main as single_claim_main

FIXTURE = Path("tests/fixtures/gukgam_2026_science_plan_reviewed_packet.json")
ARTIFACT_BYTES = b"%PDF-gukgam-reviewed-claim-batch-manifest\n"
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
    return observations[0].provider_record_key


def manifest_payload(items: list[tuple[str, UUID]]) -> dict[str, object]:
    return {
        "schema": GUKGAM_REVIEWED_CLAIM_BATCH_MANIFEST_SCHEMA,
        "items": [
            {
                "review_key": review_key,
                "organization_id": str(organization_id),
            }
            for review_key, organization_id in items
        ],
    }


def test_batch_manifest_dry_run_is_deterministic_and_writes_nothing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository, database_url = migrated_repository(tmp_path / "batch-dry-run.db")
    raw = packet_payload()
    provider_record_key = commit_packet(repository, raw)
    targets = raw["schedule"][0]["audited_targets"][:2]
    organization_ids = [
        insert_organization(repository, target)
        for target in targets
    ]
    review_keys = [
        gukgam_review_key(provider_record_key, index)
        for index in (1, 2)
    ]

    first_manifest = tmp_path / "manifest-first.json"
    first_manifest.write_text(
        json.dumps(
            manifest_payload(
                list(reversed(list(zip(review_keys, organization_ids, strict=True))))
            ),
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    second_manifest = tmp_path / "manifest-second.json"
    second_manifest.write_text(
        json.dumps(
            manifest_payload(list(zip(review_keys, organization_ids, strict=True))),
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    before_claims = len(repository.claims())
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
            "--manifest",
            str(first_manifest),
        ]
    ) == 0
    first = json.loads(capsys.readouterr().out)

    assert main(
        [
            "--database-url",
            database_url,
            "--manifest",
            str(second_manifest),
        ]
    ) == 0
    second = json.loads(capsys.readouterr().out)

    assert first == second
    assert first["status"] == "DRY_RUN"
    assert first["semantics"] == GUKGAM_REVIEWED_CLAIM_BATCH_MANIFEST_SEMANTICS
    assert first["item_count"] == 2
    assert first["all_preflights_passed"] is True
    assert first["write_performed"] is False
    assert first["batch_commit_available"] is False
    assert first["automatic_candidate_enumeration"] is False
    assert first["network_fetch"] is False
    assert [item["review_key"] for item in first["items"]] == sorted(review_keys)
    assert all(item["claim_persisted"] is False for item in first["items"])
    assert all(item["binding_committed"] is False for item in first["items"])

    assert len(repository.claims()) == before_claims
    assert (
        len(
            repository.feeder_observations(
                GUKGAM_REVIEWED_PLAN_FEEDER,
                "2026:과학기술정보방송통신위원회",
            )
        )
        == before_observations
    )


def test_batch_manifest_rejects_duplicate_review_key() -> None:
    organization_id = uuid4()
    review_key = "row:audited-target:1"
    raw = manifest_payload(
        [
            (review_key, organization_id),
            (review_key, organization_id),
        ]
    )

    with pytest.raises(ValueError, match="duplicate review_key"):
        parse_reviewed_gukgam_claim_batch_manifest(raw)


def test_batch_manifest_rejects_wrong_binding(
    tmp_path: Path,
) -> None:
    repository, _ = migrated_repository(tmp_path / "batch-wrong-binding.db")
    provider_record_key = commit_packet(repository, packet_payload())
    wrong_id = insert_organization(repository, "다른 기관")
    manifest = parse_reviewed_gukgam_claim_batch_manifest(
        manifest_payload(
            [
                (
                    gukgam_review_key(provider_record_key, 1),
                    wrong_id,
                )
            ]
        )
    )

    with pytest.raises(ValueError, match="exact-name candidate"):
        prepare_reviewed_gukgam_claim_batch_manifest(repository, manifest)

    assert repository.claims(organization_id=wrong_id) == []


def test_batch_manifest_rejects_already_published_item(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository, database_url = migrated_repository(tmp_path / "batch-published.db")
    raw = packet_payload()
    provider_record_key = commit_packet(repository, raw)
    target_name = raw["schedule"][0]["audited_targets"][0]
    organization_id = insert_organization(repository, target_name)
    review_key = gukgam_review_key(provider_record_key, 1)

    assert single_claim_main(
        [
            "--database-url",
            database_url,
            "--organization-id",
            str(organization_id),
            "--review-key",
            review_key,
            "--commit",
        ]
    ) == 0
    committed = json.loads(capsys.readouterr().out)
    assert committed["status"] == "COMMITTED"

    manifest = parse_reviewed_gukgam_claim_batch_manifest(
        manifest_payload([(review_key, organization_id)])
    )
    before_claims = len(repository.claims(organization_id=organization_id))

    with pytest.raises(ValueError, match="already-published review_key"):
        prepare_reviewed_gukgam_claim_batch_manifest(repository, manifest)

    assert len(repository.claims(organization_id=organization_id)) == before_claims

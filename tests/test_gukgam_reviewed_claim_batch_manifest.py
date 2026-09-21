from __future__ import annotations

import json
from dataclasses import replace
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
from packages.rendering.gukgam_organization_binding_review import (
    EXACT_ONE,
    build_gukgam_organization_binding_review,
    gukgam_review_key,
)
from packages.rendering.gukgam_schedule_review import load_current_gukgam_schedule_review
from packages.verification.gukgam_reviewed_plan_import import (
    GUKGAM_REVIEWED_PLAN_FEEDER,
    ReviewedGukgamArtifactProof,
    build_reviewed_gukgam_plan_capture,
)
from workers.gukgam_reviewed_claim_batch_commit import (
    GUKGAM_REVIEWED_CLAIM_BATCH_COMMIT_SEMANTICS,
    commit_reviewed_gukgam_claim_batch,
    prepare_reviewed_gukgam_claim_batch_commit,
)
from workers.gukgam_reviewed_claim_batch_commit import (
    main as batch_commit_main,
)
from workers.gukgam_reviewed_claim_batch_manifest import (
    GUKGAM_REVIEWED_CLAIM_BATCH_MANIFEST_SCHEMA,
    GUKGAM_REVIEWED_CLAIM_BATCH_MANIFEST_SEMANTICS,
    main,
    parse_reviewed_gukgam_claim_batch_manifest,
    persist_prepared_reviewed_gukgam_claim_batch,
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


def test_ten_item_manifest_uses_same_preflight_and_atomic_commit_contract(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository, database_url = migrated_repository(tmp_path / "batch-ten-items.db")
    raw = packet_payload()
    provider_record_key = commit_packet(repository, raw)
    targets = raw["schedule"][0]["audited_targets"][:10]
    organization_ids = [insert_organization(repository, target) for target in targets]
    review_keys = [
        gukgam_review_key(provider_record_key, index)
        for index in range(1, 11)
    ]
    manifest = parse_reviewed_gukgam_claim_batch_manifest(
        manifest_payload(list(zip(review_keys, organization_ids, strict=True)))
    )
    manifest_path = tmp_path / "ten-item-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest.canonical_payload(), ensure_ascii=False),
        encoding="utf-8",
    )

    assert main(
        ["--database-url", database_url, "--manifest", str(manifest_path)]
    ) == 0
    dry_run = json.loads(capsys.readouterr().out)
    assert dry_run["item_count"] == 10
    assert dry_run["write_performed"] is False
    assert dry_run["automatic_candidate_enumeration"] is False
    assert repository.claims() == []

    assert batch_commit_main(
        [
            "--database-url",
            database_url,
            "--manifest",
            str(manifest_path),
            "--expected-manifest-sha256",
            manifest.sha256(),
            "--commit",
        ]
    ) == 0
    committed = json.loads(capsys.readouterr().out)
    assert committed["status"] == "COMMITTED"
    assert committed["item_count"] == 10
    assert committed["organizations_created"] == 0
    assert committed["organizations_reused"] == 10
    assert committed["claims_created"] == 10
    assert committed["claims_reused"] == 0
    assert committed["write_performed"] is True
    assert len(repository.claims()) == 10


def test_batch_commit_reuses_one_organization_for_repeated_audit_occurrences(
    tmp_path: Path,
) -> None:
    repository, _database_url = migrated_repository(
        tmp_path / "batch-repeated-organization.db"
    )
    commit_packet(repository, packet_payload())
    organization_id = insert_organization(repository, "과학기술정보통신부")
    review = build_gukgam_organization_binding_review(
        load_current_gukgam_schedule_review(repository),
        repository.organizations(current_only=True),
    )
    repeated = [
        item
        for item in review.items
        if item.audited_target == "과학기술정보통신부"
        and item.match_class == EXACT_ONE
        and len(item.candidates) == 1
        and item.candidates[0].organization_id == organization_id
    ]
    assert len(repeated) == 2

    manifest = parse_reviewed_gukgam_claim_batch_manifest(
        manifest_payload(
            [(item.review_key, organization_id) for item in repeated]
        )
    )
    prepared = prepare_reviewed_gukgam_claim_batch_commit(
        repository,
        manifest,
        expected_manifest_sha256=manifest.sha256(),
    )
    first = commit_reviewed_gukgam_claim_batch(repository, prepared)
    assert first["status"] == "COMMITTED"
    assert first["item_count"] == 2
    assert first["organizations_created"] == 0
    assert first["organizations_reused"] == 1
    assert first["claims_created"] == 2
    assert first["claims_reused"] == 0
    assert len(repository.claims(organization_id=organization_id)) == 2

    retry = prepare_reviewed_gukgam_claim_batch_commit(
        repository,
        manifest,
        expected_manifest_sha256=manifest.sha256(),
    )
    second = commit_reviewed_gukgam_claim_batch(repository, retry)
    assert second["status"] == "REUSED"
    assert second["organizations_created"] == 0
    assert second["organizations_reused"] == 1
    assert second["claims_created"] == 0
    assert second["claims_reused"] == 2
    assert second["write_performed"] is False


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


def prepared_two_item_batch(
    repository: SqlAlchemyRepository,
) -> tuple[list[UUID], object]:
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
    manifest = parse_reviewed_gukgam_claim_batch_manifest(
        manifest_payload(list(zip(review_keys, organization_ids, strict=True)))
    )
    return (
        organization_ids,
        prepare_reviewed_gukgam_claim_batch_manifest(repository, manifest),
    )


def test_prepared_batch_adapter_reuses_existing_organizations_and_exact_retry(
    tmp_path: Path,
) -> None:
    repository, _ = migrated_repository(tmp_path / "batch-adapter.db")
    organization_ids, dry_run = prepared_two_item_batch(repository)

    first = persist_prepared_reviewed_gukgam_claim_batch(repository, dry_run)
    assert first.organizations_created == 0
    assert first.organizations_reused == 2
    assert first.claims_created == 2
    assert first.claims_reused == 0
    assert len(first.claims) == 2
    assert len(repository.organizations(current_only=True)) == 2
    assert sum(
        len(repository.claims(organization_id=organization_id))
        for organization_id in organization_ids
    ) == 2

    second = persist_prepared_reviewed_gukgam_claim_batch(repository, dry_run)
    assert second.organizations_created == 0
    assert second.organizations_reused == 2
    assert second.claims_created == 0
    assert second.claims_reused == 2
    assert [claim.id for claim in second.claims] == [claim.id for claim in first.claims]
    assert sum(
        len(repository.claims(organization_id=organization_id))
        for organization_id in organization_ids
    ) == 2


def test_prepared_batch_adapter_rolls_back_on_late_invalid_evidence(
    tmp_path: Path,
) -> None:
    repository, _ = migrated_repository(tmp_path / "batch-adapter-rollback.db")
    organization_ids, dry_run = prepared_two_item_batch(repository)
    last = dry_run.prepared_items[-1]
    broken_evidence = last.evidence.model_copy(update={"source_id": uuid4()})
    broken_last = replace(last, evidence=broken_evidence)
    broken_dry_run = replace(
        dry_run,
        prepared_items=(*dry_run.prepared_items[:-1], broken_last),
    )

    with pytest.raises(ValueError, match="missing source"):
        persist_prepared_reviewed_gukgam_claim_batch(repository, broken_dry_run)

    assert len(repository.organizations(current_only=True)) == 2
    assert all(
        repository.claims(organization_id=organization_id) == []
        for organization_id in organization_ids
    )


def test_prepared_batch_adapter_rejects_manifest_item_mismatch(
    tmp_path: Path,
) -> None:
    repository, _ = migrated_repository(tmp_path / "batch-adapter-mismatch.db")
    _organization_ids, dry_run = prepared_two_item_batch(repository)
    reversed_dry_run = replace(
        dry_run,
        prepared_items=tuple(reversed(dry_run.prepared_items)),
    )

    with pytest.raises(ValueError, match="do not match the canonical manifest"):
        persist_prepared_reviewed_gukgam_claim_batch(repository, reversed_dry_run)

    assert repository.claims() == []


def write_commit_manifest(
    tmp_path: Path,
    repository: SqlAlchemyRepository,
) -> tuple[Path, object, list[UUID], list[str]]:
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
    manifest = parse_reviewed_gukgam_claim_batch_manifest(
        manifest_payload(list(zip(review_keys, organization_ids, strict=True)))
    )
    manifest_path = tmp_path / "commit-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest.canonical_payload(), ensure_ascii=False),
        encoding="utf-8",
    )
    return manifest_path, manifest, organization_ids, review_keys


def test_batch_commit_cli_requires_explicit_commit(
    tmp_path: Path,
) -> None:
    repository, database_url = migrated_repository(tmp_path / "batch-commit-flag.db")
    manifest_path, manifest, _organization_ids, _review_keys = write_commit_manifest(
        tmp_path,
        repository,
    )

    with pytest.raises(SystemExit) as exc_info:
        batch_commit_main(
            [
                "--database-url",
                database_url,
                "--manifest",
                str(manifest_path),
                "--expected-manifest-sha256",
                manifest.sha256(),
            ]
        )

    assert exc_info.value.code == 2
    assert repository.claims() == []


def test_batch_commit_rejects_manifest_hash_mismatch_before_write(
    tmp_path: Path,
) -> None:
    repository, database_url = migrated_repository(tmp_path / "batch-commit-hash.db")
    manifest_path, _manifest, _organization_ids, _review_keys = write_commit_manifest(
        tmp_path,
        repository,
    )

    with pytest.raises(SystemExit) as exc_info:
        batch_commit_main(
            [
                "--database-url",
                database_url,
                "--manifest",
                str(manifest_path),
                "--expected-manifest-sha256",
                "0" * 64,
                "--commit",
            ]
        )

    assert exc_info.value.code == 2
    assert repository.claims() == []


def test_batch_commit_cli_commits_atomically_and_exact_retry_reuses(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository, database_url = migrated_repository(tmp_path / "batch-commit.db")
    manifest_path, manifest, organization_ids, review_keys = write_commit_manifest(
        tmp_path,
        repository,
    )
    args = [
        "--database-url",
        database_url,
        "--manifest",
        str(manifest_path),
        "--expected-manifest-sha256",
        manifest.sha256(),
        "--commit",
    ]

    assert batch_commit_main(args) == 0
    first = json.loads(capsys.readouterr().out)
    assert first["status"] == "COMMITTED"
    assert first["semantics"] == GUKGAM_REVIEWED_CLAIM_BATCH_COMMIT_SEMANTICS
    assert first["manifest_sha256"] == manifest.sha256()
    assert first["item_count"] == 2
    assert first["organizations_created"] == 0
    assert first["organizations_reused"] == 2
    assert first["claims_created"] == 2
    assert first["claims_reused"] == 0
    assert first["write_performed"] is True
    assert first["automatic_candidate_enumeration"] is False
    assert first["network_fetch"] is False
    assert [item["review_key"] for item in first["items"]] == sorted(review_keys)
    assert all(item["claim_persisted"] is True for item in first["items"])
    assert all(item["organization_created"] is False for item in first["items"])
    assert all("claim_created" not in item for item in first["items"])
    first_claim_ids = [item["claim_id"] for item in first["items"]]

    assert batch_commit_main(args) == 0
    second = json.loads(capsys.readouterr().out)
    assert second["status"] == "REUSED"
    assert second["manifest_sha256"] == first["manifest_sha256"]
    assert second["organizations_created"] == 0
    assert second["organizations_reused"] == 2
    assert second["claims_created"] == 0
    assert second["claims_reused"] == 2
    assert second["write_performed"] is False
    assert [item["claim_id"] for item in second["items"]] == first_claim_ids

    assert len(repository.organizations(current_only=True)) == 2
    assert sum(
        len(repository.claims(organization_id=organization_id))
        for organization_id in organization_ids
    ) == 2


def test_batch_commit_refuses_partially_published_manifest(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository, database_url = migrated_repository(tmp_path / "batch-commit-partial.db")
    manifest_path, manifest, organization_ids, review_keys = write_commit_manifest(
        tmp_path,
        repository,
    )

    assert single_claim_main(
        [
            "--database-url",
            database_url,
            "--organization-id",
            str(organization_ids[0]),
            "--review-key",
            review_keys[0],
            "--commit",
        ]
    ) == 0
    capsys.readouterr()

    with pytest.raises(SystemExit) as exc_info:
        batch_commit_main(
            [
                "--database-url",
                database_url,
                "--manifest",
                str(manifest_path),
                "--expected-manifest-sha256",
                manifest.sha256(),
                "--commit",
            ]
        )

    assert exc_info.value.code == 2
    assert len(repository.claims(organization_id=organization_ids[0])) == 1
    assert repository.claims(organization_id=organization_ids[1]) == []

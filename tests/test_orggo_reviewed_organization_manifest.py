from __future__ import annotations

import hashlib
import json
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config

from packages.domain.contracts import Organization
from packages.persistence import SqlAlchemyRepository
from workers.orggo_reviewed_organization_commit import (
    commit_reviewed_orggo_organizations,
    prepare_reviewed_orggo_organization_commit,
)
from workers.orggo_reviewed_organization_manifest import (
    ORGGO_REVIEWED_ORGANIZATION_MANIFEST_SCHEMA,
    organization_id_for_orggo_code,
    parse_reviewed_orggo_organization_manifest,
    prepare_reviewed_orggo_organization_manifest,
)


def migrated_repository(database: Path) -> SqlAlchemyRepository:
    database_url = f"sqlite:///{database.as_posix()}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")
    return SqlAlchemyRepository(database_url)


def proposal_payload(*, current_count: int = 0) -> dict[str, object]:
    return {
        "semantics": "REVIEW_ONLY_ORGGO_ORGANIZATION_PROPOSAL_V1",
        "status": "REVIEW_ONLY",
        "match_rule": "EXACT_PROVIDER_NAME_TO_GUKGAM_NO_EXACT_LABEL_ONLY",
        "provider_row_count": 63,
        "current_organization_count": current_count,
        "proposal_count": 1,
        "gukgam_occurrence_count": 2,
        "canonical_name_conflict_count": 0,
        "items": [
            {
                "proposal_status": "REVIEW_REQUIRED_NO_WRITE",
                "organization_name": "행정안전부",
                "provider": {
                    "org_code": "1741000",
                    "category": "중앙행정기관",
                    "chart_id": "55",
                    "source_locator": "https://www.org.go.kr/cop/bbs/getInstiChartDetail.do?codeNum=%EC%A4%91%EC%95%99%ED%96%89%EC%A0%95%EA%B8%B0%EA%B4%80&orgCode=1741000&chartId=55",
                },
                "current_exact_canonical_match_count": 0,
                "occurrence_count": 2,
                "gukgam_occurrences": [],
            }
        ],
        "limitations": ["review only"],
    }


def proposal_sha(payload: object) -> str:
    raw = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def manifest_payload(proposal: object) -> dict[str, object]:
    return {
        "schema": ORGGO_REVIEWED_ORGANIZATION_MANIFEST_SCHEMA,
        "proposal_core_sha256": proposal_sha(proposal),
        "items": [
            {
                "organization_name": "행정안전부",
                "category": "중앙행정기관",
                "org_code": "1741000",
                "chart_id": "55",
                "source_locator": "https://www.org.go.kr/cop/bbs/getInstiChartDetail.do?codeNum=%EC%A4%91%EC%95%99%ED%96%89%EC%A0%95%EA%B8%B0%EA%B4%80&orgCode=1741000&chartId=55",
            }
        ],
    }


def test_manifest_preflight_predicts_create_without_writing(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "create.db")
    proposal = proposal_payload()
    manifest = parse_reviewed_orggo_organization_manifest(manifest_payload(proposal))
    dry = prepare_reviewed_orggo_organization_manifest(repository, manifest, proposal)
    payload = dry.to_dict()
    assert payload["status"] == "DRY_RUN"
    assert payload["item_count"] == 1
    assert payload["organizations_to_create"] == 1
    assert payload["organizations_to_reuse"] == 0
    assert payload["write_performed"] is False
    assert payload["automatic_candidate_enumeration"] is False
    assert payload["gukgam_claim_publication"] is False
    assert payload["network_fetch"] is False
    assert repository.organizations() == []
    assert dry.prepared_items[0].organization.id == organization_id_for_orggo_code("1741000")


def test_organization_batch_is_idempotent_and_preflight_reuses(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "reuse.db")
    proposal = proposal_payload()
    manifest = parse_reviewed_orggo_organization_manifest(manifest_payload(proposal))
    prepared = prepare_reviewed_orggo_organization_manifest(repository, manifest, proposal)
    organization = prepared.prepared_items[0].organization

    first = repository.import_organization_batch([organization])
    assert first.organizations_created == 1
    assert first.organizations_reused == 0

    retry = prepare_reviewed_orggo_organization_manifest(repository, manifest, proposal)
    assert retry.prepared_items[0].action == "REUSE"
    assert retry.to_dict()["organizations_to_create"] == 0
    assert retry.to_dict()["organizations_to_reuse"] == 1

    second = repository.import_organization_batch([organization])
    assert second.organizations_created == 0
    assert second.organizations_reused == 1


def test_unrelated_current_organization_drift_fails_closed(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "drift.db")
    repository.import_organization_batch([Organization(id=uuid4(), name="다른기관")])
    proposal = proposal_payload()
    manifest = parse_reviewed_orggo_organization_manifest(manifest_payload(proposal))
    with pytest.raises(ValueError, match="changed outside"):
        prepare_reviewed_orggo_organization_manifest(repository, manifest, proposal)


def test_same_name_with_another_id_fails_closed(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "name-conflict.db")
    repository.import_organization_batch([Organization(id=uuid4(), name="행정안전부")])
    proposal = proposal_payload()
    manifest = parse_reviewed_orggo_organization_manifest(manifest_payload(proposal))
    with pytest.raises(ValueError, match="exact name with another ID"):
        prepare_reviewed_orggo_organization_manifest(repository, manifest, proposal)


def test_deterministic_id_collision_with_another_name_fails_closed(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "id-conflict.db")
    repository.import_organization_batch(
        [
            Organization(
                id=organization_id_for_orggo_code("1741000"),
                name="다른기관",
            )
        ]
    )
    proposal = proposal_payload()
    manifest = parse_reviewed_orggo_organization_manifest(manifest_payload(proposal))
    with pytest.raises(ValueError, match="collides with another name"):
        prepare_reviewed_orggo_organization_manifest(repository, manifest, proposal)


def test_proposal_sha_and_exact_provider_fields_are_binding(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "binding.db")
    proposal = proposal_payload()
    raw_manifest = manifest_payload(proposal)
    bad_sha = dict(raw_manifest)
    bad_sha["proposal_core_sha256"] = "0" * 64
    manifest = parse_reviewed_orggo_organization_manifest(bad_sha)
    with pytest.raises(ValueError, match="SHA-256"):
        prepare_reviewed_orggo_organization_manifest(repository, manifest, proposal)

    changed = manifest_payload(proposal)
    changed_items = list(changed["items"])
    changed_items[0] = {**changed_items[0], "chart_id": "999"}
    changed["items"] = changed_items
    manifest = parse_reviewed_orggo_organization_manifest(changed)
    with pytest.raises(ValueError, match="differs from reviewed proposal"):
        prepare_reviewed_orggo_organization_manifest(repository, manifest, proposal)


def test_commit_requires_exact_manifest_sha_and_is_idempotent(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "commit.db")
    proposal = proposal_payload()
    manifest = parse_reviewed_orggo_organization_manifest(manifest_payload(proposal))

    with pytest.raises(ValueError, match="operator confirmation"):
        prepare_reviewed_orggo_organization_commit(
            repository,
            manifest,
            proposal,
            expected_manifest_sha256="0" * 64,
        )

    prepared = prepare_reviewed_orggo_organization_commit(
        repository,
        manifest,
        proposal,
        expected_manifest_sha256=manifest.sha256(),
    )
    receipt = commit_reviewed_orggo_organizations(repository, prepared)
    assert receipt["status"] == "COMMITTED"
    assert receipt["item_count"] == 1
    assert receipt["organizations_created"] == 1
    assert receipt["organizations_reused"] == 0
    assert receipt["write_performed"] is True
    assert receipt["automatic_candidate_enumeration"] is False
    assert receipt["gukgam_claim_publication"] is False
    assert receipt["network_fetch"] is False
    assert len(repository.organizations()) == 1
    assert repository.claims() == []

    retry = prepare_reviewed_orggo_organization_commit(
        repository,
        manifest,
        proposal,
        expected_manifest_sha256=manifest.sha256(),
    )
    retry_receipt = commit_reviewed_orggo_organizations(repository, retry)
    assert retry_receipt["status"] == "REUSED"
    assert retry_receipt["organizations_created"] == 0
    assert retry_receipt["organizations_reused"] == 1
    assert retry_receipt["write_performed"] is False
    assert len(repository.organizations()) == 1
    assert repository.claims() == []


def proposal_payload_two(*, current_count: int = 0) -> dict[str, object]:
    payload = proposal_payload(current_count=current_count)
    items = list(payload["items"])
    items.append(
        {
            "proposal_status": "REVIEW_REQUIRED_NO_WRITE",
            "organization_name": "재정경제부",
            "provider": {
                "org_code": "1053000",
                "category": "중앙행정기관",
                "chart_id": "63",
                "source_locator": "https://www.org.go.kr/cop/bbs/getInstiChartDetail.do?codeNum=%EC%A4%91%EC%95%99%ED%96%89%EC%A0%95%EA%B8%B0%EA%B4%80&orgCode=1053000&chartId=63",
            },
            "current_exact_canonical_match_count": 0,
            "occurrence_count": 2,
            "gukgam_occurrences": [],
        }
    )
    payload["items"] = items
    payload["proposal_count"] = 2
    payload["gukgam_occurrence_count"] = 4
    return payload


def manifest_payload_two(proposal: object) -> dict[str, object]:
    return {
        "schema": ORGGO_REVIEWED_ORGANIZATION_MANIFEST_SCHEMA,
        "proposal_core_sha256": proposal_sha(proposal),
        "items": [
            {
                "organization_name": "행정안전부",
                "category": "중앙행정기관",
                "org_code": "1741000",
                "chart_id": "55",
                "source_locator": "https://www.org.go.kr/cop/bbs/getInstiChartDetail.do?codeNum=%EC%A4%91%EC%95%99%ED%96%89%EC%A0%95%EA%B8%B0%EA%B4%80&orgCode=1741000&chartId=55",
            },
            {
                "organization_name": "재정경제부",
                "category": "중앙행정기관",
                "org_code": "1053000",
                "chart_id": "63",
                "source_locator": "https://www.org.go.kr/cop/bbs/getInstiChartDetail.do?codeNum=%EC%A4%91%EC%95%99%ED%96%89%EC%A0%95%EA%B8%B0%EA%B4%80&orgCode=1053000&chartId=63",
            },
        ],
    }


def test_commit_refuses_partially_materialized_manifest(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "partial.db")
    proposal = proposal_payload_two()
    manifest = parse_reviewed_orggo_organization_manifest(manifest_payload_two(proposal))

    repository.import_organization_batch(
        [
            Organization(
                id=organization_id_for_orggo_code("1741000"),
                name="행정안전부",
            )
        ]
    )

    with pytest.raises(ValueError, match="partially materialized"):
        prepare_reviewed_orggo_organization_commit(
            repository,
            manifest,
            proposal,
            expected_manifest_sha256=manifest.sha256(),
        )
    assert len(repository.organizations()) == 1
    assert repository.claims() == []

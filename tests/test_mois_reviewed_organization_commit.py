from __future__ import annotations

import copy
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config

from packages.domain.contracts import Organization
from packages.persistence import SqlAlchemyRepository
from packages.rendering.mois_organization_proposal import (
    MOIS_FEEDER,
    MOIS_ORGANIZATION_PROPOSAL_SEMANTICS,
    MOIS_SCOPE_KEY,
)
from workers.mois_reviewed_organization_commit import (
    manifest_from_proposal,
    organization_id_for_mois_code,
    prepare,
    receipt,
)

OBSERVATION_ID = "563d7f7c-cd45-4cc5-a034-9bada7911132"


def migrated_repository(database: Path) -> SqlAlchemyRepository:
    url = f"sqlite:///{database.as_posix()}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    return SqlAlchemyRepository(url)


def proposal(current_count: int = 0) -> dict[str, object]:
    return {
        "semantics": MOIS_ORGANIZATION_PROPOSAL_SEMANTICS,
        "status": "REVIEW_ONLY",
        "canonical_name_conflict_count": 0,
        "current_organization_count": current_count,
        "items": [
            {
                "organization_name": "(재)한국장애인문화예술원",
                "proposal_status": "REVIEW_REQUIRED_NO_WRITE",
                "current_exact_canonical_match_count": 0,
                "provider": {
                    "org_code": "B553630",
                    "observation_id": OBSERVATION_ID,
                    "full_name": "(재)한국장애인문화예술원",
                },
            }
        ],
    }


def observation(**overrides: object) -> SimpleNamespace:
    values = {
        "feeder": MOIS_FEEDER,
        "scope_key": MOIS_SCOPE_KEY,
        "provider_record_key": "B553630",
        "normalized": {"full_name": "(재)한국장애인문화예술원"},
    }
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.fixture
def repository(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SqlAlchemyRepository:
    repo = migrated_repository(tmp_path / "mois.db")
    monkeypatch.setattr(repo, "feeder_observation", lambda _id: observation())
    return repo


def test_reviewed_mois_manifest_creates_then_reuses_derived_organization(repository):
    raw = proposal()
    manifest = manifest_from_proposal(raw)
    prepared = prepare(repository, manifest, raw, expected_manifest_sha256=manifest.sha256())
    assert [entry.action for entry in prepared] == ["CREATE"]
    expected_id = organization_id_for_mois_code("B553630")
    assert prepared[0].organization.id == expected_id
    assert expected_id != UUID(int=0) and "B553630" not in str(expected_id)

    batch = repository.import_organization_batch([entry.organization for entry in prepared])
    result = receipt(
        manifest, prepared, created=batch.organizations_created, reused=0, write_performed=True
    )
    assert result["status"] == "COMMITTED"
    assert result["gukgam_claim_publication"] is False
    again = prepare(repository, manifest, raw, expected_manifest_sha256=manifest.sha256())
    assert [entry.action for entry in again] == ["REUSE"]


def test_reviewed_mois_manifest_fails_closed(repository, monkeypatch):
    raw = proposal()
    manifest = manifest_from_proposal(raw)
    with pytest.raises(ValueError, match="operator confirmation"):
        prepare(repository, manifest, raw, expected_manifest_sha256="0" * 64)

    tampered = copy.deepcopy(raw)
    tampered["items"][0]["current_exact_canonical_match_count"] = 1
    with pytest.raises(ValueError, match="SHA-256 does not match manifest"):
        prepare(repository, manifest, tampered, expected_manifest_sha256=manifest.sha256())

    monkeypatch.setattr(
        repository, "feeder_observation", lambda _id: observation(normalized={"full_name": "다른 이름"})
    )
    with pytest.raises(ValueError, match="no longer supports"):
        prepare(repository, manifest, raw, expected_manifest_sha256=manifest.sha256())


def test_reviewed_mois_manifest_refuses_existing_exact_name(repository):
    repository.import_organization_batch(
        [Organization(id=UUID("11111111-1111-5111-8111-111111111111"), name="(재)한국장애인문화예술원")]
    )
    raw = proposal(current_count=1)
    manifest = manifest_from_proposal(raw)
    with pytest.raises(ValueError, match="already uses this exact name"):
        prepare(repository, manifest, raw, expected_manifest_sha256=manifest.sha256())

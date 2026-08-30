from datetime import date
from pathlib import Path
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from apps.api.main import create_app
from packages.domain.contracts import (
    Claim,
    ClaimEvidence,
    Person,
    Source,
    SourcePolicy,
    SourceSnapshot,
)
from packages.domain.enums import (
    CrossLaneIdentityEvidenceType,
    EpistemicStatus,
    EvidenceStance,
    IdentityStatus,
    PublicationStatus,
    SourceCollectionMode,
)
from packages.persistence import SqlAlchemyRepository
from packages.verification.cross_lane_identity import CrossLaneIdentityEvidence
from packages.verification.identity import IdentityCandidate
from packages.verification.person_onboarding import ReviewedPersonBundle, ReviewedPersonImportError
from packages.verification.profile_target import (
    ProfileTargetLink,
    ProfileTargetObservation,
    build_profile_research_target,
)

PERSON_ID = UUID("00000000-0000-0000-0000-000000009001")
POLICY_ID = UUID("10000000-0000-0000-0000-000000009001")
SOURCE_ID = UUID("20000000-0000-0000-0000-000000009001")
SNAPSHOT_ID = UUID("21000000-0000-0000-0000-000000009001")
CLAIM_ID = UUID("30000000-0000-0000-0000-000000009001")
EVIDENCE_ID = UUID("40000000-0000-0000-0000-000000009001")


def migrated_repository(database: Path) -> SqlAlchemyRepository:
    database_url = f"sqlite:///{database.as_posix()}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")
    return SqlAlchemyRepository(database_url)


def profile_target(name: str = "김온보딩"):
    primary = ProfileTargetObservation(
        lane="CORPORATE_OFFICIAL_PROFILE",
        candidate=IdentityCandidate(
            canonical_name=name,
            birth_date=date(1980, 1, 2),
            office="AI센터장",
            organization="테스트테크",
        ),
        source_refs=("company-profile-kim",),
        discovery_reasons=("PRIVATE_SECTOR_SENIOR_TALENT",),
    )
    public_role = ProfileTargetObservation(
        lane="PRESIDENTIAL_PERSONNEL",
        candidate=IdentityCandidate(
            canonical_name=name,
            birth_date=date(1980, 1, 2),
            office="AI위원",
            organization="테스트위원회",
        ),
        source_refs=("official-personnel-kim",),
        discovery_reasons=("PUBLIC_APPOINTMENT",),
    )
    bridge = (
        CrossLaneIdentityEvidence(
            evidence_type=CrossLaneIdentityEvidenceType.EXACT_BIRTH_DATE,
            source_ref="official-biography-kim",
        ),
    )
    return build_profile_research_target(
        primary,
        (ProfileTargetLink(public_role, bridge),),
    )


def reviewed_bundle(
    *,
    person_id: UUID = PERSON_ID,
    person_name: str = "김온보딩",
    include_evidence: bool = True,
    source_policy_id: UUID = POLICY_ID,
) -> ReviewedPersonBundle:
    person = Person(
        id=person_id,
        canonical_name=person_name,
        birth_date=date(1980, 1, 2),
        identity_status=IdentityStatus.RESOLVED,
    )
    policy = SourcePolicy(
        id=POLICY_ID,
        domain="example.gov",
        source_class="reviewed_official_fixture",
        collection_mode=SourceCollectionMode.DISCOVERY_ONLY,
        can_fetch=False,
        can_store_metadata=True,
        can_store_fulltext=False,
        can_send_to_ai=False,
        can_show_excerpt=True,
        can_commercialize=False,
    )
    source = Source(
        id=SOURCE_ID,
        url="https://example.gov/personnel/kim-onboarding",
        title="Reviewed official personnel fixture",
        publisher="Example Government",
        policy_id=source_policy_id,
    )
    snapshot = SourceSnapshot(
        id=SNAPSHOT_ID,
        source_id=SOURCE_ID,
        content_hash="reviewed-person-kim-v1",
        metadata={"capture": "manual_review"},
        fulltext=None,
    )
    claim = Claim(
        id=CLAIM_ID,
        person_id=person_id,
        proposition="김온보딩은 2026년 8월 30일 테스트위원회 위원으로 임명됐다.",
        subject="김온보딩",
        predicate="APPOINTED_AS",
        object_text="테스트위원회 위원",
        qualifiers={"date": "2026-08-30"},
        epistemic_status=EpistemicStatus.FACT,
        publication_status=PublicationStatus.PUBLISHED,
        asserted_as_true=True,
    )
    evidence = (
        ClaimEvidence(
            id=EVIDENCE_ID,
            claim_id=CLAIM_ID,
            source_id=SOURCE_ID,
            snapshot_id=SNAPSHOT_ID,
            stance=EvidenceStance.SUPPORT,
            excerpt=None,
        ),
    ) if include_evidence else ()
    return ReviewedPersonBundle(
        person=person,
        profile_target=profile_target(),
        policies=(policy,),
        sources=(source,),
        snapshots=(snapshot,),
        claims=(claim,),
        evidence=evidence,
    )


def test_reviewed_bundle_imports_new_person_into_existing_profile_api(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "reviewed.db")
    imported = repository.import_reviewed_person(reviewed_bundle())

    assert imported.id == PERSON_ID
    assert repository.person(PERSON_ID) is not None
    assert len(repository.people()) == 1

    with TestClient(create_app(repository)) as client:
        payload = client.get(f"/people/{PERSON_ID}").json()

    assert payload["canonical_name"] == "김온보딩"
    assert payload["claims"][0]["epistemic_status"] == "FACT"
    sections = {item["id"]: item for item in payload["profile"]["sections"]}
    assert sections["summary"]["entries"][0]["details"]["predicate"] == "APPOINTED_AS"
    assert sections["summary"]["entries"][0]["source_ids"] == [str(SOURCE_ID)]


def test_person_name_must_match_resolved_profile_target() -> None:
    with pytest.raises(ReviewedPersonImportError, match="canonical name"):
        reviewed_bundle(person_name="다른이름")


def test_existing_person_id_collision_fails_without_mutation(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "collision.db")
    repository.import_reviewed_person(reviewed_bundle())
    before = len(repository.people())

    with pytest.raises(ReviewedPersonImportError, match="already exists"):
        repository.import_reviewed_person(reviewed_bundle())

    assert len(repository.people()) == before


def test_broken_source_policy_reference_fails_and_rolls_back(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "missing-policy.db")
    bad_policy_id = UUID("10000000-0000-0000-0000-999999999999")

    with pytest.raises(ReviewedPersonImportError, match="missing SourcePolicy"):
        repository.import_reviewed_person(reviewed_bundle(source_policy_id=bad_policy_id))

    assert repository.people() == []
    assert repository.claims() == []


def test_unsupported_published_fact_fails_and_rolls_back(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "unsupported-fact.db")

    with pytest.raises(ReviewedPersonImportError, match="fact_requires_support"):
        repository.import_reviewed_person(reviewed_bundle(include_evidence=False))

    assert repository.people() == []
    assert repository.claims() == []

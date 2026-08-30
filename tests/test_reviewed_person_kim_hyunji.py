import json
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from apps.api.main import create_app
from apps.api.repository import SqlAlchemyRepository
from packages.domain.contracts import (
    Claim,
    ClaimEvidence,
    Person,
    Source,
    SourcePolicy,
    SourceSnapshot,
)
from packages.domain.enums import EvidenceStance, EpistemicStatus
from packages.verification.identity import IdentityCandidate
from packages.verification.person_onboarding import ReviewedPersonBundle
from packages.verification.profile_target import ProfileTargetObservation, build_profile_research_target

FIXTURE = Path(__file__).parent / "fixtures" / "reviewed_person_kim_hyunji_001.json"
PERSON_ID = "00000000-0000-0000-0000-000000009201"
OFFICIAL_ROLE_SOURCE = "20000000-0000-0000-0000-000000009201"
CONTROVERSY_SOURCE = "20000000-0000-0000-0000-000000009202"


def migrated_repository(database: Path) -> SqlAlchemyRepository:
    database_url = f"sqlite:///{database.as_posix()}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")
    return SqlAlchemyRepository(database_url)


def load_bundle() -> ReviewedPersonBundle:
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    target_raw = raw["profile_target"]["primary"]
    candidate_raw = target_raw["candidate"]
    candidate = IdentityCandidate(
        canonical_name=candidate_raw["canonical_name"],
        aliases=tuple(candidate_raw.get("aliases", [])),
        birth_date=None,
        office=candidate_raw.get("office"),
        organization=candidate_raw.get("organization"),
        career_anchors=tuple(candidate_raw.get("career_anchors", [])),
    )
    target = build_profile_research_target(
        ProfileTargetObservation(
            lane=target_raw["lane"],
            candidate=candidate,
            source_refs=tuple(target_raw["source_refs"]),
            discovery_reasons=tuple(target_raw.get("discovery_reasons", [])),
            appointment_target_slugs=tuple(target_raw.get("appointment_target_slugs", [])),
        )
    )
    return ReviewedPersonBundle(
        person=Person.model_validate(raw["person"]),
        profile_target=target,
        policies=tuple(SourcePolicy.model_validate(item) for item in raw["policies"]),
        sources=tuple(Source.model_validate(item) for item in raw["sources"]),
        snapshots=tuple(SourceSnapshot.model_validate(item) for item in raw["snapshots"]),
        claims=tuple(Claim.model_validate(item) for item in raw["claims"]),
        evidence=tuple(ClaimEvidence.model_validate(item) for item in raw["evidence"]),
    )


def test_bundle_separates_official_role_allegation_and_response() -> None:
    bundle = load_bundle()
    claims = {claim.predicate: claim for claim in bundle.claims}
    evidence = {item.claim_id: item for item in bundle.evidence}

    role = claims["HELD_ROLE"]
    allegation = claims["ALLEGATION"]
    response = claims["RESPONSE_TO_ALLEGATION"]

    assert bundle.person.canonical_name == "김현지"
    assert bundle.person.birth_date is None
    assert role.epistemic_status == EpistemicStatus.FACT
    assert role.asserted_as_true is True
    assert allegation.epistemic_status == EpistemicStatus.CLAIM
    assert allegation.asserted_as_true is False
    assert allegation.qualifiers["truth_status"] == "UNRESOLVED"
    assert evidence[allegation.id].stance == EvidenceStance.NEUTRAL
    assert response.epistemic_status == EpistemicStatus.FACT
    assert response.asserted_as_true is True
    assert evidence[response.id].stance == EvidenceStance.SUPPORT


def test_reviewed_kim_hyunji_bundle_imports_as_neutral_controversy_profile(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "kim-hyunji.db")
    repository.import_reviewed_person(load_bundle())

    with TestClient(create_app(repository)) as client:
        payload = client.get(f"/people/{PERSON_ID}").json()

    assert payload["canonical_name"] == "김현지"
    raw_claims = {item["predicate"]: item for item in payload["claims"]}
    assert raw_claims["ALLEGATION"]["epistemic_status"] == "CLAIM"
    assert raw_claims["ALLEGATION"]["asserted_as_true"] is False
    assert raw_claims["ALLEGATION"]["evidence"][0]["stance"] == "NEUTRAL"
    assert raw_claims["RESPONSE_TO_ALLEGATION"]["epistemic_status"] == "FACT"
    assert raw_claims["RESPONSE_TO_ALLEGATION"]["evidence"][0]["stance"] == "SUPPORT"

    sections = {item["id"]: item for item in payload["profile"]["sections"]}
    assert sections["career_timeline"]["status"] == "AVAILABLE"
    assert sections["career_timeline"]["entries"][0]["details"]["predicate"] == "HELD_ROLE"
    assert sections["career_timeline"]["entries"][0]["source_ids"] == [OFFICIAL_ROLE_SOURCE]
    assert sections["current_power_tasks"]["status"] == "UNKNOWN"

    controversy = sections["controversies"]
    assert controversy["status"] == "PARTIAL"
    assert [item["details"]["predicate"] for item in controversy["entries"]] == [
        "ALLEGATION",
        "RESPONSE_TO_ALLEGATION",
    ]
    assert [item["epistemic_status"] for item in controversy["entries"]] == ["CLAIM", "FACT"]
    assert all(item["source_ids"] == [CONTROVERSY_SOURCE] for item in controversy["entries"])
    assert controversy["entries"][0]["details"]["asserted_as_true"] is False
    assert controversy["entries"][1]["details"]["asserted_as_true"] is True


def test_profile_does_not_turn_competing_statements_into_truth_verdict() -> None:
    repository = migrated_repository(Path("/tmp/civic-intel-kim-hyunji-neutral.db"))
    try:
        repository.import_reviewed_person(load_bundle())
        with TestClient(create_app(repository)) as client:
            payload = client.get(f"/people/{PERSON_ID}").json()
        rendered = json.dumps(payload["profile"], ensure_ascii=False).casefold()
        assert "가짜뉴스" not in rendered
        assert "debunked" not in rendered
        assert "팩트체크 결과 거짓" not in rendered
        assert "faction" not in rendered
        assert "loyalty" not in rendered
        assert "influence_score" not in rendered
    finally:
        repository.engine.dispose()
        database = Path("/tmp/civic-intel-kim-hyunji-neutral.db")
        if database.exists():
            database.unlink()


def test_source_policies_and_snapshots_remain_metadata_only() -> None:
    bundle = load_bundle()

    assert all(policy.can_store_metadata for policy in bundle.policies)
    assert all(not policy.can_store_fulltext for policy in bundle.policies)
    assert all(not policy.can_send_to_ai for policy in bundle.policies)
    assert all(not policy.can_commercialize for policy in bundle.policies)
    assert all(snapshot.fulltext is None for snapshot in bundle.snapshots)

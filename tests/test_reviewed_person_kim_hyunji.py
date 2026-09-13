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
from packages.domain.enums import EpistemicStatus, EvidenceStance
from packages.verification.identity import IdentityCandidate
from packages.verification.person_onboarding import ReviewedPersonBundle
from packages.verification.profile_target import (
    ProfileTargetObservation,
    build_profile_research_target,
)

FIXTURE = Path(__file__).parent / "fixtures" / "reviewed_person_kim_hyunji_001.json"
PERSON_ID = "00000000-0000-0000-0000-000000009201"
OFFICIAL_ROLE_SOURCE = "20000000-0000-0000-0000-000000009201"
CONTROVERSY_SOURCE = "20000000-0000-0000-0000-000000009202"
ASSEMBLY_AIDE_SOURCE = "20000000-0000-0000-0000-000000009203"
PRESIDENTIAL_TRANSFER_SOURCE = "20000000-0000-0000-0000-000000009204"


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


def test_bundle_separates_career_facts_allegation_and_response() -> None:
    bundle = load_bundle()
    evidence = {item.claim_id: item for item in bundle.evidence}
    current_role = next(
        claim
        for claim in bundle.claims
        if claim.predicate == "HELD_ROLE" and claim.object_text == "대통령비서실 제1부속실장"
    )
    allegation = next(claim for claim in bundle.claims if claim.predicate == "ALLEGATION")
    response = next(
        claim for claim in bundle.claims if claim.predicate == "RESPONSE_TO_ALLEGATION"
    )
    career_facts = [
        claim
        for claim in bundle.claims
        if claim.id
        in {
            next(item.id for item in bundle.claims if item.object_text == "이재명 국회의원 보좌관"),
            next(item.id for item in bundle.claims if item.object_text == "대통령실 총무비서관"),
            next(
                item.id
                for item in bundle.claims
                if item.predicate == "APPOINTED_AS"
                and item.object_text == "대통령비서실 제1부속실장"
            ),
        }
    ]

    assert bundle.person.canonical_name == "김현지"
    assert bundle.person.birth_date is None
    assert current_role.epistemic_status == EpistemicStatus.FACT
    assert current_role.asserted_as_true is True
    assert all(item.epistemic_status == EpistemicStatus.FACT for item in career_facts)
    assert allegation.epistemic_status == EpistemicStatus.CLAIM
    assert allegation.asserted_as_true is False
    assert allegation.qualifiers["truth_status"] == "UNRESOLVED"
    assert evidence[allegation.id].stance == EvidenceStance.NEUTRAL
    assert response.epistemic_status == EpistemicStatus.FACT
    assert response.asserted_as_true is True
    assert evidence[response.id].stance == EvidenceStance.SUPPORT


def test_reviewed_kim_hyunji_bundle_imports_with_attributable_career_timeline(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "kim-hyunji.db")
    repository.import_reviewed_person(load_bundle())

    with TestClient(create_app(repository)) as client:
        payload = client.get(f"/people/{PERSON_ID}").json()

    assert payload["canonical_name"] == "김현지"
    raw_allegation = next(item for item in payload["claims"] if item["predicate"] == "ALLEGATION")
    raw_response = next(
        item for item in payload["claims"] if item["predicate"] == "RESPONSE_TO_ALLEGATION"
    )
    assert raw_allegation["epistemic_status"] == "CLAIM"
    assert raw_allegation["asserted_as_true"] is False
    assert raw_allegation["evidence"][0]["stance"] == "NEUTRAL"
    assert raw_response["epistemic_status"] == "FACT"
    assert raw_response["evidence"][0]["stance"] == "SUPPORT"

    sections = {item["id"]: item for item in payload["profile"]["sections"]}
    timeline = sections["career_timeline"]
    assert timeline["status"] == "AVAILABLE"
    assert [entry["date"] for entry in timeline["entries"]] == [
        "2022-06-22",
        "2025-09-29",
        "2025-09-29",
        "2026-08-31",
    ]
    assert [entry["details"]["predicate"] for entry in timeline["entries"]] == [
        "HELD_ROLE",
        "HELD_ROLE",
        "APPOINTED_AS",
        "HELD_ROLE",
    ]
    assert [entry["source_ids"] for entry in timeline["entries"]] == [
        [ASSEMBLY_AIDE_SOURCE],
        [PRESIDENTIAL_TRANSFER_SOURCE],
        [PRESIDENTIAL_TRANSFER_SOURCE],
        [OFFICIAL_ROLE_SOURCE],
    ]
    assert sections["current_power_tasks"]["status"] == "UNKNOWN"

    controversy = sections["controversies"]
    assert controversy["status"] == "PARTIAL"
    assert [item["details"]["predicate"] for item in controversy["entries"]] == [
        "ALLEGATION",
        "RESPONSE_TO_ALLEGATION",
    ]
    assert [item["epistemic_status"] for item in controversy["entries"]] == ["CLAIM", "FACT"]
    assert all(item["source_ids"] == [CONTROVERSY_SOURCE] for item in controversy["entries"])


def test_career_enrichment_does_not_infer_transfer_motive_or_older_roles(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "kim-hyunji-career.db")
    repository.import_reviewed_person(load_bundle())

    with TestClient(create_app(repository)) as client:
        payload = client.get(f"/people/{PERSON_ID}").json()

    rendered = json.dumps(payload["profile"], ensure_ascii=False).casefold()
    assert "국감 회피" not in rendered
    assert "성남참여자치시민연대" not in rendered
    assert "경기도청 비서관" not in rendered
    assert "가짜뉴스" not in rendered
    assert "debunked" not in rendered
    assert "faction" not in rendered
    assert "loyalty" not in rendered
    assert "influence_score" not in rendered


def test_source_policies_and_snapshots_remain_metadata_only() -> None:
    bundle = load_bundle()

    assert all(policy.can_store_metadata for policy in bundle.policies)
    assert all(not policy.can_store_fulltext for policy in bundle.policies)
    assert all(not policy.can_send_to_ai for policy in bundle.policies)
    assert all(not policy.can_commercialize for policy in bundle.policies)
    assert all(snapshot.fulltext is None for snapshot in bundle.snapshots)

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
from packages.verification.identity import IdentityCandidate
from packages.verification.person_onboarding import ReviewedPersonBundle
from packages.verification.profile_target import ProfileTargetObservation, build_profile_research_target

FIXTURE = Path(__file__).parent / "fixtures" / "reviewed_person_im_munyoung_001.json"
PERSON_ID = "00000000-0000-0000-0000-000000009101"
OFFICIAL_ROLE_SOURCE = "20000000-0000-0000-0000-000000009101"
ELECTION_SOURCE = "20000000-0000-0000-0000-000000009102"


def migrated_repository(database: Path) -> SqlAlchemyRepository:
    database_url = f"sqlite:///{database.as_posix()}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")
    return SqlAlchemyRepository(database_url)


def load_bundle() -> tuple[ReviewedPersonBundle, dict]:
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
    primary = ProfileTargetObservation(
        lane=target_raw["lane"],
        candidate=candidate,
        source_refs=tuple(target_raw["source_refs"]),
        discovery_reasons=tuple(target_raw.get("discovery_reasons", [])),
        appointment_target_slugs=tuple(target_raw.get("appointment_target_slugs", [])),
    )
    target = build_profile_research_target(primary)
    bundle = ReviewedPersonBundle(
        person=Person.model_validate(raw["person"]),
        profile_target=target,
        policies=tuple(SourcePolicy.model_validate(item) for item in raw["policies"]),
        sources=tuple(Source.model_validate(item) for item in raw["sources"]),
        snapshots=tuple(SourceSnapshot.model_validate(item) for item in raw["snapshots"]),
        claims=tuple(Claim.model_validate(item) for item in raw["claims"]),
        evidence=tuple(ClaimEvidence.model_validate(item) for item in raw["evidence"]),
    )
    return bundle, raw


def test_reviewed_bundle_preserves_identity_and_defers_unverified_prior_career() -> None:
    bundle, raw = load_bundle()

    assert bundle.person.canonical_name == "임문영"
    assert bundle.person.birth_date is None
    assert bundle.profile_target.canonical_name == "임문영"
    assert bundle.profile_target.source_refs == (
        "https://www.korea.kr/briefing/presidentView.do?newsId=148948860",
        "https://www.yna.co.kr/view/AKR20260604012500054",
    )
    assert {claim.predicate for claim in bundle.claims} == {"HELD_ROLE", "ELECTED_AS"}
    assert raw["deferred_discovery_leads"]
    rendered_claims = " ".join(claim.proposition for claim in bundle.claims)
    assert "한국PC통신" not in rendered_claims
    assert "성남시" not in rendered_claims
    assert all(snapshot.fulltext is None for snapshot in bundle.snapshots)


def test_real_im_munyoung_bundle_imports_and_renders_existing_profile(tmp_path: Path) -> None:
    bundle, _ = load_bundle()
    repository = migrated_repository(tmp_path / "im-munyoung.db")

    repository.import_reviewed_person(bundle)

    with TestClient(create_app(repository)) as client:
        payload = client.get(f"/people/{PERSON_ID}").json()

    assert payload["canonical_name"] == "임문영"
    assert payload["birth_date"] is None
    assert {item["predicate"] for item in payload["claims"]} == {"HELD_ROLE", "ELECTED_AS"}

    sections = {item["id"]: item for item in payload["profile"]["sections"]}
    assert sections["summary"]["status"] == "AVAILABLE"
    assert [item["details"]["predicate"] for item in sections["summary"]["entries"]] == [
        "ELECTED_AS"
    ]
    assert sections["summary"]["entries"][0]["source_ids"] == [ELECTION_SOURCE]

    assert sections["career_timeline"]["status"] == "AVAILABLE"
    assert [
        item["details"]["predicate"] for item in sections["career_timeline"]["entries"]
    ] == ["HELD_ROLE", "ELECTED_AS"]
    assert sections["career_timeline"]["entries"][0]["source_ids"] == [OFFICIAL_ROLE_SOURCE]
    assert sections["career_timeline"]["entries"][1]["source_ids"] == [ELECTION_SOURCE]

    assert sections["current_power_tasks"]["status"] == "UNKNOWN"
    assert sections["appointment_logic"]["status"] == "UNKNOWN"
    assert sections["forecast"]["status"] == "UNKNOWN"
    assert sections["limitations"]["status"] == "AVAILABLE"


def test_real_bundle_sources_are_metadata_only_and_fail_closed_for_reuse() -> None:
    bundle, _ = load_bundle()
    policies = {policy.id: policy for policy in bundle.policies}

    assert all(policy.can_store_metadata for policy in policies.values())
    assert all(not policy.can_store_fulltext for policy in policies.values())
    assert all(not policy.can_send_to_ai for policy in policies.values())
    assert all(not policy.can_commercialize for policy in policies.values())
    assert all(snapshot.fulltext is None for snapshot in bundle.snapshots)

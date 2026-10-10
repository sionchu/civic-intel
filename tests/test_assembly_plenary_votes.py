from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app
from packages.domain.enums import SourceRunStatus
from packages.persistence import SqlAlchemyRepository
from packages.verification.assembly_plenary_votes import (
    AssemblyPlenaryVoteError,
    AssemblyPlenaryVotePublisher,
)
from tests.test_assembly_legislative_activity import prepare_repository
from tests.test_assembly_roll_call_votes import VoteApi, enumerator

# M-001/M-002 are on the current roster fixture; M-999 is not.
VOTES = {
    "B1": {"M-001": "찬성", "M-002": "반대", "M-999": "기권"},
    "B2": {"M-001": "불참", "M-002": "찬성", "M-999": "찬성"},
    "B3": {"M-001": "기권", "M-002": "찬성", "M-999": "찬성"},
}


def collect(repository: SqlAlchemyRepository, api: VoteApi) -> None:
    result = enumerator(api, repository).enumerate()
    assert result.run.status == SourceRunStatus.SUCCESS


def vote_claims(repository: SqlAlchemyRepository):
    return [
        claim
        for claim in repository.claims(published_only=True, current_only=True)
        if claim.predicate == "ASSEMBLY_PLENARY_VOTE"
    ]


def test_publication_requires_a_complete_term_run(tmp_path: Path) -> None:
    repository = prepare_repository(tmp_path)
    with pytest.raises(AssemblyPlenaryVoteError, match="success checkpoint"):
        AssemblyPlenaryVotePublisher(repository).publish_latest_successful()
    api = VoteApi(VOTES)
    enumerator(api, repository, max_bills=1).enumerate()
    with pytest.raises(AssemblyPlenaryVoteError, match="complete term run|whole term"):
        AssemblyPlenaryVotePublisher(repository).publish_latest_successful()


def test_exact_roster_votes_become_claims_and_unreconciled_bills_are_excluded(
    tmp_path: Path,
) -> None:
    repository = prepare_repository(tmp_path)
    api = VoteApi(VOTES)
    # B3's published tallies disagree with its member rows: the bill is excluded.
    api.summary_overrides["B3"] = {"YES_TCNT": 1, "BLANK_TCNT": 2}
    collect(repository, api)

    dry = AssemblyPlenaryVotePublisher(repository).publish_latest_successful(dry_run=True)
    assert dry.published_claims == 4
    assert vote_claims(repository) == []

    result = AssemblyPlenaryVotePublisher(repository).publish_latest_successful()
    assert result.members_published == 2
    assert result.published_claims == 4
    assert result.excluded_unreconciled_bills == ("B3",)
    claims = vote_claims(repository)
    assert {claim.qualifiers["provider_person_key"] for claim in claims} == {"M-001", "M-002"}
    assert {claim.qualifiers["bill_id"] for claim in claims} == {"B1", "B2"}
    absent = next(claim for claim in claims if claim.qualifiers["vote_value"] == "NOT_PARTICIPATING")
    assert absent.qualifiers["vote_value_published"] == "불참"
    assert absent.proposition.endswith("불참으로 기록되어 있다.")
    against = next(claim for claim in claims if claim.qualifiers["vote_value"] == "NO")
    assert against.proposition.endswith("반대로 기록되어 있다.")

    again = AssemblyPlenaryVotePublisher(repository).publish_latest_successful()
    assert (again.published_claims, again.unchanged_claims) == (0, 4)


def test_profile_shows_recent_vote_episodes_and_counts_with_canonical_vote_claims(
    tmp_path: Path,
) -> None:
    repository = prepare_repository(tmp_path)
    collect(repository, VoteApi(VOTES))
    AssemblyPlenaryVotePublisher(repository).publish_latest_successful()
    member = next(
        claim.person_id
        for claim in vote_claims(repository)
        if claim.qualifiers["provider_person_key"] == "M-001"
    )

    with TestClient(create_app(repository)) as client:
        payload = client.get(f"/people/{member}").json()
        people = client.get("/people").json()
    section = next(
        item for item in payload["profile"]["sections"] if item["id"] == "decision_episodes"
    )
    assert section["status"] == "AVAILABLE"
    assert "찬성 1 · 반대 0 · 기권 1 · 불참 1" in section["note"]
    assert len(section["entries"]) == 3
    entry = section["entries"][0]
    assert entry["kind"] == "DECISION_EPISODE"
    assert entry["details"]["action"] == "PLENARY_ROLL_CALL_VOTE"
    assert entry["details"]["outcome"] in {"찬성", "기권", "불참"}
    assert entry["evidence"][0]["feeder_observation_id"]
    rendered = {item["claim_id"] for item in section["entries"]}
    embedded_votes = {
        claim["id"] for claim in payload["claims"] if claim["predicate"] == "ASSEMBLY_PLENARY_VOTE"
    }
    assert embedded_votes == rendered
    assert people and all("discovery" in item for item in people)


def test_all_votes_retain_canonical_bodies_and_source_paths_beyond_recent_ten(tmp_path: Path) -> None:
    repository = prepare_repository(tmp_path)
    api = VoteApi({f"B{number}": {"M-001": "찬성", "M-002": "반대"} for number in range(1, 22)})
    collect(repository, api)
    AssemblyPlenaryVotePublisher(repository).publish_latest_successful()
    canonical = [
        claim for claim in vote_claims(repository)
        if claim.qualifiers["provider_person_key"] == "M-001"
    ]
    person_id = canonical[0].person_id
    with TestClient(create_app(repository)) as client:
        response = client.get(f"/people/{person_id}")
        assert response.status_code == 200
        payload = response.json()
        section = next(item for item in payload["profile"]["sections"] if item["id"] == "decision_episodes")
        assert len(section["entries"]) == 10
        recent_ids = {item["claim_id"] for item in section["entries"]}
        public_votes = {item["id"]: item for item in payload["claims"] if item["predicate"] == "ASSEMBLY_PLENARY_VOTE"}
        assert set(public_votes) == {str(claim.id) for claim in canonical}
        assert len(public_votes) == 21
        assert section["eligible_count"] == 21
        assert section["input_scope"] == "PUBLISHED_SOURCE_VALIDATED_SUBJECT_VOTES"
        older = next(claim for claim in canonical if str(claim.id) not in recent_ids)
        public = public_votes[str(older.id)]
        for field in ("person_id", "subject", "proposition", "object_text", "epistemic_status",
                      "publication_status", "asserted_as_true", "resolution_note", "valid_from", "valid_to"):
            assert public[field] == older.model_dump(mode="json")[field]
        assert public["person_id"] == str(person_id)
        assert "immutable_observation_hash" not in public["qualifiers"]
        assert "immutable_observation_hash" in older.qualifiers
        evidence = repository.evidence_for(older.id)
        assert public["evidence"] == [item.model_dump(mode="json") for item in evidence]
        for source_id in public["source_ids"]:
            assert client.get(f"/sources/{source_id}").status_code == 200


def test_quoted_bill_titles_with_periods_stay_atomic() -> None:
    from packages.verification.claims import is_atomic

    for title in (
        "12.3. 윤석열 비상계엄을 해제한 대한민국 국민께 드리는 감사문",
        "찰스 랭글(Charles B. Rangel) 전 미 하원의원 추모 결의안",
    ):
        assert is_atomic(f"가회원의 본회의 표결은 국회 표결 기록에서 「{title}」에 찬성으로 기록되어 있다.")
    assert not is_atomic("가회원은 찬성했다. 그리고 반대했다.")

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


def test_profile_shows_recent_vote_episodes_and_counts_without_embedding_all_votes(
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

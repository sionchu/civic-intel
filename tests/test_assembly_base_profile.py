from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from apps.api.main import create_app
from packages.connectors.open_assembly import OpenAssemblyMemberConnector
from packages.domain.enums import MaterializationAction
from packages.persistence import SqlAlchemyRepository
from packages.verification.assembly_base_profile import (
    AssemblyBaseProfileError,
    AssemblyBaseProfilePublisher,
)
from workers.assembly_roster import AssemblyRosterEnumerator


def migrated_repository(database: Path) -> SqlAlchemyRepository:
    database_url = f"sqlite:///{database.as_posix()}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")
    return SqlAlchemyRepository(database_url)


def member_row(
    code: str,
    name: str,
    *,
    party: str = "테스트정당",
    district: str = "서울 테스트구",
    reelection: str = "초선",
    committees: str = "테스트위원회",
) -> dict[str, str]:
    return {
        "MONA_CD": code,
        "HG_NM": name,
        "BTH_DATE": "19700102",
        "POLY_NM": party,
        "ORIG_NM": district,
        "REELE_GBN_NM": reelection,
        "CMITS": committees,
    }


class SinglePageRoster:
    def __init__(self, row: dict[str, str]) -> None:
        self.row = row

    def handle(self, request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                OpenAssemblyMemberConnector.API_CODE: [
                    {"head": [{"list_total_count": 1}]},
                    {"row": [self.row]},
                ]
            },
        )

    def connector(self) -> OpenAssemblyMemberConnector:
        return OpenAssemblyMemberConnector(
            api_key="assembly-profile-test-secret",
            page_size=100,
            transport=httpx.MockTransport(self.handle),
        )


def test_base_profile_publishes_atomic_claims_and_projects_evidence(
    tmp_path: Path,
) -> None:
    repository = migrated_repository(tmp_path / "base-profile.db")
    roster = SinglePageRoster(member_row("M-001", "가회원"))
    enumeration = AssemblyRosterEnumerator(roster.connector(), repository).enumerate_and_materialize()

    publisher = AssemblyBaseProfilePublisher(repository)
    result = publisher.publish_latest_successful()

    assert result.observations_considered == 1
    assert result.observations_published == 1
    assert result.published_claims == 4
    assert result.unchanged_claims == 0
    assert result.skipped_observation_ids == ()
    person_id = enumeration.materializations[0].person_id
    assert person_id is not None
    claims = repository.claims(person_id, published_only=True, current_only=True)
    assert {claim.predicate for claim in claims} == {
        "ASSEMBLY_PARTY",
        "ASSEMBLY_DISTRICT",
        "ASSEMBLY_COMMITTEES",
        "ASSEMBLY_REELECTION",
        "HELD_ROLE",
    }
    for claim in claims[:4]:
        evidence = repository.evidence_for(claim.id)
        assert len(evidence) == 1
        assert evidence[0].feeder_observation_id == enumeration.enumeration.observation_ids[0]
        assert evidence[0].snapshot_id is not None

    with TestClient(create_app(repository)) as client:
        payload = client.get(f"/people/{person_id}").json()
        profile = payload["profile"]
        assert profile["profile_kind"] == "ASSEMBLY_MEMBER"
        assert [item["id"] for item in profile["sections"]] == [
            "overview",
            "current_role",
            "career_timeline",
            "legislative_activity",
            "limitations",
        ]
        overview = next(item for item in profile["sections"] if item["id"] == "overview")
        assert overview["status"] == "AVAILABLE"
        assert [entry["details"]["field_name"] for entry in overview["entries"]] == [
            "party",
            "district",
            "reelection",
        ]
        current_role = next(item for item in profile["sections"] if item["id"] == "current_role")
        assert current_role["status"] == "AVAILABLE"
        assert current_role["entries"][0]["details"]["predicate"] == "HELD_ROLE"
        assert current_role["entries"][1]["details"]["field_name"] == "committees"
        assert all(entry["evidence"][0]["feeder_observation_id"] for entry in overview["entries"])
        assert "normalized" not in str(payload)
        assert "TEL_NO" not in str(payload)
        assert "E_MAIL" not in str(payload)

        list_payload = client.get("/people").json()
        discovery = list_payload[0]["discovery"]
        assert discovery["facets"]["role"]["value"] == "국회의원"
        assert discovery["facets"]["party"]["value"] == "테스트정당"
        assert discovery["facets"]["district"]["value"] == "서울 테스트구"
        assert discovery["facets"]["committees"]["value"] == "테스트위원회"
        assert discovery["facets"]["reelection"]["value"] == "초선"
        assert discovery["as_of"]
        assert discovery["source_ids"]
        assert discovery["evidence_ids"]
        assert "normalized" not in str(list_payload)


def test_base_profile_rerun_is_idempotent(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "base-profile-rerun.db")
    roster = SinglePageRoster(member_row("M-001", "가회원"))
    enumerator = AssemblyRosterEnumerator(roster.connector(), repository)
    enumerator.enumerate_and_materialize()
    publisher = AssemblyBaseProfilePublisher(repository)

    first = publisher.publish_latest_successful()
    second = publisher.publish_latest_successful()

    assert first.published_claims == 4
    assert first.unchanged_claims == 0
    assert second.published_claims == 4
    assert second.unchanged_claims == 4
    assert len(repository.claims(published_only=True, current_only=True)) == 5


def test_base_profile_preserves_missingness_without_inference(tmp_path: Path) -> None:
    row = member_row("M-001", "가회원", party="", reelection="", committees="")
    repository = migrated_repository(tmp_path / "base-profile-missing.db")
    roster = SinglePageRoster(row)
    AssemblyRosterEnumerator(roster.connector(), repository).enumerate_and_materialize()

    result = AssemblyBaseProfilePublisher(repository).publish_latest_successful()

    assert result.published_claims == 1
    assert result.missing_field_counts == {
        "party": 1,
        "committees": 1,
        "reelection": 1,
    }
    person = repository.public_people()[0]
    with TestClient(create_app(repository)) as client:
        profile = client.get(f"/people/{person.id}").json()["profile"]
        overview = next(
            item
            for item in profile["sections"]
            if item["id"] == "overview"
        )
    assert overview["status"] == "PARTIAL"
    assert [entry["details"]["field_name"] for entry in overview["entries"]] == ["district"]
    current_role = next(item for item in profile["sections"] if item["id"] == "current_role")
    assert current_role["status"] == "PARTIAL"
    with TestClient(create_app(repository)) as client:
        discovery = client.get("/people").json()[0]["discovery"]
    assert discovery["facets"]["party"] is None
    assert discovery["facets"]["district"]["value"] == "서울 테스트구"
    assert discovery["facets"]["committees"] is None
    assert discovery["facets"]["reelection"] is None
    assert set(discovery["missing_fields"]) == {"party", "committees", "reelection"}


def test_changed_observation_version_fails_closed(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "base-profile-version.db")
    roster = SinglePageRoster(member_row("M-001", "가회원"))
    enumerator = AssemblyRosterEnumerator(roster.connector(), repository)
    enumerator.enumerate_and_materialize()
    publisher = AssemblyBaseProfilePublisher(repository)
    publisher.publish_latest_successful()
    before = repository.claims(published_only=True, current_only=True)

    roster.row["POLY_NM"] = "변경정당"
    changed = enumerator.enumerate_and_materialize()
    assert changed.outcome_counts()[MaterializationAction.AUTO_LINK.value] == 1

    with pytest.raises(AssemblyBaseProfileError, match="immutable observation version"):
        publisher.publish_latest_successful()

    assert repository.claims(published_only=True, current_only=True) == before

from __future__ import annotations

from importlib import import_module
from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from apps.api.main import create_app
from packages.connectors.open_assembly import AssemblyApiError, OpenAssemblyMemberConnector
from packages.domain.enums import (
    IdentityReviewStatus,
    MaterializationAction,
    MaterializationDecisionClass,
    PublicationStatus,
    SourceRunStatus,
)
from packages.persistence import SqlAlchemyRepository
from packages.verification.assembly_base_profile import AssemblyBaseProfilePublisher
from packages.verification.claims import GateResult
from packages.verification.materialization import MaterializationError
from workers.assembly_roster import AssemblyRosterEnumerator

repository_module = import_module("packages.persistence.repository")
SECRET = "assembly-evidence-directory-test-secret"


def member_row(
    code: str,
    name: str,
    *,
    birth_date: str = "19700102",
    party: str = "테스트정당",
) -> dict[str, str]:
    return {
        "MONA_CD": code,
        "HG_NM": name,
        "HJ_NM": f"{name}漢字",
        "ENG_NM": f"{name} English",
        "BTH_DATE": birth_date,
        "POLY_NM": party,
        "ORIG_NM": "서울 테스트구",
        "REELE_GBN_NM": "초선",
        "ELECT_GBN_NM": "지역구",
        "CMITS": "테스트위원회",
        "TEL_NO": "02-0000-0000",
        "E_MAIL": "must-not-persist@example.invalid",
        "KEY": SECRET,
    }


class MultiPageRoster:
    def __init__(self, pages: dict[int, list[dict[str, str]]], *, page_size: int = 2) -> None:
        self.pages = pages
        self.page_size = page_size
        self.fail_pages: set[int] = set()
        self.calls: list[int] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        assert request.url.params["KEY"] == SECRET
        page = int(request.url.params["pIndex"])
        self.calls.append(page)
        if page in self.fail_pages:
            return httpx.Response(503, text=f"provider failure {SECRET}")
        rows = self.pages.get(page, [])
        total = sum(len(items) for items in self.pages.values())
        return httpx.Response(
            200,
            json={
                OpenAssemblyMemberConnector.API_CODE: [
                    {
                        "head": [
                            {"list_total_count": total},
                            {"RESULT": {"CODE": "INFO-000", "MESSAGE": "정상"}},
                        ]
                    },
                    {"row": rows},
                ]
            },
        )

    def connector(self) -> OpenAssemblyMemberConnector:
        return OpenAssemblyMemberConnector(
            api_key=SECRET,
            page_size=self.page_size,
            transport=httpx.MockTransport(self.handle),
        )


def migrated_repository(database: Path) -> SqlAlchemyRepository:
    database_url = f"sqlite:///{database.as_posix()}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")
    return SqlAlchemyRepository(database_url)


def three_member_roster() -> MultiPageRoster:
    return MultiPageRoster(
        {
            1: [member_row("M-001", "가회원"), member_row("M-002", "나회원")],
            2: [member_row("M-003", "다회원")],
        }
    )


def test_successful_roster_materializes_and_reaches_public_evidence_directory(
    tmp_path: Path,
) -> None:
    repository = migrated_repository(tmp_path / "public.db")
    roster = three_member_roster()

    result = AssemblyRosterEnumerator(roster.connector(), repository).enumerate_and_materialize()

    assert result.enumeration.run.status == SourceRunStatus.SUCCESS
    assert result.enumeration.pages_committed == 2
    assert result.enumeration.unique_records == 3
    assert len(result.enumeration.observation_ids) == 3
    assert result.outcome_counts() == {
        MaterializationAction.AUTO_CREATE.value: 3,
        MaterializationAction.AUTO_LINK.value: 0,
        MaterializationAction.REVIEW_REQUIRED.value: 0,
        MaterializationAction.HARD_CONFLICT.value: 0,
    }
    assert len(repository.public_people()) == 3
    assert all(
        claim.predicate == "HELD_ROLE"
        and claim.publication_status == PublicationStatus.PUBLISHED
        for claim in repository.claims(published_only=True)
    )

    materialized = result.materializations[0]
    assert materialized.person_id is not None
    assert materialized.claim_id is not None
    evidence = repository.evidence_for(materialized.claim_id)
    assert len(evidence) == 1
    assert evidence[0].feeder_observation_id == result.enumeration.observation_ids[0]
    assert evidence[0].snapshot_id is not None

    with TestClient(create_app(repository)) as client:
        people_response = client.get("/people")
        assert people_response.status_code == 200
        people = people_response.json()
        assert {item["canonical_name"] for item in people} == {"가회원", "나회원", "다회원"}

        detail = client.get(f"/people/{materialized.person_id}")
        assert detail.status_code == 200
        payload = detail.json()
        timeline = next(
            section for section in payload["profile"]["sections"] if section["id"] == "career_timeline"
        )
        entry = next(item for item in timeline["entries"] if item["kind"] == "CLAIM")
        assert entry["details"]["predicate"] == "HELD_ROLE"
        assert entry["evidence"][0]["feeder_observation_id"] == str(
            result.enumeration.observation_ids[0]
        )
        assert payload["claims"][0]["evidence"][0]["snapshot_id"] == str(
            evidence[0].snapshot_id
        )

        source_id = payload["claims"][0]["evidence"][0]["source_id"]
        source = client.get(f"/sources/{source_id}")
        assert source.status_code == 200
        assert source.json()["source_class"] == "official_open_api"
        assert "policy" not in source.json()


def test_successful_rerun_and_changed_observation_are_idempotent_and_linked(
    tmp_path: Path,
) -> None:
    repository = migrated_repository(tmp_path / "rerun.db")
    roster = three_member_roster()
    enumerator = AssemblyRosterEnumerator(roster.connector(), repository)

    first = enumerator.enumerate_and_materialize()
    second = enumerator.enumerate_and_materialize()

    assert second.enumeration.run.observations_created == 0
    assert second.enumeration.run.observations_unchanged == 3
    assert second.outcome_counts()[MaterializationAction.AUTO_LINK.value] == 3
    assert len(repository.public_people()) == 3
    assert len(repository.claims(published_only=True)) == 3
    assert len(repository.person_observation_links()) == 3

    roster.pages[1][0] = member_row("M-001", "가회원", party="변경정당")
    changed = enumerator.enumerate_and_materialize()

    assert changed.enumeration.run.observations_created == 1
    assert changed.enumeration.run.observations_unchanged == 2
    assert changed.outcome_counts()[MaterializationAction.AUTO_LINK.value] == 3
    assert len(repository.public_people()) == 3
    assert len(repository.claims(published_only=True)) == 3
    first_person_id = first.materializations[0].person_id
    assert first_person_id is not None
    assert len(repository.person_observation_links(first_person_id)) == 2


def test_same_name_different_provider_is_review_required_and_not_public_person(
    tmp_path: Path,
) -> None:
    repository = migrated_repository(tmp_path / "same-name.db")
    result = AssemblyRosterEnumerator(
        MultiPageRoster(
            {
                1: [member_row("M-001", "동명이인"), member_row("M-002", "동명이인")]
            }
        ).connector(),
        repository,
    ).enumerate_and_materialize()

    assert [item.decision.action for item in result.materializations] == [
        MaterializationAction.AUTO_CREATE,
        MaterializationAction.REVIEW_REQUIRED,
    ]
    assert (
        result.materializations[1].decision.decision_class
        == MaterializationDecisionClass.SAME_NAME_AMBIGUITY
    )
    assert len(repository.public_people()) == 1
    assert len(repository.identity_review_items(IdentityReviewStatus.OPEN)) == 1

    with TestClient(create_app(repository)) as client:
        assert len(client.get("/people").json()) == 1


def test_same_name_birth_date_contradiction_is_hard_conflict_and_not_public(
    tmp_path: Path,
) -> None:
    repository = migrated_repository(tmp_path / "hard-conflict.db")
    result = AssemblyRosterEnumerator(
        MultiPageRoster(
            {
                1: [
                    member_row("M-001", "동명이인", birth_date="19700102"),
                    member_row("M-002", "동명이인", birth_date="19800102"),
                ]
            }
        ).connector(),
        repository,
    ).enumerate_and_materialize()

    conflict = result.materializations[1]
    assert conflict.decision.action == MaterializationAction.HARD_CONFLICT
    assert (
        conflict.decision.decision_class
        == MaterializationDecisionClass.EXACT_BIRTH_DATE_CONFLICT
    )
    assert len(repository.public_people()) == 1
    assert len(repository.identity_review_items(IdentityReviewStatus.OPEN)) == 1

    with TestClient(create_app(repository)) as client:
        assert len(client.get("/people").json()) == 1


def test_reviewed_same_name_people_remain_distinct_in_discovery(
    tmp_path: Path,
) -> None:
    repository = migrated_repository(tmp_path / "same-name-reviewed.db")
    result = AssemblyRosterEnumerator(
        MultiPageRoster(
            {
                1: [
                    member_row("M-001", "동명이인", birth_date="19700102", party="첫정당"),
                    member_row("M-002", "동명이인", birth_date="19800102", party="둘째정당"),
                ]
            }
        ).connector(),
        repository,
    ).enumerate_and_materialize()

    conflict = result.materializations[1]
    assert conflict.review_item_id is not None
    reviewed = repository.resolve_assembly_distinct_person_review(
        conflict.review_item_id,
        resolution_note="공식 현재 명부의 서로 다른 생년월일을 확인하여 별도 Person으로 검토 처리",
    )
    assert reviewed.person_id is not None
    AssemblyBaseProfilePublisher(repository).publish_latest_successful()

    with TestClient(create_app(repository)) as client:
        people = client.get("/people").json()

    assert len(people) == 2
    assert len({item["id"] for item in people}) == 2
    assert {item["canonical_name"] for item in people} == {"동명이인"}
    assert {item["discovery"]["facets"]["party"]["value"] for item in people} == {
        "첫정당",
        "둘째정당",
    }


def test_publication_gate_failure_rolls_back_source_specific_materialization(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = migrated_repository(tmp_path / "gate.db")
    roster = MultiPageRoster({1: [member_row("M-001", "롤백의원")]})
    enumerator = AssemblyRosterEnumerator(roster.connector(), repository)
    enumeration = enumerator.enumerate()
    observation_id = enumeration.observation_ids[0]
    monkeypatch.setattr(
        repository_module,
        "validate_claim_publication",
        lambda *args, **kwargs: GateResult(False, ("synthetic_publication_failure",)),
    )

    with pytest.raises(MaterializationError, match="synthetic_publication_failure"):
        repository.materialize_feeder_observation(observation_id)

    assert repository.people() == []
    assert repository.claims() == []
    assert repository.person_observation_links() == []
    assert repository.identity_review_items() == []
    assert repository.feeder_observation(observation_id) is not None


def test_resume_materializes_prior_committed_page_and_new_page_only_after_success(
    tmp_path: Path,
) -> None:
    repository = migrated_repository(tmp_path / "resume.db")
    roster = three_member_roster()
    enumerator = AssemblyRosterEnumerator(roster.connector(), repository)
    roster.fail_pages.add(2)

    with pytest.raises(AssemblyApiError):
        enumerator.enumerate()

    prior_ids = {
        item.id
        for item in repository.feeder_observations(
            AssemblyRosterEnumerator.FEEDER, AssemblyRosterEnumerator.SCOPE_KEY
        )
    }
    assert len(prior_ids) == 2
    assert repository.source_runs()[-1].status == SourceRunStatus.PARTIAL

    roster.fail_pages.clear()
    resumed = enumerator.enumerate_and_materialize(resume=True)

    assert resumed.enumeration.run.status == SourceRunStatus.SUCCESS
    assert resumed.enumeration.pages_committed == 1
    assert set(resumed.enumeration.observation_ids) >= prior_ids
    assert len(resumed.enumeration.observation_ids) == 3
    assert resumed.outcome_counts()[MaterializationAction.AUTO_CREATE.value] == 3
    assert len(repository.public_people()) == 3

from __future__ import annotations

import json
from importlib import import_module
from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from apps.api.main import create_app
from packages.connectors.open_assembly import OpenAssemblyMemberConnector
from packages.domain.enums import (
    IdentityReviewStatus,
    MaterializationAction,
    MaterializationDecisionClass,
    PublicationStatus,
)
from packages.persistence import SqlAlchemyRepository
from packages.verification.assembly_base_profile import AssemblyBaseProfilePublisher
from packages.verification.claims import GateResult
from packages.verification.materialization import MaterializationError
from workers.assembly_roster import AssemblyRosterEnumerator
from workers.assembly_roster import main as assembly_roster_main

SECRET = "materialization-secret"
repository_module = import_module("packages.persistence.repository")


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
        "BTH_DATE": birth_date,
        "POLY_NM": party,
        "ORIG_NM": "서울 테스트구",
        "REELE_GBN_NM": "초선",
        "ELECT_GBN_NM": "지역구",
        "CMITS": "테스트위원회",
        "TEL_NO": "02-0000-0000",
        "E_MAIL": "not-materialized@example.invalid",
        "KEY": SECRET,
    }


class OnePageRoster:
    def __init__(self, rows: list[dict[str, str]]) -> None:
        self.rows = rows

    def handle(self, request: httpx.Request) -> httpx.Response:
        assert request.url.params["KEY"] == SECRET
        return httpx.Response(
            200,
            json={
                OpenAssemblyMemberConnector.API_CODE: [
                    {
                        "head": [
                            {"list_total_count": len(self.rows)},
                            {"RESULT": {"CODE": "INFO-000", "MESSAGE": "정상"}},
                        ]
                    },
                    {"row": self.rows},
                ]
            },
        )

    def connector(self) -> OpenAssemblyMemberConnector:
        return OpenAssemblyMemberConnector(
            api_key=SECRET,
            page_size=100,
            transport=httpx.MockTransport(self.handle),
        )


def migrated_repository(database: Path) -> SqlAlchemyRepository:
    database_url = f"sqlite:///{database.as_posix()}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")
    return SqlAlchemyRepository(database_url)


def enumerate_rows(repository: SqlAlchemyRepository, roster: OnePageRoster):
    AssemblyRosterEnumerator(roster.connector(), repository).enumerate()
    return repository.feeder_observations(
        AssemblyRosterEnumerator.FEEDER, AssemblyRosterEnumerator.SCOPE_KEY
    )


def test_unique_assembly_identity_auto_creates_person_and_published_fact(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "create.db")
    observation = enumerate_rows(
        repository, OnePageRoster([member_row("M-001", "가의원")])
    )[0]

    result = repository.materialize_feeder_observation(observation.id)

    assert result.created
    assert result.decision.action == MaterializationAction.AUTO_CREATE
    assert (
        result.decision.decision_class
        == MaterializationDecisionClass.AUTHORITATIVE_NEW_IDENTITY
    )
    assert result.person_id is not None
    person = repository.person(result.person_id)
    assert person is not None
    assert person.canonical_name == "가의원"
    assert len(repository.people()) == 1
    links = repository.person_observation_links(result.person_id)
    assert len(links) == 1
    assert links[0].observation_id == observation.id
    assert links[0].action == MaterializationAction.AUTO_CREATE

    claims = repository.claims(result.person_id)
    assert len(claims) == 1
    assert claims[0].predicate == "HELD_ROLE"
    assert claims[0].publication_status == PublicationStatus.PUBLISHED
    evidence = repository.evidence_for(claims[0].id)
    assert len(evidence) == 1
    assert evidence[0].snapshot_id == observation.snapshot_id
    assert evidence[0].feeder_observation_id == observation.id


def test_changed_same_provider_identity_auto_links_without_duplicate_person(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "link.db")
    roster = OnePageRoster([member_row("M-001", "가의원")])
    first_observation = enumerate_rows(repository, roster)[0]
    first = repository.materialize_feeder_observation(first_observation.id)
    roster.rows[0] = member_row("M-001", "가의원", party="변경정당")
    observations = enumerate_rows(repository, roster)
    changed_observation = next(
        item for item in observations if item.content_hash != first_observation.content_hash
    )

    linked = repository.materialize_feeder_observation(changed_observation.id)
    repeated = repository.materialize_feeder_observation(changed_observation.id)

    assert linked.decision.action == MaterializationAction.AUTO_LINK
    assert linked.decision.decision_class == MaterializationDecisionClass.EXACT_PROVIDER_IDENTITY
    assert linked.person_id == first.person_id
    assert repeated.person_id == first.person_id
    assert len(repository.people()) == 1
    assert len(repository.person_observation_links(first.person_id)) == 2
    assert len(repository.claims(first.person_id)) == 1


def test_same_korean_name_without_provider_link_enters_review_not_merge(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "review.db")
    observations = enumerate_rows(
        repository,
        OnePageRoster(
            [
                member_row("M-001", "동명이인"),
                member_row("M-002", "동명이인"),
            ]
        ),
    )
    first = repository.materialize_feeder_observation(observations[0].id)

    review = repository.materialize_feeder_observation(observations[1].id)

    assert first.person_id is not None
    assert review.decision.action == MaterializationAction.REVIEW_REQUIRED
    assert review.decision.decision_class == MaterializationDecisionClass.SAME_NAME_AMBIGUITY
    assert review.review_item_id is not None
    assert len(repository.people()) == 1
    items = repository.identity_review_items(IdentityReviewStatus.OPEN)
    assert len(items) == 1
    assert items[0].observation_id == observations[1].id
    assert items[0].candidate_person_id == first.person_id
    assert SECRET not in repr(items[0].model_dump(mode="json"))


def test_exact_birth_date_conflict_enters_hard_conflict_review(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "conflict.db")
    observations = enumerate_rows(
        repository,
        OnePageRoster(
            [
                member_row("M-001", "동명이인", birth_date="19700102"),
                member_row("M-002", "동명이인", birth_date="19800102"),
            ]
        ),
    )
    repository.materialize_feeder_observation(observations[0].id)

    conflict = repository.materialize_feeder_observation(observations[1].id)

    assert conflict.decision.action == MaterializationAction.HARD_CONFLICT
    assert (
        conflict.decision.decision_class
        == MaterializationDecisionClass.EXACT_BIRTH_DATE_CONFLICT
    )
    assert len(repository.people()) == 1
    assert len(repository.identity_review_items(IdentityReviewStatus.OPEN)) == 1


def test_linked_provider_birth_date_change_fails_closed(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "linked-conflict.db")
    roster = OnePageRoster([member_row("M-001", "가의원", birth_date="19700102")])
    first_observation = enumerate_rows(repository, roster)[0]
    created = repository.materialize_feeder_observation(first_observation.id)
    roster.rows[0] = member_row("M-001", "가의원", birth_date="19800102")
    changed_observation = next(
        item
        for item in enumerate_rows(repository, roster)
        if item.content_hash != first_observation.content_hash
    )

    conflict = repository.materialize_feeder_observation(changed_observation.id)

    assert conflict.decision.action == MaterializationAction.HARD_CONFLICT
    assert conflict.person_id is None
    assert conflict.decision.candidate_person_id == created.person_id
    assert len(repository.people()) == 1
    assert len(repository.person_observation_links(created.person_id)) == 1
    assert len(repository.identity_review_items(IdentityReviewStatus.OPEN)) == 1


def test_publication_gate_failure_rolls_back_person_claim_evidence_and_link(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = migrated_repository(tmp_path / "rollback.db")
    observation = enumerate_rows(
        repository, OnePageRoster([member_row("M-001", "롤백의원")])
    )[0]
    monkeypatch.setattr(
        repository_module,
        "validate_claim_publication",
        lambda *args, **kwargs: GateResult(False, ("synthetic_publication_failure",)),
    )

    with pytest.raises(MaterializationError, match="synthetic_publication_failure"):
        repository.materialize_feeder_observation(observation.id)

    assert repository.people() == []
    assert repository.claims() == []
    assert repository.person_observation_links() == []
    assert repository.identity_review_items() == []
    assert len(
        repository.feeder_observations(
            AssemblyRosterEnumerator.FEEDER, AssemblyRosterEnumerator.SCOPE_KEY
        )
    ) == 1


def test_reviewed_assembly_distinct_resolution_is_atomic_idempotent_and_public(
    tmp_path: Path,
) -> None:
    repository = migrated_repository(tmp_path / "reviewed-distinct.db")
    roster = OnePageRoster(
        [
            member_row("M-001", "동명이인", birth_date="19700102"),
            member_row("M-002", "동명이인", birth_date="19800102"),
        ]
    )
    observations = enumerate_rows(repository, roster)
    existing = repository.materialize_feeder_observation(observations[0].id)
    conflict = repository.materialize_feeder_observation(observations[1].id)
    assert existing.person_id is not None
    assert conflict.review_item_id is not None
    review = repository.identity_review_items(IdentityReviewStatus.OPEN)[0]

    resolved = repository.resolve_assembly_distinct_person_review(
        review.id,
        resolution_note=(
            "Operator reviewed the exact Assembly provider record and birth-date conflict; "
            "retain a separate canonical Person without merging the existing candidate."
        ),
    )

    assert resolved.created
    assert resolved.person_id is not None
    assert resolved.person_id != existing.person_id
    assert resolved.claim_id is not None
    assert resolved.review_item_id == review.id
    assert resolved.decision.action == MaterializationAction.REVIEWED_CREATE
    assert (
        resolved.decision.decision_class
        == MaterializationDecisionClass.REVIEWED_DISTINCT_IDENTITY
    )
    assert len(repository.public_people()) == 2
    reviewed_person = repository.person(resolved.person_id)
    assert reviewed_person is not None
    assert reviewed_person.birth_date.isoformat() == "1980-01-02"
    links = repository.person_observation_links(resolved.person_id)
    assert len(links) == 1
    assert links[0].action == MaterializationAction.REVIEWED_CREATE
    assert links[0].decision_class == MaterializationDecisionClass.REVIEWED_DISTINCT_IDENTITY
    assert links[0].review_item_id == review.id
    role_claims = repository.claims(resolved.person_id, published_only=True, current_only=True)
    assert len(role_claims) == 1
    assert role_claims[0].id == resolved.claim_id
    assert role_claims[0].qualifiers == {
        "source_contract": "assembly_member_roster",
        "source_scope": "current_member_roster",
        "semantic_scope": "legislative_member_roster",
        "provider_record_key": "M-002",
        "immutable_observation_hash": observations[1].content_hash,
    }
    evidence = repository.evidence_for(resolved.claim_id)
    assert len(evidence) == 1
    assert evidence[0].snapshot_id == observations[1].snapshot_id
    assert evidence[0].feeder_observation_id == observations[1].id
    stored_review = repository.identity_review_items()[0]
    assert stored_review.status == IdentityReviewStatus.RESOLVED
    assert stored_review.resolved_at is not None
    assert stored_review.resolution_note is not None
    assert stored_review.details["resolution_action"] == MaterializationAction.REVIEWED_CREATE.value
    assert stored_review.details["resolved_person_id"] == str(resolved.person_id)

    repeated = repository.resolve_assembly_distinct_person_review(
        review.id,
        resolution_note="The already committed reviewed resolution is retried idempotently.",
    )
    assert not repeated.created
    assert repeated.person_id == resolved.person_id
    assert repeated.claim_id == resolved.claim_id
    assert len(repository.public_people()) == 2
    assert len(repository.claims(resolved.person_id)) == 1

    profile_result = AssemblyBaseProfilePublisher(repository).publish_latest_successful()
    assert profile_result.observations_considered == 2
    assert profile_result.observations_published == 2
    assert profile_result.published_claims == 8
    assert {
        claim.predicate
        for claim in repository.claims(resolved.person_id, published_only=True, current_only=True)
    } == {
        "HELD_ROLE",
        "ASSEMBLY_PARTY",
        "ASSEMBLY_DISTRICT",
        "ASSEMBLY_COMMITTEES",
        "ASSEMBLY_REELECTION",
    }
    with TestClient(create_app(repository)) as client:
        people = client.get("/people")
        assert people.status_code == 200
        assert len(people.json()) == 2
        resolved_discovery = next(
            item["discovery"] for item in people.json() if item["id"] == str(resolved.person_id)
        )
        assert resolved_discovery["facets"]["role"]["value"] == "국회의원"
        assert "role" not in resolved_discovery["missing_fields"]
        detail = client.get(f"/people/{resolved.person_id}")
        assert detail.status_code == 200
        payload = detail.json()
        overview = next(
            item for item in payload["profile"]["sections"] if item["id"] == "overview"
        )
        assert overview["status"] == "AVAILABLE"
        assert len(overview["entries"]) == 3
        assert all(entry["evidence"] for entry in overview["entries"])
        current_role = next(
            item for item in payload["profile"]["sections"] if item["id"] == "current_role"
        )
        assert current_role["status"] == "AVAILABLE"
        assert len(current_role["entries"]) == 2
        assert "normalized" not in str(payload)
        assert "TEL_NO" not in str(payload)
        assert "E_MAIL" not in str(payload)


def test_reviewed_assembly_distinct_resolution_rejects_stale_observation_version(
    tmp_path: Path,
) -> None:
    repository = migrated_repository(tmp_path / "reviewed-distinct-stale.db")
    roster = OnePageRoster(
        [
            member_row("M-001", "동명이인", birth_date="19700102"),
            member_row("M-002", "동명이인", birth_date="19800102"),
        ]
    )
    observations = enumerate_rows(repository, roster)
    repository.materialize_feeder_observation(observations[0].id)
    repository.materialize_feeder_observation(observations[1].id)
    review = repository.identity_review_items(IdentityReviewStatus.OPEN)[0]

    roster.rows[1] = member_row("M-002", "동명이인", birth_date="19800102", party="변경정당")
    enumerate_rows(repository, roster)

    with pytest.raises(MaterializationError, match="current successful roster version"):
        repository.resolve_assembly_distinct_person_review(
            review.id,
            resolution_note="This should fail closed after the provider observation changed.",
        )

    assert repository.identity_review_items(IdentityReviewStatus.OPEN)[0].id == review.id
    assert len(repository.public_people()) == 1
    assert len(repository.person_observation_links()) == 1


def test_reviewed_assembly_distinct_resolution_rolls_back_on_publication_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = migrated_repository(tmp_path / "reviewed-distinct-rollback.db")
    observations = enumerate_rows(
        repository,
        OnePageRoster(
            [
                member_row("M-001", "동명이인", birth_date="19700102"),
                member_row("M-002", "동명이인", birth_date="19800102"),
            ]
        ),
    )
    repository.materialize_feeder_observation(observations[0].id)
    repository.materialize_feeder_observation(observations[1].id)
    review = repository.identity_review_items(IdentityReviewStatus.OPEN)[0]
    monkeypatch.setattr(
        repository_module,
        "validate_claim_publication",
        lambda *args, **kwargs: GateResult(False, ("synthetic_review_failure",)),
    )

    with pytest.raises(MaterializationError, match="synthetic_review_failure"):
        repository.resolve_assembly_distinct_person_review(
            review.id,
            resolution_note="A failed publication gate must leave the review open.",
        )

    assert len(repository.public_people()) == 1
    assert len(repository.person_observation_links()) == 1
    assert len(repository.claims()) == 1
    assert repository.identity_review_items(IdentityReviewStatus.OPEN)[0].id == review.id


def test_reviewed_assembly_distinct_resolution_cli_is_explicit_and_idempotent(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    database = tmp_path / "reviewed-distinct-cli.db"
    repository = migrated_repository(database)
    observations = enumerate_rows(
        repository,
        OnePageRoster(
            [
                member_row("M-001", "동명이인", birth_date="19700102"),
                member_row("M-002", "동명이인", birth_date="19800102"),
            ]
        ),
    )
    repository.materialize_feeder_observation(observations[0].id)
    repository.materialize_feeder_observation(observations[1].id)
    review = repository.identity_review_items(IdentityReviewStatus.OPEN)[0]
    database_url = f"sqlite:///{database.as_posix()}"

    assert assembly_roster_main(
        [
            "--resolve-review-item",
            str(review.id),
            "--resolution-note",
            "Operator approved the exact source-specific distinct identity.",
            "--database-url",
            database_url,
        ]
    ) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["action"] == MaterializationAction.REVIEWED_CREATE.value
    assert payload["decision_class"] == MaterializationDecisionClass.REVIEWED_DISTINCT_IDENTITY.value
    assert payload["created"] is True

    assert assembly_roster_main(
        [
            "--resolve-review-item",
            str(review.id),
            "--resolution-note",
            "Retry the already committed review resolution.",
            "--database-url",
            database_url,
        ]
    ) == 0
    repeated_payload = json.loads(capsys.readouterr().out)
    assert repeated_payload["created"] is False
    assert repeated_payload["person_id"] == payload["person_id"]
    assert repeated_payload["claim_id"] == payload["claim_id"]

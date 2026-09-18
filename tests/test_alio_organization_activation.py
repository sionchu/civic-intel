from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from test_batch_alio_executives import (
    FakeAlioProvider,
    executive_table,
    report_html,
    vacant_executive_table,
)

from apps.api.main import create_app
from packages.domain.contracts import ClaimEvidence, Organization
from packages.domain.db import SourcePolicyRow
from packages.domain.enums import EvidenceStance, SourceRunStatus
from packages.persistence import SqlAlchemyRepository
from packages.rendering.alio_organization_content import (
    ALIO_CLASSIFICATION_PREDICATE,
    build_alio_classification_claim,
)
from workers.alio_current_executive_claim_import import (
    prepare_import,
)
from workers.public_institutions import AlioExecutiveEnumerator


def migrated_repository(database: Path) -> SqlAlchemyRepository:
    database_url = f"sqlite:///{database.as_posix()}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")
    return SqlAlchemyRepository(database_url)


def enumerated_repository(
    database: Path,
    provider: FakeAlioProvider | None = None,
) -> tuple[SqlAlchemyRepository, FakeAlioProvider]:
    repository = migrated_repository(database)
    source = provider or FakeAlioProvider()
    result = AlioExecutiveEnumerator(source.connector(), repository).enumerate()
    assert result.run.status == SourceRunStatus.SUCCESS
    return repository, source


def commit_prepared(repository: SqlAlchemyRepository):
    prepared = prepare_import(repository)
    result = repository.import_organization_claim_batch(
        [item.organization for item in prepared.items],
        [
            (item.organization, claim, [evidence])
            for item in prepared.items
            for claim, evidence in item.claims
        ],
    )
    return prepared, result


def test_alio_organization_import_is_dry_run_then_atomic_public_commit(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repository, _ = enumerated_repository(tmp_path / "activation.db")
    database_url = f"sqlite:///{(tmp_path / 'activation.db').as_posix()}"

    from workers.alio_current_executive_claim_import import main

    assert main(["--database-url", database_url]) == 0
    dry_run = json.loads(capsys.readouterr().out)
    assert dry_run["status"] == "DRY_RUN"
    assert dry_run["organizations"] == 2
    assert dry_run["organizations_created"] == 2
    assert dry_run["claims"] == 5
    assert repository.organizations() == []

    assert main(["--database-url", database_url, "--commit"]) == 0
    committed = json.loads(capsys.readouterr().out)
    assert committed["status"] == "COMMITTED"
    assert committed["organizations_created"] == 2
    assert committed["claims_created"] == 5
    assert committed["claims_reused"] == 0
    assert repository.people() == []
    assert len(repository.organizations(current_only=True)) == 2

    claims = [
        claim
        for organization in repository.organizations()
        for claim in repository.claims(organization_id=organization.id, current_only=True)
    ]
    assert len(claims) == 5
    assert sum(claim.predicate == ALIO_CLASSIFICATION_PREDICATE for claim in claims) == 2
    assert all(
        len(repository.evidence_for(claim.id)) == 1
        and repository.evidence_for(claim.id)[0].stance == EvidenceStance.SUPPORT
        for claim in claims
    )

    with TestClient(create_app(repository)) as client:
        organizations = client.get("/organizations")
        assert organizations.status_code == 200
        assert len(organizations.json()) == 2
        detail = client.get(f"/organizations/{repository.organizations()[0].id}")
        assert detail.status_code == 200
        assert "normalized" not in json.dumps(detail.json(), ensure_ascii=False)
        assert "contact" not in json.dumps(detail.json(), ensure_ascii=False).casefold()


def test_alio_import_preflight_uses_one_scope_observation_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, _ = enumerated_repository(tmp_path / "bounded-read.db")
    calls: list[str | None] = []
    original = repository.feeder_observations

    def tracked(
        feeder: str,
        scope_key: str,
        provider_record_key: str | None = None,
    ):
        calls.append(provider_record_key)
        return original(feeder, scope_key, provider_record_key)

    monkeypatch.setattr(repository, "feeder_observations", tracked)

    prepared = prepare_import(repository)

    assert len(prepared.observations) == 3
    assert calls == [None]


def test_alio_organization_import_is_idempotent(tmp_path: Path) -> None:
    repository, _ = enumerated_repository(tmp_path / "idempotent.db")

    first_prepared, first = commit_prepared(repository)
    second_prepared, second = commit_prepared(repository)

    assert first_prepared.organizations_created == 2
    assert first.organizations_created == 2
    assert first.claims_created == 5
    assert second_prepared.organizations_reused == 2
    assert second.organizations_created == 0
    assert second.organizations_reused == 2
    assert second.claims_created == 0
    assert second.claims_reused == 5
    assert len(repository.organizations()) == 2
    assert len(repository.claims(organization_id=repository.organizations()[0].id)) == 2


def test_alio_same_name_requires_exact_binding_and_exact_binding_is_reused(
    tmp_path: Path,
) -> None:
    repository, _ = enumerated_repository(tmp_path / "identity.db")
    same_name = Organization(name="테스트공기업")
    with repository.sessions() as session:
        repository._add_organization_row(session, same_name)
        session.commit()

    with pytest.raises(ValueError, match="same-name"):
        prepare_import(repository)
    assert repository.claims(organization_id=same_name.id) == []

    repository, _ = enumerated_repository(tmp_path / "exact-binding.db")
    bound = Organization(id=uuid4(), name="테스트공기업")
    observation = repository.feeder_observations(
        AlioExecutiveEnumerator.FEEDER,
        AlioExecutiveEnumerator.SCOPE_KEY,
        "2026083100000001:1",
    )[0]
    context = repository.feeder_observation_contexts([observation.id])[observation.id]
    _, snapshot, source, policy = context
    claim, evidence = build_alio_classification_claim(
        bound,
        observation,
        source=source,
        snapshot=snapshot,
        policy=policy,
    )
    repository.import_organization_claim_batch([bound], [(bound, claim, [evidence])])

    prepared, result = commit_prepared(repository)
    assert prepared.organizations_reused == 1
    assert result.organizations_created == 1
    assert result.organizations_reused == 1
    assert len([item for item in repository.organizations() if item.name == "테스트공기업"]) == 1
    assert len(repository.claims(organization_id=bound.id)) == 3


def test_alio_masked_and_no_current_rows_do_not_create_named_people_or_claims(
    tmp_path: Path,
) -> None:
    provider = FakeAlioProvider()
    provider.documents[provider.disclosures["C0001"]] = report_html(vacant_executive_table())
    provider.no_disclosure_for.add("C0002")
    repository, _ = enumerated_repository(tmp_path / "masked.db", provider)

    prepared, result = commit_prepared(repository)
    assert prepared.named_rows == 0
    assert prepared.masked_rows == 1
    assert result.claims_created == 1
    organizations = repository.organizations()
    assert [item.name for item in organizations] == ["테스트공기업"]
    assert repository.people() == []
    claims = repository.claims(organization_id=organizations[0].id)
    assert [item.predicate for item in claims] == [ALIO_CLASSIFICATION_PREDICATE]


def test_alio_correction_only_observation_is_not_current_organization_content(
    tmp_path: Path,
) -> None:
    provider = FakeAlioProvider()
    provider.report_titles["C0001"] = "임원현황(수시공시) 수정공시"
    provider.documents[provider.disclosures["C0001"]] = report_html()
    repository, _ = enumerated_repository(tmp_path / "correction.db", provider)

    prepared, result = commit_prepared(repository)
    assert prepared.named_rows == 1
    assert result.organizations_created == 1
    assert [item.name for item in repository.organizations()] == ["테스트준정부기관"]


def test_alio_changed_immutable_observation_version_fails_closed(tmp_path: Path) -> None:
    provider = FakeAlioProvider()
    repository, _ = enumerated_repository(tmp_path / "version.db", provider)
    provider.documents[provider.disclosures["C0001"]] = report_html(
        executive_table("김기관", career="변경된 주요경력"),
        executive_table(
            "박감사", position="비상임감사", title="비상임감사", career="회계법인 대표"
        ),
    )
    AlioExecutiveEnumerator(provider.connector(), repository).enumerate()

    with pytest.raises(ValueError, match="immutable observation version"):
        prepare_import(repository)
    assert repository.organizations() == []
    assert repository.claims() == []


def test_alio_batch_rolls_back_all_organizations_on_late_evidence_failure(
    tmp_path: Path,
) -> None:
    repository, _ = enumerated_repository(tmp_path / "rollback.db")
    prepared = prepare_import(repository)
    items = [
        (item.organization, claim, [evidence])
        for item in prepared.items
        for claim, evidence in item.claims
    ]
    first_claim, first_evidence = items[0][1], items[0][2][0]
    items[-1] = (
        items[-1][0],
        items[-1][1],
        [
            ClaimEvidence(
                id=uuid4(),
                claim_id=items[-1][1].id,
                source_id=uuid4(),
                snapshot_id=first_evidence.snapshot_id,
                feeder_observation_id=first_evidence.feeder_observation_id,
                stance=first_evidence.stance,
            )
        ],
    )
    assert first_claim.id != items[-1][1].id

    with pytest.raises(ValueError, match="missing source"):
        repository.import_organization_claim_batch(
            [item.organization for item in prepared.items], items
        )
    assert repository.organizations() == []
    assert repository.claims() == []


def test_alio_policy_denial_blocks_publication_preflight(tmp_path: Path) -> None:
    repository, _ = enumerated_repository(tmp_path / "policy.db")
    with repository.sessions() as session:
        row = session.get(SourcePolicyRow, "13000000-0000-0000-0000-000000000001")
        assert row is not None
        row.can_store_metadata = False
        session.commit()

    with pytest.raises(ValueError, match="SourcePolicy forbids metadata storage"):
        prepare_import(repository)
    assert repository.organizations() == []

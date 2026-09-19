from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import event
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


def scaled_batch(prepared, organization_count: int):
    templates = [
        (claim, evidence)
        for item in prepared.items
        for claim, evidence in item.claims
    ]
    organizations: list[Organization] = []
    items = []
    for index in range(organization_count):
        organization = Organization(name=f"확장 테스트 기관 {index:03d}")
        organizations.append(organization)
        for template_index, (template_claim, template_evidence) in enumerate(templates):
            qualifiers = dict(template_claim.qualifiers)
            qualifiers["provider_record_key"] = (
                f"{template_claim.qualifiers['provider_record_key']}"
                f":scaled:{index:03d}:{template_index:02d}"
            )
            claim = template_claim.model_copy(
                update={
                    "id": uuid4(),
                    "organization_id": organization.id,
                    "proposition": template_claim.proposition.replace(
                        template_claim.subject, organization.name
                    ),
                    "subject": organization.name,
                    "qualifiers": qualifiers,
                }
            )
            evidence = template_evidence.model_copy(
                update={"id": uuid4(), "claim_id": claim.id}
            )
            items.append((organization, claim, [evidence]))
    return organizations, items


def count_batch_selects(repository: SqlAlchemyRepository, organizations, items) -> int:
    statements: list[str] = []

    def before_cursor_execute(_connection, _cursor, statement, *_args):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    event.listen(repository.engine, "before_cursor_execute", before_cursor_execute)
    try:
        repository.import_organization_claim_batch(organizations, items)
    finally:
        event.remove(repository.engine, "before_cursor_execute", before_cursor_execute)
    return len(statements)


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
        organization = next(
            organization
            for organization in repository.organizations()
            if any(
                claim.predicate == ALIO_EXECUTIVE_PREDICATE
                for claim in repository.claims(
                    organization_id=organization.id,
                    published_only=True,
                    current_only=True,
                )
            )
        )
        detail = client.get(f"/organizations/{organization.id}")
        assert detail.status_code == 200
        assert "normalized" not in json.dumps(detail.json(), ensure_ascii=False)
        assert "contact" not in json.dumps(detail.json(), ensure_ascii=False).casefold()

        ontology = client.get(f"/ontology/organizations/{organization.id}")
        assert ontology.status_code == 200
        ontology_payload = ontology.json()
        assert ontology_payload["center_node_id"] == f"organization:{organization.id}"
        executive_claim_count = sum(
            claim.predicate == ALIO_EXECUTIVE_PREDICATE
            for claim in repository.claims(
                organization_id=organization.id,
                published_only=True,
                current_only=True,
            )
        )
        assert len(ontology_payload["edges"]) == executive_claim_count
        assert all(
            edge["relation_type"] == "LISTS_EXECUTIVE"
            for edge in ontology_payload["edges"]
        )
        assert all(
            node["canonical_id"] is None
            for node in ontology_payload["nodes"]
            if node["kind"] == "SOURCE_LISTED_ROLE_HOLDER"
        )
        assert "normalized" not in json.dumps(ontology_payload, ensure_ascii=False)
        assert "contact" not in json.dumps(ontology_payload, ensure_ascii=False).casefold()


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


def test_alio_organization_batch_query_shape_is_bounded(tmp_path: Path) -> None:
    small_repository, _ = enumerated_repository(tmp_path / "query-small.db")
    small_prepared = prepare_import(small_repository)
    small_count = count_batch_selects(
        small_repository,
        [item.organization for item in small_prepared.items],
        [
            (item.organization, claim, [evidence])
            for item in small_prepared.items
            for claim, evidence in item.claims
        ],
    )

    scaled_repository, _ = enumerated_repository(tmp_path / "query-scaled.db")
    scaled_prepared = prepare_import(scaled_repository)
    organizations, items = scaled_batch(scaled_prepared, 120)
    scaled_count = count_batch_selects(scaled_repository, organizations, items)

    assert len(items) == 600
    assert scaled_count <= small_count + 20
    assert scaled_count <= 40


def test_alio_organization_batch_rejects_duplicate_input_ids_and_names(
    tmp_path: Path,
) -> None:
    repository, _ = enumerated_repository(tmp_path / "duplicate-input.db")
    prepared = prepare_import(repository)
    organization = prepared.items[0].organization
    claim, evidence = prepared.items[0].claims[0]
    duplicate = Organization(name=organization.name)
    duplicate_claim = claim.model_copy(
        update={
            "id": uuid4(),
            "organization_id": duplicate.id,
            "subject": duplicate.name,
            "proposition": claim.proposition.replace(claim.subject, duplicate.name),
            "qualifiers": {
                **claim.qualifiers,
                "provider_record_key": f"{claim.qualifiers['provider_record_key']}:duplicate",
            },
        }
    )
    duplicate_evidence = evidence.model_copy(update={"id": uuid4(), "claim_id": duplicate_claim.id})

    with pytest.raises(ValueError, match="duplicate incoming Organization names"):
        repository.import_organization_claim_batch(
            [organization, duplicate],
            [(organization, claim, [evidence]), (duplicate, duplicate_claim, [duplicate_evidence])],
        )
    assert repository.organizations() == []

    with pytest.raises(ValueError, match="duplicate Claim IDs"):
        repository.import_organization_claim_batch(
            [organization],
            [
                (organization, claim, [evidence]),
                (
                    organization,
                    claim.model_copy(
                        update={
                            "qualifiers": {
                                **claim.qualifiers,
                                "provider_record_key": f"{claim.qualifiers['provider_record_key']}:id",
                            }
                        }
                    ),
                    [evidence.model_copy(update={"id": uuid4()})],
                ),
            ],
        )

    with pytest.raises(ValueError, match="duplicate Evidence IDs"):
        repository.import_organization_claim_batch(
            [organization],
            [
                (organization, claim, [evidence]),
                (
                    organization,
                    claim.model_copy(
                        update={
                            "id": uuid4(),
                            "qualifiers": {
                                **claim.qualifiers,
                                "provider_record_key": f"{claim.qualifiers['provider_record_key']}:evidence",
                            },
                        }
                    ),
                    [evidence],
                ),
            ],
        )


def test_alio_organization_batch_rejects_existing_id_and_source_owner_collisions(
    tmp_path: Path,
) -> None:
    repository, _ = enumerated_repository(tmp_path / "collision-claim.db")
    prepared, _ = commit_prepared(repository)
    organization = prepared.items[0].organization
    claim, evidence = prepared.items[0].claims[0]

    with pytest.raises(ValueError, match="ID already exists"):
        repository.import_organization_claim_batch(
            [organization],
            [
                (
                    organization,
                    claim.model_copy(
                        update={
                            "qualifiers": {
                                **claim.qualifiers,
                                "provider_record_key": f"{claim.qualifiers['provider_record_key']}:collision",
                            }
                        }
                    ),
                    [evidence.model_copy(update={"id": uuid4(), "claim_id": claim.id})],
                )
            ],
        )

    with pytest.raises(ValueError, match="evidence ID already exists"):
        new_claim = claim.model_copy(
            update={
                "id": uuid4(),
                "qualifiers": {
                    **claim.qualifiers,
                    "provider_record_key": f"{claim.qualifiers['provider_record_key']}:evidence-collision",
                },
            }
        )
        repository.import_organization_claim_batch(
            [organization],
            [
                (
                    organization,
                    new_claim,
                    [evidence.model_copy(update={"claim_id": new_claim.id})],
                )
            ],
        )

    new_organization = Organization(name="소유권 충돌 기관")
    owner_claim = claim.model_copy(
        update={
            "id": uuid4(),
            "organization_id": new_organization.id,
            "subject": new_organization.name,
            "proposition": claim.proposition.replace(claim.subject, new_organization.name),
        }
    )
    owner_evidence = evidence.model_copy(update={"id": uuid4(), "claim_id": owner_claim.id})
    with pytest.raises(ValueError, match="bound to another Organization"):
        repository.import_organization_claim_batch(
            [new_organization], [(new_organization, owner_claim, [owner_evidence])]
        )
    assert repository.organization(new_organization.id) is None


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

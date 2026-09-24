from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, func, select
from test_alio_organization_activation import (
    commit_prepared,
    enumerated_repository,
)
from test_batch_alio_executives import (
    FakeAlioProvider,
    executive_table,
    report_html,
)

from apps.api.main import create_app
from packages.domain import db
from packages.domain.admin import AdminCommand
from packages.domain.enums import IdentityStatus, PublicationStatus
from packages.persistence.alio_person_materialization import (
    AlioPersonMaterializationError,
)
from packages.verification.alio_person_materialization import (
    PERSON_ROLE_PREDICATE,
)
from packages.verification.postgresql import verify_restored_database


def ready_repository(tmp_path: Path, provider: FakeAlioProvider | None = None):
    repository, provider = enumerated_repository(tmp_path / "alio-safe.db", provider)
    commit_prepared(repository)
    return repository, provider


def table_counts(repository):
    with repository.sessions() as session:
        return {
            "people": session.scalar(select(func.count()).select_from(db.PersonRow)),
            "claims": session.scalar(select(func.count()).select_from(db.ClaimRow)),
            "evidence": session.scalar(select(func.count()).select_from(db.ClaimEvidenceRow)),
            "links": session.scalar(select(func.count()).select_from(db.PersonObservationLinkRow)),
            "published": session.scalar(
                select(func.count())
                .select_from(db.ClaimRow)
                .where(
                    db.ClaimRow.superseded_at.is_(None),
                    db.ClaimRow.publication_status == PublicationStatus.PUBLISHED.value,
                )
            ),
            "observations": session.scalar(
                select(func.count()).select_from(db.FeederObservationRow)
            ),
            "snapshots": session.scalar(select(func.count()).select_from(db.SourceSnapshotRow)),
        }


def test_dry_run_is_deterministic_and_reconciles_fixture(tmp_path: Path):
    repository, _ = ready_repository(tmp_path)
    before = table_counts(repository)

    first = repository.prepare_alio_person_materialization()
    second = repository.prepare_alio_person_materialization()

    assert first.to_dict() == second.to_dict()
    assert first.sha256() == second.sha256()
    assert first.current_named_rows == 3
    assert first.action_counts() == {
        "CREATE": 3,
        "REVIEW": 0,
        "CONFLICT": 0,
        "NOOP": 0,
    }
    assert first.reason_counts() == {"SAFE_SINGLETON_SOURCE_CONTEXT": 3}
    assert len(first.to_dict()["selected"]) == 3
    assert {
        item["person_identity_status"] for item in first.to_dict()["selected"]
    } == {"REVIEW"}
    assert {
        item["claim_publication_status"] for item in first.to_dict()["selected"]
    } == {"DRAFT"}
    assert {
        item["link_decision_class"] for item in first.to_dict()["selected"]
    } == {"DETERMINISTIC_SOURCE_CONTEXT"}
    assert first.to_dict()["expected_post_counts"] == {
        "people": before["people"] + 3,
        "claims": before["claims"] + 3,
        "evidence": before["evidence"] + 3,
        "links": before["links"] + 3,
        "published_claims": before["published"],
    }
    assert first.to_dict()["source_fetch"] is False
    assert first.to_dict()["claim_publication"] is False
    assert table_counts(repository) == before


def test_commit_creates_draft_source_context_people_and_is_idempotent(tmp_path: Path):
    repository, _ = ready_repository(tmp_path)
    before = table_counts(repository)
    preflight = repository.prepare_alio_person_materialization()

    receipt = repository.commit_alio_person_materialization(
        expected_receipt_sha256=preflight.sha256()
    )

    after = table_counts(repository)
    assert receipt["status"] == "COMMITTED"
    assert receipt["created_people"] == 3
    assert receipt["created_claims"] == 3
    assert receipt["created_evidence"] == 3
    assert receipt["created_links"] == 3
    assert after["people"] == before["people"] + 3
    assert after["claims"] == before["claims"] + 3
    assert after["evidence"] == before["evidence"] + 3
    assert after["links"] == before["links"] + 3
    assert after["published"] == before["published"]
    assert after["observations"] == before["observations"]
    assert after["snapshots"] == before["snapshots"]

    with repository.sessions() as session:
        people = list(session.scalars(select(db.PersonRow)))
        claims = list(
            session.scalars(
                select(db.ClaimRow).where(db.ClaimRow.predicate == PERSON_ROLE_PREDICATE)
            )
        )
        links = list(session.scalars(select(db.PersonObservationLinkRow)))
    assert len(people) == 3
    assert all(row.identity_status == IdentityStatus.REVIEW.value for row in people)
    assert len(claims) == 3
    assert all(row.publication_status == "DRAFT" for row in claims)
    assert all(row.epistemic_status == "CLAIM" for row in claims)
    assert all(row.asserted_as_true is False for row in claims)
    assert all(
        row.qualifiers["identity_scope"] == "DETERMINISTIC_ALIO_SOURCE_CONTEXT"
        for row in claims
    )
    assert all(row.action == "AUTO_CREATE" for row in links)
    assert all(row.decision_class == "DETERMINISTIC_SOURCE_CONTEXT" for row in links)

    rerun = repository.prepare_alio_person_materialization()
    assert rerun.action_counts() == {
        "CREATE": 0,
        "REVIEW": 0,
        "CONFLICT": 0,
        "NOOP": 3,
    }
    assert rerun.reason_counts() == {"ALREADY_MATERIALIZED": 3}
    noop = repository.commit_alio_person_materialization(
        expected_receipt_sha256=rerun.sha256()
    )
    assert noop["status"] == "NOOP"
    assert noop["write_performed"] is False
    assert table_counts(repository) == after
    assert repository.admin_queue(state="SOURCE_CONTEXT_REVIEW")["total"] == 3
    assert repository.admin_queue(state="REGISTERED")["total"] == 0
    summary = repository.operator_summary()
    assert summary["counts"]["current_people"] == before["people"] + 3
    assert summary["counts"]["resolved_people"] == before["people"]
    assert summary["counts"]["source_context_review_people"] == 3
    with TestClient(create_app(repository)) as client:
        assert client.get("/people").json() == []
        for item in preflight.create_items:
            assert item.packet is not None
            assert client.get(f"/people/{item.packet.person.id}").status_code == 404


def test_repeated_current_name_and_existing_person_collision_stay_review_only(tmp_path: Path):
    provider = FakeAlioProvider()
    disclosure = provider.disclosures["C0002"]
    provider.documents[disclosure] = report_html(executive_table("김기관"))
    repository, _ = ready_repository(tmp_path, provider)

    now = datetime.now(UTC)
    with repository.sessions() as session:
        session.add(
            db.PersonRow(
                id=str(uuid4()),
                canonical_name="박감사",
                birth_date=None,
                identity_status="RESOLVED",
                valid_from=now,
                valid_to=None,
                recorded_at=now,
                superseded_at=None,
            )
        )
        session.commit()

    preflight = repository.prepare_alio_person_materialization()
    assert preflight.current_named_rows == 3
    assert preflight.action_counts() == {
        "CREATE": 0,
        "REVIEW": 3,
        "CONFLICT": 0,
        "NOOP": 0,
    }
    assert preflight.reason_counts() == {
        "CURRENT_NAME_REPEATED": 2,
        "CURRENT_PERSON_OR_ALIAS_COLLISION": 1,
    }


def test_alias_collision_stays_review_only(tmp_path: Path):
    repository, _ = ready_repository(tmp_path)
    now = datetime.now(UTC)
    person_id = str(uuid4())
    with repository.sessions() as session:
        session.add(
            db.PersonRow(
                id=person_id,
                canonical_name="다른현재이름",
                birth_date=None,
                identity_status="RESOLVED",
                valid_from=now,
                valid_to=None,
                recorded_at=now,
                superseded_at=None,
            )
        )
        session.flush()
        session.add(
            db.PersonAliasRow(
                id=str(uuid4()),
                person_id=person_id,
                name="김기관",
                valid_from=now,
                valid_to=None,
                recorded_at=now,
                superseded_at=None,
            )
        )
        session.commit()

    preflight = repository.prepare_alio_person_materialization()
    assert preflight.reason_counts()["CURRENT_PERSON_OR_ALIAS_COLLISION"] == 1
    assert preflight.action_counts()["CREATE"] == 2


def test_historical_provider_version_drift_stays_review_only(tmp_path: Path):
    repository, _ = ready_repository(tmp_path)
    first = repository.prepare_alio_person_materialization().create_items[0]
    with repository.sessions() as session:
        original = session.get(db.FeederObservationRow, str(first.observation_id))
        session.add(
            db.FeederObservationRow(
                id=str(uuid4()),
                feeder=original.feeder,
                scope_key=original.scope_key,
                provider_record_key=original.provider_record_key,
                snapshot_id=original.snapshot_id,
                run_id=original.run_id,
                recorded_at=original.recorded_at,
                provider_observed_at=original.provider_observed_at,
                semantic_scope=original.semantic_scope,
                identity_hints_json=original.identity_hints_json,
                normalized_json={**original.normalized_json, "title": "historical changed version"},
                content_hash="f" * 64,
            )
        )
        session.commit()

    preflight = repository.prepare_alio_person_materialization()
    assert preflight.reason_counts()["HISTORICAL_VERSION_DRIFT"] == 1
    assert preflight.action_counts()["CREATE"] == 2
    assert preflight.action_counts()["REVIEW"] == 1


def test_missing_organization_binding_is_conflict_not_creation(tmp_path: Path):
    repository, _ = enumerated_repository(tmp_path / "missing-org.db")

    preflight = repository.prepare_alio_person_materialization()

    assert preflight.current_named_rows == 3
    assert preflight.action_counts()["CREATE"] == 0
    assert preflight.action_counts()["CONFLICT"] == 3
    assert preflight.reason_counts() == {"ORGANIZATION_BINDING_REQUIRED": 3}


def test_stale_receipt_rejects_entire_commit(tmp_path: Path):
    repository, _ = ready_repository(tmp_path)
    preflight = repository.prepare_alio_person_materialization()
    first = preflight.create_items[0]
    now = datetime.now(UTC)
    with repository.sessions() as session:
        session.add(
            db.PersonRow(
                id=str(uuid4()),
                canonical_name=first.canonical_name,
                birth_date=None,
                identity_status="RESOLVED",
                valid_from=now,
                valid_to=None,
                recorded_at=now,
                superseded_at=None,
            )
        )
        session.commit()
    before = table_counts(repository)

    with pytest.raises(AlioPersonMaterializationError) as exc:
        repository.commit_alio_person_materialization(
            expected_receipt_sha256=preflight.sha256()
        )

    assert exc.value.code == "STALE_PREFLIGHT"
    assert table_counts(repository) == before


def test_partial_deterministic_artifact_is_hard_conflict(tmp_path: Path):
    repository, _ = ready_repository(tmp_path)
    preflight = repository.prepare_alio_person_materialization()
    packet = preflight.create_items[0].packet
    assert packet is not None
    person = packet.person
    with repository.sessions() as session:
        session.add(
            db.PersonRow(
                id=str(person.id),
                canonical_name=person.canonical_name,
                birth_date=person.birth_date,
                identity_status=person.identity_status.value,
                valid_from=person.valid_from,
                valid_to=person.valid_to,
                recorded_at=person.recorded_at,
                superseded_at=None,
            )
        )
        session.commit()

    next_preflight = repository.prepare_alio_person_materialization()
    assert next_preflight.reason_counts()["PARTIAL_OR_CONFLICTING_MATERIALIZATION"] == 1
    assert next_preflight.action_counts()["CONFLICT"] == 1
    assert next_preflight.action_counts()["CREATE"] == 2


def test_database_failure_rolls_back_people_claims_evidence_and_links(
    tmp_path: Path,
):
    repository, _ = ready_repository(tmp_path)
    preflight = repository.prepare_alio_person_materialization()
    before = table_counts(repository)

    def fail_claim_insert(mapper, connection, target):
        raise RuntimeError("synthetic claim insert failure")

    event.listen(db.ClaimRow, "before_insert", fail_claim_insert)
    try:
        with pytest.raises(RuntimeError, match="synthetic claim insert failure"):
            repository.commit_alio_person_materialization(
                expected_receipt_sha256=preflight.sha256()
            )
    finally:
        event.remove(db.ClaimRow, "before_insert", fail_claim_insert)

    assert table_counts(repository) == before


def test_cli_dry_run_and_commit_require_exact_receipt(tmp_path: Path, capsys):
    from workers.alio_safe_person_materialization import main

    repository, _ = ready_repository(tmp_path)
    database_url = str(repository.engine.url)
    repository.engine.dispose()

    assert main(["--database-url", database_url]) == 0
    dry_run = json.loads(capsys.readouterr().out)
    assert dry_run["status"] == "DRY_RUN"
    assert dry_run["write_performed"] is False
    assert dry_run["selected_count"] == 3

    assert (
        main(
            [
                "--database-url",
                database_url,
                "--commit",
                "--expected-receipt-sha256",
                dry_run["receipt_sha256"],
            ]
        )
        == 0
    )
    committed = json.loads(capsys.readouterr().out)
    assert committed["status"] == "COMMITTED"
    assert committed["created_people"] == 3
    assert committed["claim_publication"] is False

def test_source_context_person_requires_human_resolution_before_registered_state(tmp_path: Path):
    repository, _ = ready_repository(tmp_path)
    preflight = repository.prepare_alio_person_materialization()
    repository.commit_alio_person_materialization(expected_receipt_sha256=preflight.sha256())
    item = preflight.create_items[0]
    assert item.packet is not None
    person_id = item.packet.person.id

    command = AdminCommand(
        request_id=uuid4(),
        action="RESOLVE_PERSON",
        record_ids=(person_id,),
        reason="공식 ALIO 현재 공시의 이름·기관·직책과 연결된 원문 근거를 직접 확인했습니다.",
        human_verified=True,
    )
    preview = repository.admin_preview(command)
    receipt = repository.admin_commit(command, "test-reviewer", preview["state_hash"])

    person = repository.person(person_id)
    assert person is not None
    assert person.identity_status == IdentityStatus.RESOLVED
    assert receipt["result"]["outcomes"][0]["cross_source_merge"] is False
    claims = repository.claims(person_id=person_id)
    assert len(claims) == 1
    assert claims[0].publication_status == PublicationStatus.DRAFT
    assert repository.admin_queue(state="SOURCE_CONTEXT_REVIEW")["total"] == 2
    assert repository.admin_queue(state="REGISTERED")["total"] == 1
    with repository.sessions() as session:
        session.add(
            db.ClaimRow(
                id=str(uuid4()),
                person_id=str(person_id),
                organization_id=None,
                subject="다른 공개 기록",
                predicate="UNRELATED_PUBLISHED_CLAIM",
                object_text="ALIO 역할 Claim과 무관한 공개 기록",
                proposition="ALIO 역할 Claim과 무관한 공개 기록이다.",
                qualifiers={},
                epistemic_status="CLAIM",
                publication_status="PUBLISHED",
                asserted_as_true=False,
                resolution_note=None,
                valid_from=datetime.now(UTC),
                valid_to=None,
                recorded_at=datetime.now(UTC),
                superseded_at=None,
            )
        )
        session.commit()

    with TestClient(create_app(repository)) as client:
        assert all(row["id"] != str(person_id) for row in client.get("/people").json())
        assert client.get(f"/people/{person_id}").status_code == 404

    publish = AdminCommand(
        request_id=uuid4(),
        action="PUBLISH",
        record_ids=(claims[0].id,),
        reason="신원 확인 뒤에도 별도 역할 공개 검증을 수행합니다.",
    )
    publish_preview = repository.admin_preview(publish)
    repository.admin_commit(publish, "test-reviewer", publish_preview["state_hash"])
    with TestClient(create_app(repository)) as client:
        assert any(row["id"] == str(person_id) for row in client.get("/people").json())
        assert client.get(f"/people/{person_id}").status_code == 200


def test_resolve_person_rejects_non_source_context_identity(tmp_path: Path):
    repository, _ = ready_repository(tmp_path)
    now = datetime.now(UTC)
    person_id = uuid4()
    with repository.sessions() as session:
        session.add(
            db.PersonRow(
                id=str(person_id),
                canonical_name="일반 검토 인물",
                birth_date=None,
                identity_status=IdentityStatus.REVIEW.value,
                valid_from=now,
                valid_to=None,
                recorded_at=now,
                superseded_at=None,
            )
        )
        session.commit()
    command = AdminCommand(
        request_id=uuid4(),
        action="RESOLVE_PERSON",
        record_ids=(person_id,),
        reason="일반 REVIEW 인물에는 source-context 자동 승인 경로를 적용하지 않습니다.",
        human_verified=True,
    )
    with pytest.raises(Exception, match="source-context"):
        repository.admin_preview(command)

def test_human_resolution_and_publication_remain_materialization_noop(tmp_path: Path):
    repository, _ = ready_repository(tmp_path)
    preflight = repository.prepare_alio_person_materialization()
    repository.commit_alio_person_materialization(expected_receipt_sha256=preflight.sha256())
    item = preflight.create_items[0]
    assert item.packet is not None
    person_id = item.packet.person.id

    resolve = AdminCommand(
        request_id=uuid4(),
        action="RESOLVE_PERSON",
        record_ids=(person_id,),
        reason="공식 ALIO 현재 공시와 source-context 역할 근거를 사람 검토로 확인했습니다.",
        human_verified=True,
    )
    resolve_preview = repository.admin_preview(resolve)
    repository.admin_commit(resolve, "test-reviewer", resolve_preview["state_hash"])

    publish = AdminCommand(
        request_id=uuid4(),
        action="PUBLISH",
        record_ids=(item.packet.claim.id,),
        reason="확인된 source-context 신원과 현재 역할 근거를 검토하여 공개합니다.",
    )
    publish_preview = repository.admin_preview(publish)
    repository.admin_commit(publish, "test-reviewer", publish_preview["state_hash"])

    rerun = repository.prepare_alio_person_materialization()
    selected = next(row for row in rerun.items if row.observation_id == item.observation_id)
    assert selected.action == "NOOP"
    assert selected.reason == "ALREADY_MANAGED"
    assert rerun.action_counts()["CREATE"] == 0
    noop = repository.commit_alio_person_materialization(
        expected_receipt_sha256=rerun.sha256()
    )
    assert noop["write_performed"] is False


def test_renamed_source_context_person_with_preserved_alias_remains_noop(tmp_path: Path):
    repository, _ = ready_repository(tmp_path)
    preflight = repository.prepare_alio_person_materialization()
    repository.commit_alio_person_materialization(expected_receipt_sha256=preflight.sha256())
    item = preflight.create_items[0]
    assert item.packet is not None
    person_id = item.packet.person.id

    resolve = AdminCommand(
        request_id=uuid4(),
        action="RESOLVE_PERSON",
        record_ids=(person_id,),
        reason="공식 ALIO source-context 신원을 사람 검토로 확인했습니다.",
        human_verified=True,
    )
    preview = repository.admin_preview(resolve)
    repository.admin_commit(resolve, "test-reviewer", preview["state_hash"])

    evidence_id = item.packet.evidence.id
    rename = AdminCommand(
        request_id=uuid4(),
        action="RENAME_PERSON",
        record_ids=(person_id,),
        reason="공식 근거를 검토하여 canonical 표기를 정정하고 이전 표기를 alias로 보존합니다.",
        evidence_ids=(evidence_id,),
        value=item.packet.person.canonical_name + " 정정",
    )
    rename_preview = repository.admin_preview(rename)
    repository.admin_commit(rename, "test-reviewer", rename_preview["state_hash"])

    rerun = repository.prepare_alio_person_materialization()
    selected = next(row for row in rerun.items if row.observation_id == item.observation_id)
    assert selected.action == "NOOP"
    assert selected.reason == "ALREADY_MANAGED"

def test_restore_verifier_separates_review_people_from_public_roster(tmp_path: Path):
    repository, _ = ready_repository(tmp_path)
    preflight = repository.prepare_alio_person_materialization()
    repository.commit_alio_person_materialization(expected_receipt_sha256=preflight.sha256())
    with repository.sessions() as session:
        organization_claims = session.scalar(
            select(func.count())
            .select_from(db.ClaimRow)
            .where(
                db.ClaimRow.organization_id.is_not(None),
                db.ClaimRow.publication_status == PublicationStatus.PUBLISHED.value,
                db.ClaimRow.superseded_at.is_(None),
            )
        ) or 0
    report = verify_restored_database(
        str(repository.engine.url),
        expected_people=3,
        expected_public_people=0,
        expected_organization_claims=organization_claims,
    )
    assert report["people"] == 3
    assert report["public_people"] == 0

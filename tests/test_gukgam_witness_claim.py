from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event

from apps.api.main import create_app
from apps.cli.main import main, parse_command
from packages.domain.contracts import Person, PersonObservationLink
from packages.domain.enums import (
    IdentityStatus,
    MaterializationAction,
    MaterializationDecisionClass,
)
from packages.persistence.acquisition import AcquisitionRepository
from packages.persistence.models import (
    IdentityReviewItemRow,
    PersonObservationLinkRow,
    PersonRow,
    SourceCheckpointRow,
)
from packages.rendering.gukgam_witness_claim import GukgamWitnessClaimError
from packages.rendering.gukgam_witness_review import load_current_gukgam_witness_documents
from tests.cli_support import cli_payload
from tests.test_gukgam_reviewed_plan_import import migrated_repository
from tests.test_gukgam_witness import ARTIFACT, capture, synthetic_packet
from workers.gukgam_witness_import import persist_capture


@pytest.fixture
def scenario(tmp_path):
    path = tmp_path / "witness-claim.db"
    repository = migrated_repository(path)
    persist_capture(repository, capture())
    with repository(read_only=True) as uow:
        document = load_current_gukgam_witness_documents(uow.acquisition)[0]
    person = Person(canonical_name="검토된 합성인물", identity_status=IdentityStatus.RESOLVED)
    other = Person(canonical_name="동명이인 합성후보", identity_status=IdentityStatus.RESOLVED)
    links = []
    with repository() as uow:
        uow.identity.add_person(person)
        uow.identity.add_person(other)
        uow._session.flush()
        for context in document.contexts:
            review_id = uuid4()
            uow._session.add(
                IdentityReviewItemRow(
                    id=str(review_id),
                    observation_id=str(context[0].id),
                    candidate_person_id=str(person.id),
                    reason_code="SYNTHETIC_IDENTITY_REVIEW",
                    details_json={},
                    status="RESOLVED",
                    created_at=datetime.now(UTC),
                    resolved_at=datetime.now(UTC),
                    resolution_note="SYNTHETIC ONLY; no real identity approval",
                )
            )
            link = PersonObservationLink(
                person_id=person.id,
                observation_id=context[0].id,
                action=MaterializationAction.REVIEWED_LINK,
                decision_class=MaterializationDecisionClass.REVIEWED_BRIDGE,
                review_item_id=review_id,
            )
            # Reviewed admin paths retain the exact review reference; the generic automatic
            # writer deliberately has no reviewed identity authority.
            uow._session.add(
                PersonObservationLinkRow(
                    id=str(link.id),
                    person_id=str(link.person_id),
                    observation_id=str(link.observation_id),
                    action=link.action.value,
                    decision_class=link.decision_class.value,
                    linked_at=link.linked_at,
                    superseded_at=None,
                    review_item_id=str(review_id),
                )
            )
            links.append(link)
        uow.commit()
    yield repository, path, person, other, document, links
    repository.close()


def prepare(scenario, index=0, **overrides):
    repository, _, person, _, document, _ = scenario
    observation = document.contexts[index][0]
    args = {
        "person_id": person.id,
        "observation_id": observation.id,
        "expected_observation_hash": observation.content_hash,
        "expected_packet_hash": document.packet.content_hash,
    }
    args.update(overrides)
    return repository.onboarding.prepare_gukgam_witness_claim(**args)


def cli_args(scenario):
    _, path, person, _, document, _ = scenario
    observation = document.contexts[0][0]
    return [
        "inspect",
        "gukgam-witness-claim",
        "--database-url",
        f"sqlite:///{path.as_posix()}",
        "--person-id",
        str(person.id),
        "--observation-id",
        str(observation.id),
        "--expected-observation-hash",
        observation.content_hash,
        "--expected-packet-hash",
        document.packet.content_hash,
    ]


@pytest.mark.parametrize("index", [0, 1, 2])
def test_source_listing_categories_exact_evidence_and_draft_public_boundary(scenario, index):
    repository, path, person, _, document, links = scenario
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    observation, snapshot, source, _ = document.contexts[index]
    result = prepare(scenario, index)
    assert prepare(scenario, index) == result
    claim, evidence = result.claim, result.evidence
    assert claim.person_id == person.id and claim.organization_id is None
    assert claim.publication_status.value == "DRAFT" and claim.epistemic_status.value == "CLAIM"
    assert not claim.asserted_as_true and claim.superseded_at is None
    assert claim.qualifiers["category"] == document.packet.rows[index].category
    assert claim.qualifiers["identity_link_id"] == str(links[index].id)
    assert claim.qualifiers["event_semantics"] == "OFFICIAL_SOURCE_LISTING_NOT_ACTUAL_ATTENDANCE"
    assert "organization_id" not in claim.qualifiers and "audit_date" not in claim.qualifiers
    assert evidence.claim_id == claim.id and evidence.feeder_observation_id == observation.id
    assert evidence.snapshot_id == snapshot.id and evidence.source_id == source.id
    assert evidence.excerpt is None and evidence.stance.value == "SUPPORT"
    assert claim.recorded_at == observation.recorded_at
    assert claim.valid_from.isoformat() == "2026-09-22T00:00:00+00:00"
    assert (
        claim.subject != claim.qualifiers["printed_name"]
    )  # reviewed bridge permits a supplied alias
    assert repository.claims(person.id) == []
    with TestClient(create_app(repository)) as client:
        assert client.get(f"/sources/{source.id}").status_code == 404
        # Existing resolved source-linked Persons may have an empty public profile. The new
        # in-memory pair must never enter its Claim projection or source reachability.
        public_claims = client.get(f"/people/{person.id}/claims")
        assert public_claims.status_code == 200 and public_claims.json() == []
        assert claim.predicate not in client.get(f"/people/{person.id}").text
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    if index == 0:
        assert "requested_datetime_text" not in claim.qualifiers
        assert "printed_affiliation_role" not in claim.qualifiers
        assert claim.qualifiers["printed_institution_group"] == "합성기관"
    else:
        assert claim.qualifiers["requested_datetime_text"] == "2026.10.6. 14:00"
        assert "printed_institution_group" not in claim.qualifiers


@pytest.mark.parametrize(
    "field", ["expected_observation_hash", "expected_packet_hash", "person_id", "observation_id"]
)
def test_explicit_inputs_fail_closed(scenario, field):
    with pytest.raises(GukgamWitnessClaimError):
        prepare(scenario, **{field: "0" * 64 if field.endswith("hash") else uuid4()})


@pytest.mark.parametrize(
    "change",
    [
        "unresolved_person",
        "superseded_person",
        "absent_link",
        "superseded_link",
        "automatic_link",
        "wrong_decision",
        "absent_review_reference",
        "open_review",
        "rejected_review",
        "wrong_review_person",
        "wrong_review_observation",
        "missing_resolution_time",
        "blank_review_note",
        "ambiguous_binding",
    ],
)
def test_reviewed_identity_gate_never_uses_name_or_context(scenario, change):
    repository, path, person, other, document, links = scenario
    with repository() as uow:
        stored_person = uow._session.get(PersonRow, str(person.id))
        link = uow._session.get(PersonObservationLinkRow, str(links[0].id))
        review = uow._session.get(IdentityReviewItemRow, str(links[0].review_item_id))
        if change == "unresolved_person":
            stored_person.identity_status = "REVIEW"
        elif change == "superseded_person":
            stored_person.superseded_at = datetime.now(UTC)
        elif change == "absent_link":
            uow._session.delete(link)
        elif change == "superseded_link":
            link.superseded_at = datetime.now(UTC)
        elif change == "automatic_link":
            link.action = "AUTO_LINK"
        elif change == "wrong_decision":
            link.decision_class = "EXACT_PROVIDER_IDENTITY"
        elif change == "absent_review_reference":
            link.review_item_id = None
        elif change == "open_review":
            review.status = "OPEN"
        elif change == "rejected_review":
            review.status = "REJECTED"
        elif change == "wrong_review_person":
            review.candidate_person_id = str(other.id)
        elif change == "wrong_review_observation":
            review.observation_id = str(document.contexts[1][0].id)
        elif change == "missing_resolution_time":
            review.resolved_at = None
        elif change == "blank_review_note":
            review.resolution_note = " "
        elif change == "ambiguous_binding":
            uow.identity.link_observation(
                PersonObservationLink(
                    person_id=other.id,
                    observation_id=document.contexts[0][0].id,
                    action=MaterializationAction.REVIEWED_LINK,
                    decision_class=MaterializationDecisionClass.REVIEWED_BRIDGE,
                )
            )
        uow.commit()
    before = path.read_bytes()
    with pytest.raises(GukgamWitnessClaimError):
        prepare(scenario)
    assert path.read_bytes() == before and repository.claims(person.id) == []


def test_replacement_bytes_require_current_observation_and_new_identity_review(scenario):
    repository, _, _, _, document, _ = scenario
    changed_artifact = ARTIFACT + b"replacement"
    raw = synthetic_packet()
    raw["attachment_sha256"] = hashlib.sha256(changed_artifact).hexdigest()
    persist_capture(repository, capture(raw, changed_artifact))
    with pytest.raises(GukgamWitnessClaimError, match="current selected"):
        prepare(scenario)
    with repository(read_only=True) as uow:
        current = load_current_gukgam_witness_documents(uow.acquisition)[0]
    observation = current.contexts[0][0]
    with pytest.raises(GukgamWitnessClaimError, match="unique active"):
        prepare(
            scenario,
            observation_id=observation.id,
            expected_observation_hash=observation.content_hash,
            expected_packet_hash=current.packet.content_hash,
        )
    assert current.packet.content_hash != document.packet.content_hash


def test_explicit_subset_excludes_old_reviewed_row_without_resurrection(scenario):
    repository, _, _, _, _, _ = scenario
    raw = synthetic_packet()
    raw["selection"] = "EXPLICIT_REVIEW_SUBSET"
    raw["rows"] = raw["rows"][1:]
    persist_capture(repository, capture(raw))
    with pytest.raises(GukgamWitnessClaimError, match="current selected"):
        prepare(scenario)


def test_failed_checkpoint_stops_preparation(scenario):
    repository, _, _, _, _, _ = scenario
    with repository() as uow:
        checkpoint = uow._session.query(SourceCheckpointRow).one()
        checkpoint.cursor = "invalid"
        uow.commit()
    with pytest.raises(ValueError, match="successful review"):
        prepare(scenario)


@pytest.mark.parametrize("change", ["duplicate", "wrong_context"])
def test_recovered_observation_provenance_cannot_be_silently_replaced(
    scenario, monkeypatch, change
):
    _, _, _, _, document, _ = scenario
    if change == "duplicate":
        observations = [context[0] for context in document.contexts]
        monkeypatch.setattr(
            AcquisitionRepository,
            "feeder_observations",
            lambda *args: observations + observations[:1],
        )
    else:
        contexts = {context[0].id: context for context in document.contexts}
        contexts[document.contexts[0][0].id] = document.contexts[1]
        monkeypatch.setattr(
            AcquisitionRepository, "feeder_observation_contexts", lambda *args: contexts
        )
    with pytest.raises(ValueError, match="duplicated|context differs"):
        prepare(scenario)


def test_cli_is_read_only_with_safe_stdout_and_no_network(scenario, monkeypatch, capsys):
    repository, path, _, _, document, _ = scenario
    before = path.read_bytes()
    monkeypatch.setattr("httpx.Client.send", lambda *a, **kw: pytest.fail("network request"))
    statements = []
    # Also prove the application UoW uses only SELECT statements against real migrated SQLite.
    event.listen(
        repository.engine,
        "before_cursor_execute",
        lambda connection, cursor, statement, *args: statements.append(statement),
    )
    assert prepare(scenario).to_dict()["claim_persisted"] is False
    assert all(sql.strip().upper().startswith(("SELECT", "BEGIN")) for sql in statements)
    assert main(cli_args(scenario)) == 0
    output = capsys.readouterr().out
    payload = cli_payload(output)
    assert payload["status"] == "DRAFT_PREPARED_IN_MEMORY"
    assert payload["attendance_state"] == "NOT_VERIFIED" and not payload["publication_approval"]
    for private in (
        "printed_name",
        "proposition",
        "source_section",
        "resolution_note",
        document.packet.rows[0].printed_name,
        "SYNTHETIC ONLY",
    ):
        assert private not in output
    assert path.read_bytes() == before


@pytest.mark.parametrize("verb", ["observe", "materialize", "publish", "review"])
def test_no_witness_claim_mutation_command(scenario, verb):
    args = cli_args(scenario)
    args[0] = verb
    with pytest.raises(SystemExit):
        parse_command(args)


def test_cli_failure_is_redacted_and_missing_database_is_not_created(scenario, tmp_path, capsys):
    args = cli_args(scenario)
    args[-1] = "0" * 64
    with pytest.raises(SystemExit):
        main(args)
    output = capsys.readouterr().out
    assert "COMMAND_FAILED" in output and "검토된" not in output
    missing = tmp_path / "missing.db"
    args[3] = f"sqlite:///{missing.as_posix()}"
    with pytest.raises(SystemExit):
        main(args)
    assert not missing.exists()


def test_claim_ids_separate_categories_and_shared_name_cell_role_rows(scenario):
    repository, _, _, _, _, _ = scenario
    assert len({prepare(scenario, i).claim.id for i in range(3)}) == 3
    raw = synthetic_packet()
    sibling = dict(raw["rows"][0])
    sibling.update(
        table_row_number=2,
        name_from_merged_cell=True,
        record_key=sibling["record_key"].removesuffix("row:1") + "row:2",
        printed_role="다른 합성역할",
    )
    raw["rows"].append(sibling)
    persist_capture(repository, capture(raw))
    with repository(read_only=True) as uow:
        document = load_current_gukgam_witness_documents(uow.acquisition)[0]
    with pytest.raises(GukgamWitnessClaimError, match="unique active"):
        prepare(
            scenario,
            observation_id=document.contexts[-1][0].id,
            expected_observation_hash=document.contexts[-1][0].content_hash,
            expected_packet_hash=document.packet.content_hash,
        )
    # A bridge for the first printed name cell never silently binds its second role row.

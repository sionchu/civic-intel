"""Reviewed links from no-Person-ID source rows (Gukgam witness, OpenDART) to a canonical Person.

One SQLite database carries all three real-shaped lanes: an ALIO-registered Person, an imported
committee witness list and an OpenDART executive-status enumeration.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from test_alio_organization_activation import commit_prepared, enumerated_repository
from test_batch_opendart_executives import FakeOpenDartProvider, enumerator
from test_gukgam_witness import ARTIFACT_BYTES, cli, payload

from apps.api.main import create_app
from packages.domain import db
from packages.domain.admin import AdminCommand
from packages.persistence.admin_workflow import AdminError
from packages.verification.person_record_links import (
    LINKED_WITNESS_PREDICATE,
    OPENDART_ROLE_PREDICATE,
    birth_year_month_conflict,
    listed_name,
    witness_institution_anchors,
)
from workers.gukgam_witness_claim_commit import main as witness_claim_main
from workers.gukgam_witness_import import main as witness_import_main

ACTOR = "test-reviewer"
REASON = "공식 증인 명단·공시 원문과 대상 인물의 기존 공식 기록을 직접 대조했습니다."


def command(action: str, *ids: Any, **kwargs: Any) -> AdminCommand:
    return AdminCommand(
        request_id=uuid4(),
        action=action,
        record_ids=tuple(UUID(str(item)) for item in ids),
        reason=REASON,
        **kwargs,
    )


def apply(repository, request: AdminCommand) -> dict:
    preview = repository.admin_preview(request)
    return repository.admin_commit(request, ACTOR, preview["state_hash"])


def link(repository, observation_id: str, person_id: str, bridge: tuple[str, ...]) -> dict:
    return apply(
        repository,
        command(
            "LINK_PERSON",
            observation_id,
            target_person_id=UUID(person_id),
            evidence_ids=tuple(UUID(item) for item in bridge),
            identity_basis="OFFICIAL_CAREER_CONTINUITY",
            human_verified=True,
        ),
    )


def witness_packet(tmp_path: Path) -> tuple[Path, Path]:
    raw = payload()
    first, second = raw["rows"][0], raw["rows"][1]
    # The institution head is listed by name, Hanja and the exact ALIO institution/title.
    first.update(name="김기관(金機關)", affiliation_title="테스트공기업 원장")
    # Same listed name, different institution: a homonym that must never link.
    second.update(name="김기관", affiliation_title="다른기관 이사장", target_institution=None)
    packet = tmp_path / "packet.json"
    packet.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    artifact = tmp_path / "list.pdf"
    artifact.write_bytes(ARTIFACT_BYTES)
    return packet, artifact


@pytest.fixture
def world(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    repository, _ = enumerated_repository(tmp_path / "links.db")
    commit_prepared(repository)
    database_url = str(repository.engine.url)

    queue = repository.admin_queue(state="ALL")["items"]
    alio_row = next(item for item in queue if item["fields"]["canonical_name"] == "김기관")
    registered = apply(
        repository, command("REGISTER_PERSON", alio_row["id"], human_verified=True)
    )["result"]["outcomes"][0]
    apply(repository, command("PUBLISH", registered["claim_id"]))
    bridge = tuple(str(item.id) for item in repository.evidence_for(UUID(registered["claim_id"])))

    packet, artifact = witness_packet(tmp_path)
    assert witness_import_main(cli(packet, artifact, "--database-url", database_url, "--commit")) == 0
    capsys.readouterr()
    base = [
        "--packet", str(packet), "--database-url", database_url,
        "--create-committee-organizations",
    ]
    assert witness_claim_main(base) == 0
    plan = json.loads(capsys.readouterr().out)
    assert witness_claim_main([*base, "--commit", "--expected-plan-sha256", plan["plan_sha256"]]) == 0
    capsys.readouterr()

    provider = FakeOpenDartProvider()
    provider.executives["00000001"]["list"][0]["nm"] = "김기관"  # type: ignore[index]
    assert enumerator(provider, repository).enumerate().run.status.value == "SUCCESS"

    yield {
        "repository": repository,
        "person_id": registered["person_id"],
        "bridge": bridge,
    }
    repository.engine.dispose()


def observation(repository, feeder: str, **match: Any) -> str:
    with repository.sessions() as session:
        rows = session.scalars(
            select(db.FeederObservationRow).where(db.FeederObservationRow.feeder == feeder)
        ).all()
    found = [
        row.id
        for row in rows
        if all(row.normalized_json.get(key) == value for key, value in match.items())
    ]
    assert len(found) == 1, found
    return found[0]


def counts(repository) -> dict[str, int]:
    with repository.sessions() as session:
        return {
            model.__tablename__: session.scalar(select(func.count()).select_from(model))
            for model in (db.PersonRow, db.ClaimRow, db.PersonObservationLinkRow)
        }


def test_pure_anchor_rules() -> None:
    assert listed_name("이선영(李宣姈)") == "이선영"
    assert listed_name(" 김기관 ") == "김기관"
    assert birth_year_month_conflict(date(1975, 4, 9), "1975년 04월") is False
    assert birth_year_month_conflict(date(1980, 1, 1), "1975년 04월") is True
    assert birth_year_month_conflict(None, "1975년 04월") is False
    assert birth_year_month_conflict(date(1980, 1, 1), "") is False
    assert witness_institution_anchors(
        {"affiliation_title": "테스트공기업 원장"}, ["테스트공기업", "다른기관"]
    ) == ("테스트공기업",)
    assert witness_institution_anchors({"target_institution": "다른기관"}, ["다른기관"]) == (
        "다른기관",
    )
    assert witness_institution_anchors({"affiliation_title": "주식회사 갑 대표"}, ["갑"]) == ()


def test_reviewed_witness_and_dart_rows_reach_one_public_profile_with_provenance(world) -> None:
    repository, person_id, bridge = world["repository"], world["person_id"], world["bridge"]
    witness_id = observation(repository, "gukgam_reviewed_witness", row_number=1)
    dart_id = observation(repository, "opendart_disclosed_executives", canonical_name="김기관")

    before = counts(repository)
    witness = link(repository, witness_id, person_id, bridge)["result"]["outcomes"][0]
    assert witness["identity_action"] == "REVIEWED_LINK"
    assert witness["institution_anchors"] == ["테스트공기업"]
    dart = link(repository, dart_id, person_id, bridge)["result"]["outcomes"][0]
    after = counts(repository)
    assert after["people"] == before["people"]
    assert after["person_observation_links"] == before["person_observation_links"] + 2

    # Linked Claims are DRAFT source-attributed CLAIMs; nothing is public before PUBLISH.
    with TestClient(create_app(repository)) as client:
        profile = client.get(f"/people/{person_id}").json()
        witnesses = client.get("/gukgam/2026/witnesses").json()
    section_ids = {section["id"] for section in profile["profile"]["sections"]}
    assert "gukgam_2026" not in section_ids and "corporate_roles" not in section_ids
    assert not any("linked_person" in item for item in witnesses["items"])

    for claim_id in (witness["claim_id"], dart["claim_id"]):
        apply(repository, command("PUBLISH", claim_id))

    with TestClient(create_app(repository)) as client:
        profile = client.get(f"/people/{person_id}").json()
        witnesses = client.get("/gukgam/2026/witnesses").json()
        sections = {section["id"]: section for section in profile["profile"]["sections"]}
        assert ["identity", "gukgam_2026", "public_institution_roles", "corporate_roles"] == [
            item for item in profile["profile"]["section_order"][:4]
        ]
        gukgam = sections["gukgam_2026"]["entries"][0]
        assert gukgam["epistemic_status"] == "CLAIM"
        assert gukgam["details"]["affiliation_title"] == "테스트공기업 원장"
        assert gukgam["details"]["category"] == "증인"
        assert "request_reason_text" not in json.dumps(profile, ensure_ascii=False)
        corporate = sections["corporate_roles"]["entries"][0]
        assert corporate["details"]["corp_name"] == "알파테크"
        assert corporate["details"]["receipt_no"] == "20260831000001"
        assert corporate["details"]["reported_main_career_semantics"] == (
            "company_disclosed_not_independently_verified"
        )
        assert "birth_year_month" not in corporate["details"]
        # Claim -> Evidence -> Source stays unbroken and each source is publicly readable.
        for entry in (gukgam, corporate):
            stances = {item["stance"] for item in entry["evidence"]}
            assert stances == {"SUPPORT", "NEUTRAL"}
            support = next(item for item in entry["evidence"] if item["stance"] == "SUPPORT")
            assert support["feeder_observation_id"] in {witness_id, dart_id}
            for source_id in entry["source_ids"]:
                assert client.get(f"/sources/{source_id}").status_code == 200

    linked_rows = [item for item in witnesses["items"] if "linked_person" in item]
    assert len(linked_rows) == 1
    assert linked_rows[0]["linked_person"] == {"id": person_id, "name": "김기관"}
    assert linked_rows[0]["name"] == "김기관(金機關)"
    homonym = next(item for item in witnesses["items"] if item["affiliation_title"] == "다른기관 이사장")
    assert "linked_person" not in homonym

    # Re-running the same review never duplicates a link or a Claim.
    snapshot = counts(repository)
    for observation_id in (witness_id, dart_id):
        with pytest.raises(AdminError) as error:
            link(repository, observation_id, person_id, bridge)
        assert error.value.code == "ALREADY_LINKED"
    assert counts(repository) == snapshot


def test_same_name_without_institution_anchor_is_refused(world) -> None:
    repository = world["repository"]
    homonym = observation(repository, "gukgam_reviewed_witness", row_number=2)
    before = counts(repository)
    with pytest.raises(AdminError) as error:
        link(repository, homonym, world["person_id"], world["bridge"])
    assert error.value.code == "WITNESS_INSTITUTION_ANCHOR_REQUIRED"
    assert counts(repository) == before


def test_name_mismatch_and_birth_year_month_conflict_are_refused(world) -> None:
    repository, person_id, bridge = world["repository"], world["person_id"], world["bridge"]
    other_name = observation(repository, "opendart_disclosed_executives", canonical_name="이사외")
    with pytest.raises(AdminError) as error:
        link(repository, other_name, person_id, bridge)
    assert error.value.code == "IDENTITY_CONFLICT"

    with repository.sessions() as session:
        session.get(db.PersonRow, person_id).birth_date = date(1980, 1, 1)
        session.commit()
    dart_id = observation(repository, "opendart_disclosed_executives", canonical_name="김기관")
    before = counts(repository)
    with pytest.raises(AdminError) as error:
        link(repository, dart_id, person_id, bridge)
    assert error.value.code == "BIRTH_YEAR_MONTH_CONFLICT"
    assert counts(repository) == before


def test_bridge_must_come_from_the_target_persons_own_records(world) -> None:
    repository = world["repository"]
    stranger = str(uuid4())
    with repository.sessions() as session:
        source_person = session.get(db.PersonRow, world["person_id"])
        session.add(
            db.PersonRow(
                id=stranger,
                canonical_name="김기관",
                birth_date=None,
                identity_status="RESOLVED",
                valid_from=source_person.valid_from,
                valid_to=None,
                recorded_at=source_person.recorded_at,
                superseded_at=None,
            )
        )
        session.commit()
    witness_id = observation(repository, "gukgam_reviewed_witness", row_number=1)
    with pytest.raises(AdminError) as error:
        link(repository, witness_id, stranger, world["bridge"])
    assert error.value.code == "BRIDGE_NOT_TARGET_RECORD"


def test_no_person_id_rows_cannot_register_a_new_person(world) -> None:
    repository = world["repository"]
    dart_id = observation(repository, "opendart_disclosed_executives", canonical_name="박대표")
    with pytest.raises(AdminError) as error:
        apply(repository, command("REGISTER_PERSON", dart_id, human_verified=True))
    assert error.value.code == "SOURCE_RECORD_LINK_ONLY"


def test_withdrawn_witness_list_row_withholds_the_person_claim(world) -> None:
    repository, person_id, bridge = world["repository"], world["person_id"], world["bridge"]
    witness_id = observation(repository, "gukgam_reviewed_witness", row_number=1)
    linked = link(repository, witness_id, person_id, bridge)["result"]["outcomes"][0]
    apply(repository, command("PUBLISH", linked["claim_id"]))
    source_claim_id = next(
        claim.qualifiers["source_claim_id"]
        for claim in repository.claims(person_id=UUID(person_id))
        if claim.predicate == LINKED_WITNESS_PREDICATE
    )
    withdrawn = apply(repository, command("WITHDRAW", source_claim_id))["result"]["outcomes"][0]
    assert withdrawn["dependent_person_claims_withheld"] == [linked["claim_id"]]
    with TestClient(create_app(repository)) as client:
        profile = client.get(f"/people/{person_id}").json()
    assert "gukgam_2026" not in {section["id"] for section in profile["profile"]["sections"]}
    # Re-publishing the Person Claim is refused while its source row is withdrawn.
    with pytest.raises(AdminError) as error:
        apply(repository, command("PUBLISH", linked["claim_id"]))
    assert error.value.code == "WITNESS_CLAIM_REQUIRED"
    assert OPENDART_ROLE_PREDICATE not in {
        claim.predicate for claim in repository.claims(person_id=UUID(person_id))
    }


def test_candidate_report_is_read_only_and_needs_a_second_anchor(world) -> None:
    from workers.person_link_candidates import build_person_link_candidate_report

    repository = world["repository"]
    before = counts(repository)
    report = build_person_link_candidate_report(repository)
    assert counts(repository) == before
    assert report["write_performed"] is False
    witness = report["summary"]["gukgam_witness"]
    assert witness["candidates"] == 1 and witness["link_ready"] == 1
    assert witness["exact_name_only_not_a_candidate"] == 1
    (candidate,) = [item for item in report["candidates"] if item["lane"] == "GUKGAM_WITNESS"]
    assert candidate["anchors"] == ["EXACT_LISTED_NAME", "INSTITUTION:테스트공기업"]
    assert candidate["person_records"][0]["bridge_evidence_ids"] == sorted(world["bridge"])
    assert "request_reason_text" not in json.dumps(report, ensure_ascii=False)
    # Birth unknown and company absent from the source-reported career: name-only, no candidate.
    assert report["summary"]["opendart_executive"]["exact_name_only_not_a_candidate"] == 1
    assert report == build_person_link_candidate_report(repository)

    with repository.sessions() as session:
        session.get(db.PersonRow, world["person_id"]).birth_date = date(1975, 4, 9)
        session.commit()
    agreeing = build_person_link_candidate_report(repository, lanes=("opendart",))
    (dart,) = agreeing["candidates"]
    assert dart["anchors"] == ["EXACT_NAME", "BIRTH_YEAR_MONTH_AGREES"]
    assert dart["blocked_reasons"] == []

    with repository.sessions() as session:
        session.get(db.PersonRow, world["person_id"]).birth_date = date(1980, 1, 1)
        session.commit()
    conflicting = build_person_link_candidate_report(repository, lanes=("opendart",))
    assert conflicting["candidates"] == []
    assert conflicting["summary"]["opendart_executive"]["birth_year_month_conflict_refused"] == 1

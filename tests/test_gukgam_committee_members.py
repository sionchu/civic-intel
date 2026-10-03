from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from test_assembly_base_profile import member_row, migrated_repository
from test_gukgam_reviewed_claim_import import (
    commit_packet,
    insert_organization,
    packet_payload,
)

import packages.rendering.gukgam_committee_members as projection_module
from apps.api.main import create_app
from packages.connectors.open_assembly import OpenAssemblyMemberConnector
from packages.domain.contracts import Claim, ClaimEvidence, Person
from packages.domain.enums import EpistemicStatus, EvidenceStance, IdentityStatus, PublicationStatus
from packages.rendering.gukgam_committee_members import (
    GUKGAM_COMMITTEE_MEMBERS_SEMANTICS,
    GukgamCommitteeMembersError,
    build_gukgam_committee_members_projection,
)
from packages.rendering.gukgam_organization_claim import (
    GukgamAuditTargetProjection,
    GukgamAuditTargetProjectionItem,
)
from packages.verification.assembly_base_profile import AssemblyBaseProfilePublisher
from workers.assembly_roster import AssemblyRosterEnumerator
from workers.gukgam_reviewed_claim_import import main


class MultiRowRoster:
    def __init__(self, rows: list[dict[str, str]]) -> None:
        self.rows = rows

    def handle(self, request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                OpenAssemblyMemberConnector.API_CODE: [
                    {"head": [{"list_total_count": len(self.rows)}]},
                    {"row": self.rows},
                ]
            },
        )

    def connector(self) -> OpenAssemblyMemberConnector:
        return OpenAssemblyMemberConnector(
            api_key="committee-members-test-secret",
            page_size=100,
            transport=httpx.MockTransport(self.handle),
        )


def test_committee_endpoint_lists_claim_backed_members_of_target_committees(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = migrated_repository(tmp_path / "committees.db")
    database_url = f"sqlite:///{(tmp_path / 'committees.db').as_posix()}"
    raw = packet_payload()
    committee = raw["source"]["committee_name"]
    review_key = commit_packet(repository, raw)
    organization_id = insert_organization(repository, raw["schedule"][0]["audited_targets"][0])
    assert main(
        [
            "--database-url", database_url,
            "--organization-id", str(organization_id),
            "--review-key", review_key,
            "--commit",
        ]
    ) == 0
    capsys.readouterr()

    roster = MultiRowRoster(
        [
            member_row("M-001", "나회원", party="가정당", committees=f"{committee}, 국방위원회"),
            member_row("M-002", "가회원", party="나정당", committees=f"국방위원회,{committee}"),
            member_row("M-003", "다회원", committees="국방위원회"),
            member_row("M-004", "라회원", committees="기획재정위원회"),
        ]
    )
    AssemblyRosterEnumerator(roster.connector(), repository).enumerate_and_materialize()
    AssemblyBaseProfilePublisher(repository).publish_latest_successful()

    with TestClient(create_app(repository)) as client:
        response = client.get("/gukgam/2026/committees")
        assert response.status_code == 200
        payload = response.json()
        targets = client.get("/gukgam/2026/targets").json()
        people = {item["canonical_name"]: item["id"] for item in client.get("/people").json()}
        member_claims = {
            claim["id"]: claim
            for claim in client.get(f"/people/{people['가회원']}/claims").json()
        }

    assert payload["semantics"] == GUKGAM_COMMITTEE_MEMBERS_SEMANTICS
    assert payload["roster_semantics"] == "MEMBER_ROSTER_SNAPSHOT_NOT_AUDIT_DAY_ATTENDANCE"
    assert payload["year"] == 2026
    assert payload["committee_count"] == 1
    only = payload["committees"][0]
    assert only["committee_name"] == committee
    assert only["target_count"] == targets["target_count"] == 1
    assert only["member_count"] == 2
    assert [member["person"]["name"] for member in only["members"]] == ["가회원", "나회원"]
    assert [member["party"] for member in only["members"]] == ["나정당", "가정당"]

    first = only["members"][0]
    assert first["person"]["id"] == people["가회원"]
    claim = member_claims[first["claim_id"]]
    assert claim["predicate"] == "ASSEMBLY_COMMITTEES"
    assert first["epistemic_status"] == claim["epistemic_status"]
    assert set(first["evidence_ids"]) == {item["id"] for item in claim["evidence"]}
    assert set(first["source_ids"]) == set(claim["source_ids"])
    assert member_claims[first["party_claim_id"]]["predicate"] == "ASSEMBLY_PARTY"

    serialized = json.dumps(payload, ensure_ascii=False)
    assert "다회원" not in serialized  # other committee only
    assert "라회원" not in serialized  # old committee name is never merged
    assert "국방위원회" not in serialized  # no committee without a published target claim
    assert any("audit-day attendance" in text for text in payload["limitations"])
    assert any("questioned" in text for text in payload["limitations"])
    for forbidden in ("score", "rank", "confidence", "normalized", "review_key"):
        assert forbidden not in serialized

    with TestClient(create_app(repository)) as client:
        ontology = client.get(f"/ontology/people/{people['가회원']}").json()
    committee_edges = [e for e in ontology["edges"] if e["relation_type"] == "SERVED_ON"]
    assert {
        node["label"]
        for node in ontology["nodes"]
        if node["kind"] == "COMMITTEE"
    } == {"국방위원회", committee}
    assert {edge["claim_id"] for edge in committee_edges} == {first["claim_id"]}


def test_committee_endpoint_is_empty_without_published_targets(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "empty.db")
    with TestClient(create_app(repository)) as client:
        response = client.get("/gukgam/2026/committees")
    assert response.status_code == 200
    assert response.json()["committees"] == []
    assert response.json()["committee_count"] == 0


# --- pure projection --------------------------------------------------------------------

COMMITTEE = "국방위원회"


def _targets() -> GukgamAuditTargetProjection:
    ids = (uuid4(),)
    item = GukgamAuditTargetProjectionItem(
        organization_id=uuid4(),
        organization_name="테스트기관",
        committee_name=COMMITTEE,
        audit_date="2026-10-14",
        time_text=None,
        venue=None,
        section="국방부",
        page_number=1,
        source_published_date="2026-09-20",
        claim_id=uuid4(),
        evidence_ids=ids,
        source_ids=ids,
        snapshot_ids=ids,
        observation_ids=ids,
    )
    return GukgamAuditTargetProjection(year=2026, items=(item,))


def _person(name: str, status: IdentityStatus = IdentityStatus.RESOLVED) -> Person:
    return Person(id=uuid4(), canonical_name=name, identity_status=status)


def _claim(person: Person, predicate: str, text: str, **overrides) -> tuple[Claim, ClaimEvidence]:
    field = {"ASSEMBLY_COMMITTEES": "committees", "ASSEMBLY_PARTY": "party"}[predicate]
    claim = Claim(
        id=uuid4(),
        person_id=person.id,
        proposition=f"{person.canonical_name} {text}",
        subject=person.canonical_name,
        predicate=predicate,
        object_text=text,
        qualifiers=overrides.pop(
            "qualifiers", {"source_contract": "assembly_member_roster", "field_name": field}
        ),
        epistemic_status=EpistemicStatus.FACT,
        publication_status=overrides.pop("publication_status", PublicationStatus.PUBLISHED),
        asserted_as_true=True,
        valid_from=datetime(2026, 9, 1, tzinfo=UTC),
        **overrides,
    )
    evidence = ClaimEvidence(
        id=uuid4(), claim_id=claim.id, source_id=uuid4(), stance=EvidenceStance.SUPPORT
    )
    return claim, evidence


def _context(*pairs: tuple[Claim, ClaimEvidence]):
    return (
        tuple(claim for claim, _ in pairs),
        {claim.id: (evidence,) for claim, evidence in pairs},
    )


@pytest.fixture
def open_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        projection_module,
        "validate_claim_publication",
        lambda *args, **kwargs: SimpleNamespace(publishable=True, failures=()),
    )


def _build(people, contexts):
    return build_gukgam_committee_members_projection(
        _targets(), people, contexts, sources={}, policies={}
    ).to_dict()


def test_projection_requires_resolved_people_and_exact_committee_names(
    open_gate: None,
) -> None:
    member = _person("가회원")
    review = _person("나회원", IdentityStatus.REVIEW)
    renamed = _person("다회원")
    contexts = {
        member.id: _context(
            _claim(member, "ASSEMBLY_COMMITTEES", f"운영위원회, {COMMITTEE} "),
            _claim(member, "ASSEMBLY_PARTY", "테스트정당"),
        ),
        review.id: _context(_claim(review, "ASSEMBLY_COMMITTEES", COMMITTEE)),
        renamed.id: _context(_claim(renamed, "ASSEMBLY_COMMITTEES", "기획재정위원회")),
    }

    payload = _build([member, review, renamed], contexts)

    assert [c["committee_name"] for c in payload["committees"]] == [COMMITTEE]
    members = payload["committees"][0]["members"]
    assert [m["person"]["name"] for m in members] == ["가회원"]
    assert members[0]["party"] == "테스트정당"


def test_projection_ignores_unpublished_and_party_may_be_absent(open_gate: None) -> None:
    draft = _person("가회원")
    no_party = _person("나회원")
    contexts = {
        draft.id: _context(
            _claim(draft, "ASSEMBLY_COMMITTEES", COMMITTEE, publication_status=PublicationStatus.DRAFT)
        ),
        no_party.id: _context(_claim(no_party, "ASSEMBLY_COMMITTEES", COMMITTEE)),
    }

    members = _build([draft, no_party], contexts)["committees"][0]["members"]

    assert [m["person"]["name"] for m in members] == ["나회원"]
    assert members[0]["party"] is None and members[0]["party_claim_id"] is None


def test_projection_skips_claims_failing_the_publication_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        projection_module,
        "validate_claim_publication",
        lambda *args, **kwargs: SimpleNamespace(publishable=False, failures=("x",)),
    )
    member = _person("가회원")
    contexts = {member.id: _context(_claim(member, "ASSEMBLY_COMMITTEES", COMMITTEE))}

    assert _build([member], contexts)["committees"][0]["members"] == []


@pytest.mark.parametrize(
    "qualifiers",
    [
        {"source_contract": "unrelated", "field_name": "committees"},
        {"source_contract": "assembly_member_roster", "field_name": "party"},
    ],
)
def test_projection_fails_closed_on_unexpected_roster_contract(
    open_gate: None, qualifiers: dict[str, str]
) -> None:
    member = _person("가회원")
    contexts = {
        member.id: _context(_claim(member, "ASSEMBLY_COMMITTEES", COMMITTEE, qualifiers=qualifiers))
    }

    with pytest.raises(GukgamCommitteeMembersError, match="invalid source contract"):
        _build([member], contexts)

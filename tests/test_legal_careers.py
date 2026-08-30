import json
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from packages.connectors.legal_personnel_records import (
    moj_prosecution_personnel_policy,
    parse_moj_prosecution_rows,
    parse_supreme_court_rows,
    supreme_court_personnel_policy,
)
from packages.domain.contracts import LegalCareerEpisode
from packages.domain.enums import LegalCareerEventType, LegalCareerType
from packages.verification.identity import IdentityStatus, resolve_identity
from workers.legal_careers import (
    render_legal_career_json,
    stage_judicial_rows,
    stage_prosecution_rows,
)

FIXTURE = Path(__file__).parent / "fixtures" / "legal_personnel.json"


def fixture() -> dict[str, list[dict]]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_legal_personnel_policies_fail_closed_for_live_collection_and_commercial_reuse() -> None:
    for policy in (moj_prosecution_personnel_policy(), supreme_court_personnel_policy()):
        assert policy.can_store_metadata
        assert not policy.can_fetch
        assert not policy.can_store_fulltext
        assert not policy.can_send_to_ai
        assert not policy.can_commercialize


def test_prosecutor_events_preserve_transfer_and_new_appointment_semantics() -> None:
    records = parse_moj_prosecution_rows(fixture()["prosecution"])
    assert [item.event_type for item in records] == [
        LegalCareerEventType.TRANSFER,
        LegalCareerEventType.APPOINTMENT,
    ]
    assert records[0].career_type == LegalCareerType.PROSECUTOR
    assert records[1].career_type == LegalCareerType.CHIEF_PROSECUTOR
    assert records[1].public_assignment_domain == "형사부"


def test_judicial_events_keep_court_president_judge_and_administration_distinct() -> None:
    records = parse_supreme_court_rows(fixture()["judiciary"])
    assert [item.career_type for item in records] == [
        LegalCareerType.COURT_PRESIDENT,
        LegalCareerType.JUDGE,
        LegalCareerType.JUDICIAL_ADMINISTRATION,
    ]
    assert records[0].event_date == date(2026, 2, 9)
    assert records[1].event_date == date(2026, 2, 23)


def test_staged_legal_records_are_identity_candidates_with_dated_career_anchors() -> None:
    staged = stage_prosecution_rows(fixture()["prosecution"])
    candidate = staged[0].candidate
    assert candidate.canonical_name == "김검사"
    assert candidate.organization == "부산지방검찰청"
    assert "legal_personnel_date:2026-08-31" in candidate.career_anchors
    assert resolve_identity(candidate, candidate).status == IdentityStatus.RESOLVED


def test_output_does_not_expose_private_fields_or_infer_case_responsibility_or_ideology() -> None:
    rendered = render_legal_career_json(fixture()["prosecution"], fixture()["judiciary"])
    assert "010-0000-0000" not in rendered
    assert "수집금지 주소" not in rendered
    assert '"client"' not in rendered.casefold()
    assert '"ideology"' not in rendered.casefold()
    assert '"case_outcome"' not in rendered.casefold()
    assert "사건 전체에 대한 개인 책임" in rendered
    assert "정치성향" in rendered


def test_legal_career_contract_requires_source_and_rejects_ideology_or_client_fields() -> None:
    kwargs = {
        "person_id": uuid4(),
        "organization_id": uuid4(),
        "career_type": LegalCareerType.JUDGE,
        "event_type": LegalCareerEventType.TRANSFER,
        "title": "부장판사",
        "event_date": date(2026, 2, 23),
        "valid_from": datetime(2026, 2, 23, tzinfo=UTC),
        "source_ids": [uuid4()],
    }
    episode = LegalCareerEpisode(**kwargs)
    assert episode.career_type == LegalCareerType.JUDGE

    with pytest.raises(ValidationError):
        LegalCareerEpisode(**(kwargs | {"source_ids": []}))
    with pytest.raises(ValidationError):
        LegalCareerEpisode(**kwargs, ideology_score=0.8)
    with pytest.raises(ValidationError):
        LegalCareerEpisode(**kwargs, client_names=["비공개 의뢰인"])


def test_law_firm_affiliation_lane_cannot_generate_client_or_political_relationships_in_this_stage() -> None:
    staged = stage_judicial_rows(fixture()["judiciary"])[0].to_dict()
    serialized = json.dumps(staged, ensure_ascii=False)
    assert "client_names" not in serialized
    assert "political_relationship" not in serialized
    assert "faction" not in serialized

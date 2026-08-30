import json
from pathlib import Path

from packages.connectors.labor_union_records import (
    nationwide_labor_union_policy,
    parse_labor_union_rows,
)
from packages.verification.identity import IdentityStatus, resolve_identity
from workers.labor_leadership import render_labor_union_json, stage_labor_union_rows

FIXTURE = Path(__file__).parent / "fixtures" / "labor_unions.json"


def fixture() -> list[dict]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_labor_union_policy_is_metadata_only_and_live_collection_fail_closed() -> None:
    policy = nationwide_labor_union_policy()
    assert policy.domain == "data.go.kr"
    assert policy.can_store_metadata
    assert not policy.can_fetch
    assert not policy.can_store_fulltext
    assert not policy.can_send_to_ai
    assert not policy.can_commercialize


def test_union_organization_facts_are_separate_from_person_candidate() -> None:
    records = parse_labor_union_rows(fixture())
    assert records[0].union_name == "테스트공사노동조합"
    assert records[0].affiliated_federation == "한국노동조합총연맹"
    assert records[0].membership_count == 500
    assert records[0].workplace_name == "테스트공사"

    staged = stage_labor_union_rows(fixture())
    candidate = staged[0].leadership_candidate
    assert candidate is not None
    assert candidate.canonical_name == "김노동"
    assert candidate.organization == "테스트공사노동조합"
    assert candidate.office == "대표자(전국노동조합표준데이터)"
    assert resolve_identity(candidate, candidate).status == IdentityStatus.RESOLVED


def test_masked_or_missing_representative_never_creates_person_candidate() -> None:
    staged = stage_labor_union_rows(fixture())
    assert staged[1].leadership_candidate is None
    assert staged[2].leadership_candidate is None


def test_membership_count_remains_organization_level_only() -> None:
    payload = stage_labor_union_rows(fixture())[0].to_dict()
    assert payload["organization"]["membership_count"] == 500
    assert payload["organization"]["membership_count_semantics"] == "ORGANIZATION_LEVEL_ONLY"
    assert "membership_count" not in payload["leadership_candidate"]


def test_private_location_contact_and_member_roster_fields_never_reach_output() -> None:
    rendered = render_labor_union_json(fixture())
    assert "수집금지 주소" not in rendered
    assert "수집금지 지번" not in rendered
    assert "02-0000-0000" not in rendered
    assert "37.0000" not in rendered
    assert "127.0000" not in rendered
    assert "일반조합원A" not in rendered
    assert "일반조합원B" not in rendered


def test_leadership_evidence_does_not_infer_ordinary_membership_or_political_alignment() -> None:
    rendered = render_labor_union_json(fixture())
    assert "일반 조합원 여부" in rendered
    assert "정치성향" in rendered
    assert '"party"' not in rendered.casefold()
    assert '"faction"' not in rendered.casefold()
    assert '"member_names"' not in rendered.casefold()

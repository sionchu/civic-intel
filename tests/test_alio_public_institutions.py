import json
from pathlib import Path

from packages.connectors.alio_disclosures import (
    alio_public_institution_policy,
    parse_compensation_rows,
    parse_executive_rows,
    parse_institution_rows,
    parse_reemployment_rows,
)
from packages.domain.enums import (
    PublicInstitutionClassification,
    PublicInstitutionExecutiveKind,
)
from packages.verification.identity import IdentityStatus, resolve_identity
from workers.public_institutions import (
    render_public_institution_json,
    stage_executive_rows,
    stage_reemployment_rows,
)

FIXTURE = Path(__file__).parent / "fixtures" / "alio_public_institution.json"


def fixture() -> dict[str, list[dict]]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_alio_policy_is_reviewed_but_live_fetch_stays_disabled() -> None:
    policy = alio_public_institution_policy()
    assert policy.domain == "alio.go.kr"
    assert policy.can_store_metadata
    assert policy.can_commercialize
    assert not policy.can_fetch
    assert not policy.can_store_fulltext
    assert not policy.can_send_to_ai


def test_public_institution_classifications_remain_distinct() -> None:
    records = parse_institution_rows(fixture()["institutions"])
    assert [item.classification for item in records] == [
        PublicInstitutionClassification.PUBLIC_CORPORATION,
        PublicInstitutionClassification.QUASI_GOVERNMENT,
        PublicInstitutionClassification.OTHER_PUBLIC_INSTITUTION,
    ]


def test_executive_staging_preserves_term_selection_and_reported_career_semantics() -> None:
    rows = fixture()["executives"]
    records = parse_executive_rows(rows)
    staged = stage_executive_rows(rows)

    assert records[0].executive_kind == PublicInstitutionExecutiveKind.INSTITUTION_HEAD
    assert records[0].term_start.isoformat() == "2025-03-12"
    assert records[0].term_end is not None
    assert records[0].selection_procedure is not None
    assert records[0].reported_careers == ("테스트부 차관", "테스트청장")

    candidate = staged[0].candidate
    assert candidate.canonical_name == "김기관"
    assert candidate.organization == "테스트공기업"
    assert "alio_institution_code:ALIO-C001" in candidate.career_anchors
    assert resolve_identity(candidate, candidate).status == IdentityStatus.RESOLVED

    rendered = json.dumps(staged[0].to_dict(), ensure_ascii=False)
    assert "독립적으로 검증한 사실과는 구분" in rendered
    assert "정치적 임명" in rendered
    assert "02-1111-1111" not in rendered


def test_compensation_is_role_category_disclosure_not_personal_wealth() -> None:
    records = parse_compensation_rows(fixture()["compensation"])
    assert records[0].executive_kind == PublicInstitutionExecutiveKind.INSTITUTION_HEAD
    assert records[0].total_thousand_krw == 210000

    data = json.loads(
        render_public_institution_json(
            fixture()["institutions"],
            fixture()["executives"],
            fixture()["compensation"],
            fixture()["reemployment"],
        )
    )
    compensation = data["compensation"][0]
    assert compensation["person_id"] is None
    assert compensation["person_attribution"] == "ROLE_CATEGORY_ONLY"
    assert "wealth" not in json.dumps(compensation).casefold()


def test_general_employee_reemployment_never_creates_person_candidate() -> None:
    records = parse_reemployment_rows(fixture()["reemployment"])
    staged = stage_reemployment_rows(fixture()["reemployment"])

    assert records[0].executive_person_scope
    assert staged[0].candidate is not None
    assert staged[0].candidate.canonical_name == "최퇴직"

    assert not records[1].executive_person_scope
    assert records[1].person_name is None
    assert staged[1].candidate is None
    assert staged[1].to_dict()["identity_semantics"] == "NON_EXECUTIVE_OR_NAME_NOT_STAGED"

    assert records[2].person_name is None
    assert staged[2].candidate is None


def test_reemployment_is_not_confused_with_ethics_review_or_wrongdoing() -> None:
    staged = stage_reemployment_rows(fixture()["reemployment"])[0]
    payload = json.dumps(staged.to_dict(), ensure_ascii=False)

    assert "실제 재취업 현황" in payload
    assert "취업심사 결정과는 별도 사건" in payload
    assert "자동 판정하지 않는다" in payload
    assert '"decision"' not in payload


def test_private_contact_and_location_fields_do_not_reach_review_output() -> None:
    rendered = render_public_institution_json(
        fixture()["institutions"],
        fixture()["executives"],
        fixture()["compensation"],
        fixture()["reemployment"],
    )
    assert "수집하지 않을 주소" not in rendered
    assert "02-0000-0000" not in rendered
    assert "02-1111-1111" not in rendered
    assert "010-1234-5678" not in rendered
    assert "일반직원" not in rendered

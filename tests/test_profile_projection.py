from datetime import UTC, datetime
from uuid import UUID, uuid5

import pytest

from packages.domain.contracts import Claim, ClaimEvidence, Person
from packages.domain.enums import (
    EpistemicStatus,
    EvidenceStance,
    IdentityStatus,
    PublicationStatus,
)
from packages.rendering.profile_projection import SECTION_DEFINITIONS, build_profile_projection

PERSON_ID = UUID("00000000-0000-0000-0000-000000000099")
CLAIM_ID = UUID("30000000-0000-0000-0000-000000000099")
EVIDENCE_ID = UUID("40000000-0000-0000-0000-000000000099")
SOURCE_ID = UUID("20000000-0000-0000-0000-000000000099")


def person() -> Person:
    return Person(
        id=PERSON_ID,
        canonical_name="김프로필",
        identity_status=IdentityStatus.RESOLVED,
    )


def nomination_claim() -> Claim:
    return Claim(
        id=CLAIM_ID,
        person_id=PERSON_ID,
        proposition="김프로필은 위원장 후보자로 지명됐다.",
        subject="김프로필",
        predicate="NOMINATED_AS",
        object_text="위원장 후보자",
        qualifiers={"date": "2026-08-30"},
        epistemic_status=EpistemicStatus.FACT,
        publication_status=PublicationStatus.PUBLISHED,
        asserted_as_true=True,
    )


def nomination_evidence() -> ClaimEvidence:
    return ClaimEvidence(
        id=EVIDENCE_ID,
        claim_id=CLAIM_ID,
        source_id=SOURCE_ID,
        stance=EvidenceStance.SUPPORT,
        excerpt="projection must not copy this excerpt",
    )


def section(profile: dict, section_id: str) -> dict:
    return next(item for item in profile["sections"] if item["id"] == section_id)


def test_declared_asset_section_requires_validated_rows_and_exact_evidence() -> None:
    from packages.verification.assembly_asset_import import ASSEMBLY_ASSET_TOTAL_PREDICATE

    claim = nomination_claim().model_copy(
        update={
            "predicate": ASSEMBLY_ASSET_TOTAL_PREDICATE,
            "epistemic_status": EpistemicStatus.CLAIM,
            "asserted_as_true": False,
            "qualifiers": {"source_contract": "peti_public_declared_total_metadata_v1"},
        }
    )
    proof = nomination_evidence()
    row = {
        "claim_id": str(claim.id),
        "person_id": str(PERSON_ID),
        "evidence_id": str(proof.id),
        "source_id": str(proof.source_id),
        "amount_thousand_krw": 0,
        "amount_unit": "THOUSAND_KRW",
        "publication_date": "2099-03-26",
        "report_type": "UNKNOWN",
    }
    empty = build_profile_projection(person(), [claim], {claim.id: [proof]}, [], [])
    assert section(empty, "public_declared_assets")["entries"] == []
    assert not any(
        entry.get("claim_id") == str(claim.id)
        for lane in empty["sections"]
        for entry in lane["entries"]
    )
    profile = build_profile_projection(
        person(), [claim], {claim.id: [proof]}, [], [], declared_assets=[row]
    )
    entry = section(profile, "public_declared_assets")["entries"][0]
    assert entry["details"]["amount_thousand_krw"] == 0
    assert entry["epistemic_status"] == "CLAIM"
    assert entry["source_ids"] == [str(proof.source_id)]
    assert entry["evidence_ids"] == [str(proof.id)]
    with pytest.raises(ValueError):
        build_profile_projection(
            person(),
            [claim],
            {claim.id: [proof]},
            [],
            [],
            declared_assets=[row | {"source_id": str(PERSON_ID)}],
        )


def test_profile_projection_has_stable_section_contract() -> None:
    claim = nomination_claim()
    evidence = nomination_evidence()
    profile = build_profile_projection(
        person(),
        [claim],
        {claim.id: [evidence]},
        [],
        [],
    )

    assert profile["section_order"] == [item[0] for item in SECTION_DEFINITIONS]
    assert len(profile["sections"]) == len(SECTION_DEFINITIONS)
    assert profile["semantics"] == "DERIVED_READ_MODEL_FROM_CANONICAL_EVIDENCE"


def test_nomination_populates_summary_and_timeline_but_not_current_power() -> None:
    claim = nomination_claim()
    evidence = nomination_evidence()
    profile = build_profile_projection(
        person(),
        [claim],
        {claim.id: [evidence]},
        [],
        [],
    )

    summary = section(profile, "summary")
    timeline = section(profile, "career_timeline")
    power = section(profile, "current_power_tasks")

    assert summary["status"] == "AVAILABLE"
    assert timeline["status"] == "AVAILABLE"
    assert summary["entries"][0]["details"]["predicate"] == "NOMINATED_AS"
    assert summary["entries"][0]["claim_id"] == str(CLAIM_ID)
    assert summary["entries"][0]["evidence_ids"] == [str(EVIDENCE_ID)]
    assert summary["entries"][0]["source_ids"] == [str(SOURCE_ID)]
    assert power["status"] == "UNKNOWN"
    assert power["entries"] == []


def test_projection_never_copies_evidence_excerpt() -> None:
    claim = nomination_claim()
    evidence = nomination_evidence()
    profile = build_profile_projection(
        person(),
        [claim],
        {claim.id: [evidence]},
        [],
        [],
    )

    assert "projection must not copy this excerpt" not in str(profile)


def test_typed_relationship_is_stakeholder_but_co_mention_only_is_not() -> None:
    claim = nomination_claim()
    evidence = nomination_evidence()
    relationships = [
        {
            "id": "rel-appointment",
            "person_id": str(PERSON_ID),
            "related_organization_id": "org-1",
            "related_person_id": None,
            "relationship_type": "appointed leadership",
            "strength": "STRONG",
            "evidence": [
                {
                    "claim_evidence_id": str(EVIDENCE_ID),
                    "evidence_type": "APPOINTMENT",
                }
            ],
        },
        {
            "id": "rel-comention",
            "person_id": str(PERSON_ID),
            "related_person_id": "person-2",
            "related_organization_id": None,
            "relationship_type": "same announcement co-mention",
            "strength": "WEAK",
            "evidence": [
                {
                    "claim_evidence_id": str(EVIDENCE_ID),
                    "evidence_type": "CO_MENTION",
                }
            ],
        },
    ]
    profile = build_profile_projection(
        person(),
        [claim],
        {claim.id: [evidence]},
        relationships,
        [],
    )

    stakeholders = section(profile, "stakeholders")
    assert stakeholders["status"] == "AVAILABLE"
    assert [item["id"] for item in stakeholders["entries"]] == ["relationship:rel-appointment"]
    assert stakeholders["entries"][0]["source_ids"] == [str(SOURCE_ID)]


def test_untraceable_typed_relationship_fails_closed() -> None:
    claim = nomination_claim()
    evidence = nomination_evidence()
    relationship = {
        "id": "rel-untraceable",
        "person_id": str(PERSON_ID),
        "related_organization_id": "org-unknown",
        "related_person_id": None,
        "relationship_type": "untraceable leadership",
        "strength": "STRONG",
        "evidence": [
            {
                "claim_evidence_id": "40000000-0000-0000-0000-999999999999",
                "evidence_type": "APPOINTMENT",
            }
        ],
    }
    profile = build_profile_projection(
        person(),
        [claim],
        {claim.id: [evidence]},
        [relationship],
        [],
    )

    stakeholders = section(profile, "stakeholders")
    assert stakeholders["status"] == "UNKNOWN"
    assert stakeholders["entries"] == []


def test_untraceable_decision_episode_fails_closed() -> None:
    claim = nomination_claim()
    evidence = nomination_evidence()
    profile = build_profile_projection(
        person(),
        [claim],
        {claim.id: [evidence]},
        [],
        [
            {
                "id": "episode-1",
                "person_id": str(PERSON_ID),
                "description": "Public decision episode",
                "action": "acted",
                "target": "policy",
                "outcome": "published",
                "source_ids": [str(SOURCE_ID)],
                "independent_origin_ids": ["origin-1"],
            }
        ],
    )

    episodes = section(profile, "decision_episodes")
    patterns = section(profile, "repeated_patterns")
    assert episodes["status"] == "UNKNOWN"
    assert episodes["entries"] == []
    assert patterns["status"] == "UNKNOWN"
    assert patterns["entries"] == []


def test_evidence_linked_decision_episode_keeps_canonical_trace() -> None:
    claim = nomination_claim()
    evidence = nomination_evidence()
    profile = build_profile_projection(
        person(),
        [claim],
        {claim.id: [evidence]},
        [],
        [
            {
                "id": "episode-1",
                "person_id": str(PERSON_ID),
                "description": "Public decision episode",
                "action": "acted",
                "target": "policy",
                "outcome": "published",
                "source_ids": [str(SOURCE_ID)],
                "independent_origin_ids": ["origin-1"],
                "claim_id": str(claim.id),
                "evidence_ids": [str(evidence.id)],
            }
        ],
    )

    entry = section(profile, "decision_episodes")["entries"][0]
    assert entry["kind"] == "DECISION_EPISODE"
    assert entry["claim_id"] == str(claim.id)
    assert entry["evidence_ids"] == [str(evidence.id)]
    assert entry["source_ids"] == [str(SOURCE_ID)]
    assert entry["evidence"][0]["stance"] == "SUPPORT"


def test_limitations_surface_unknown_sections_instead_of_filling_them() -> None:
    claim = nomination_claim()
    evidence = nomination_evidence()
    profile = build_profile_projection(
        person(),
        [claim],
        {claim.id: [evidence]},
        [],
        [],
    )

    limitations = section(profile, "limitations")
    limited_sections = {
        item["details"].get("section_id")
        for item in limitations["entries"]
        if item["kind"] == "LIMITATION"
    }
    assert "current_power_tasks" in limited_sections
    assert "forecast" in limited_sections
    assert "hearing_questions" in limited_sections
    assert profile["coverage"]["unknown"] > 0


def test_assembly_profile_uses_role_aware_content_and_dated_career_only() -> None:
    assembly_person = Person(
        id=UUID("00000000-0000-0000-0000-000000000199"),
        canonical_name="국회회원",
        identity_status=IdentityStatus.RESOLVED,
    )
    roster_role = Claim(
        id=UUID("30000000-0000-0000-0000-000000000199"),
        person_id=assembly_person.id,
        proposition="국회회원은 국회의원 명부에 등재되어 있다.",
        subject="국회회원",
        predicate="HELD_ROLE",
        object_text="국회의원",
        qualifiers={
            "source_scope": "current_member_roster",
            "provider_record_key": "M-199",
        },
        epistemic_status=EpistemicStatus.FACT,
        publication_status=PublicationStatus.PUBLISHED,
        asserted_as_true=True,
    )
    party = Claim(
        id=UUID("30000000-0000-0000-0000-000000000200"),
        person_id=assembly_person.id,
        proposition="국회회원의 소속 정당은 테스트정당이다.",
        subject="국회회원",
        predicate="ASSEMBLY_PARTY",
        object_text="테스트정당",
        qualifiers={
            "source_contract": "assembly_member_roster",
            "source_scope": "current_member_roster",
            "field_name": "party",
        },
        epistemic_status=EpistemicStatus.FACT,
        publication_status=PublicationStatus.PUBLISHED,
        asserted_as_true=True,
    )
    historical = Claim(
        id=UUID("30000000-0000-0000-0000-000000000201"),
        person_id=assembly_person.id,
        proposition="국회회원은 과거 위원회 보좌관으로 근무했다.",
        subject="국회회원",
        predicate="WORKED_AS",
        object_text="위원회 보좌관",
        qualifiers={"date": "2020-01-02"},
        epistemic_status=EpistemicStatus.FACT,
        publication_status=PublicationStatus.PUBLISHED,
        asserted_as_true=True,
    )
    profile = build_profile_projection(
        assembly_person,
        [roster_role, party, historical],
        {},
        [],
        [],
    )

    assert [item["id"] for item in profile["sections"]] == [
        "overview",
        "current_role",
        "career_timeline",
        "legislative_activity",
        "official_press_records",
        "public_self_housing",
        "public_declared_assets",
        "limitations",
    ]
    assert section(profile, "career_timeline")["entries"][0]["claim_id"] == str(historical.id)
    assert all(
        item["id"] not in {"appointment_logic", "hearing_questions", "forecast", "stakeholders"}
        for item in profile["sections"]
    )
    assert "국회회원은 국회의원 명부에 등재되어 있다." not in str(
        section(profile, "career_timeline")
    )


def opendart_role_claim(**qualifiers: str) -> Claim:
    return Claim(
        id=UUID("30000000-0000-0000-0000-000000000301"),
        person_id=PERSON_ID,
        proposition="테스트전자는 OpenDART 임원 현황 공시에 김프로필을 상무로 기재했다.",
        subject="김프로필",
        predicate="OPENDART_DISCLOSED_EXECUTIVE_ROLE",
        object_text="테스트전자 상무",
        qualifiers={"corp_name": "테스트전자", "business_year": "2025", **qualifiers},
        epistemic_status=EpistemicStatus.CLAIM,
        publication_status=PublicationStatus.PUBLISHED,
    )


def opendart_role_evidence(claim: Claim) -> ClaimEvidence:
    return ClaimEvidence(
        id=UUID("40000000-0000-0000-0000-000000000301"),
        claim_id=claim.id,
        source_id=SOURCE_ID,
        snapshot_id=UUID("50000000-0000-0000-0000-000000000301"),
        feeder_observation_id=UUID("60000000-0000-0000-0000-000000000301"),
        stance=EvidenceStance.SUPPORT,
    )


def test_empty_sections_carry_projection_only_reasons() -> None:
    claim = nomination_claim()
    profile = build_profile_projection(
        person(), [claim], {claim.id: [nomination_evidence()]}, [], []
    )

    reasons = {item["id"]: item["reason"] for item in profile["sections"]}
    assert reasons["identity"] is None
    assert reasons["summary"] is None
    assert reasons["assembly_base_profile"] == "NOT_APPLICABLE"
    assert section(profile, "assembly_base_profile")["status"] == "NOT_APPLICABLE"
    assert reasons["recent_changes"] == "INSUFFICIENT_EVIDENCE"
    assert reasons["current_power_tasks"] == "SOURCE_NOT_COLLECTED"
    assert reasons["decision_episodes"] == "SOURCE_NOT_COLLECTED"
    assert reasons["stakeholders"] == "SOURCE_NOT_COLLECTED"
    assert reasons["controversies"] == "SOURCE_NOT_COLLECTED"
    assert reasons["repeated_patterns"] == "INSUFFICIENT_EVIDENCE"
    # A published nomination makes the hearing lane applicable; no question is generated.
    assert reasons["hearing_questions"] == "DERIVATION_NOT_AVAILABLE"
    assert section(profile, "hearing_questions")["entries"] == []
    assert reasons["forecast"] == "DERIVATION_NOT_AVAILABLE"
    assert section(profile, "forecast")["entries"] == []
    assert profile["coverage"]["not_applicable"] == 1

    limited = {
        item["details"]["section_id"]: item["details"]["reason"]
        for item in section(profile, "limitations")["entries"]
        if item["kind"] == "LIMITATION"
    }
    assert "assembly_base_profile" not in limited
    assert limited["current_power_tasks"] == "SOURCE_NOT_COLLECTED"


def test_hearing_questions_are_not_applicable_without_a_published_nomination() -> None:
    claim = opendart_role_claim()
    profile = build_profile_projection(
        person(), [claim], {claim.id: [opendart_role_evidence(claim)]}, [], []
    )

    hearing = section(profile, "hearing_questions")
    assert hearing["status"] == "NOT_APPLICABLE"
    assert hearing["reason"] == "NOT_APPLICABLE"
    assert hearing["entries"] == []
    assert profile["coverage"]["not_applicable"] == 2


def test_company_disclosed_responsibility_feeds_current_power_as_attributed_claim() -> None:
    claim = opendart_role_claim(responsibility="경영지원 총괄")
    evidence = opendart_role_evidence(claim)
    profile = build_profile_projection(person(), [claim], {claim.id: [evidence]}, [], [])

    power = section(profile, "current_power_tasks")
    assert power["status"] == "PARTIAL"
    assert power["reason"] is None
    [entry] = power["entries"]
    assert entry["title"] == "테스트전자 공시 담당업무: 경영지원 총괄"
    assert entry["epistemic_status"] == "CLAIM"
    assert entry["claim_id"] == str(claim.id)
    assert entry["evidence_ids"] == [str(evidence.id)]
    assert entry["evidence"][0]["feeder_observation_id"] == str(evidence.feeder_observation_id)
    assert entry["details"]["responsibility"] == "경영지원 총괄"
    assert entry["details"]["responsibility_semantics"] == (
        "company_disclosed_responsibility_not_authority"
    )


def test_blank_unpublished_or_evidenceless_responsibility_yields_no_power_entry() -> None:
    blank = opendart_role_claim(responsibility="-")
    unpublished = opendart_role_claim(responsibility="재무").model_copy(
        update={"publication_status": PublicationStatus.DRAFT}
    )
    for claim, evidence in (
        (blank, [opendart_role_evidence(blank)]),
        (unpublished, [opendart_role_evidence(unpublished)]),
        (opendart_role_claim(responsibility="재무"), []),
    ):
        profile = build_profile_projection(person(), [claim], {claim.id: evidence}, [], [])
        power = section(profile, "current_power_tasks")
        assert power["entries"] == []
        assert power["reason"] == "SOURCE_NOT_COLLECTED"


def test_independent_episodes_make_patterns_eligible_but_never_generate_one() -> None:
    claim = nomination_claim()
    evidence = nomination_evidence()
    episodes = [
        {
            "id": f"episode-{index}",
            "person_id": str(PERSON_ID),
            "description": f"Public decision episode {index}",
            "action": "acted",
            "target": "policy",
            "outcome": "published",
            "source_ids": [str(SOURCE_ID)],
            "independent_origin_ids": [f"origin-{index}"],
            "claim_id": str(claim.id),
            "evidence_ids": [str(evidence.id)],
        }
        for index in (1, 2)
    ]
    one = build_profile_projection(person(), [claim], {claim.id: [evidence]}, [], episodes[:1])
    two = build_profile_projection(person(), [claim], {claim.id: [evidence]}, [], episodes)

    assert section(one, "repeated_patterns")["reason"] == "INSUFFICIENT_EVIDENCE"
    patterns = section(two, "repeated_patterns")
    assert patterns["reason"] == "DERIVATION_NOT_AVAILABLE"
    assert patterns["status"] == "UNKNOWN"
    assert patterns["entries"] == []


def source_career_claim(predicate: str = "ASSEMBLY_BIOGRAPHY_CAREER", **qualifiers: str) -> Claim:
    contracts = {
        "ASSEMBLY_BIOGRAPHY_CAREER": "assembly_member_profile_biography",
        "NEC_CANDIDATE_CAREER": "nec_assembly_candidate_submission",
        "ASSEMBLY_HISTORICAL_TERM": "assembly_historical_member_term",
    }
    historical = predicate == "ASSEMBLY_HISTORICAL_TERM"
    return Claim(
        id=uuid5(CLAIM_ID, predicate),
        person_id=PERSON_ID,
        proposition="공식 기록에 김프로필의 「2024.1~2024.5 테스트정당 대표」 경력이 기재되어 있다.",
        subject="김프로필",
        predicate=predicate,
        object_text="2024.1~2024.5 테스트정당 대표",
        qualifiers={"source_contract": contracts[predicate], **qualifiers},
        epistemic_status=EpistemicStatus.FACT if historical else EpistemicStatus.CLAIM,
        publication_status=PublicationStatus.PUBLISHED,
        asserted_as_true=historical,
        # Collection / election date must never substitute for a career period.
        valid_from=datetime(2026, 10, 7, tzinfo=UTC),
        recorded_at=datetime(2026, 10, 8, tzinfo=UTC),
    )


def career_evidence(claim: Claim) -> ClaimEvidence:
    return ClaimEvidence(
        id=uuid5(claim.id, "SUPPORT"),
        claim_id=claim.id,
        source_id=SOURCE_ID,
        stance=EvidenceStance.SUPPORT,
        snapshot_id=UUID("50000000-0000-0000-0000-000000000301"),
        feeder_observation_id=UUID("60000000-0000-0000-0000-000000000301"),
    )


def test_attributed_month_career_reaches_assembly_timeline_without_truth_or_date_upgrade() -> None:
    claim = source_career_claim(
        period_start="2024-01-01",
        period_start_precision="MONTH",
        period_end="2024-05-01",
        period_end_precision="MONTH",
        date="2026-10-07",
        private_contact="not a public projection field",
    )
    evidence = career_evidence(claim)
    roster = nomination_claim().model_copy(
        update={
            "predicate": "HELD_ROLE",
            "qualifiers": {"source_scope": "current_member_roster", "provider_record_key": "M-99"},
        }
    )
    profile = build_profile_projection(person(), [roster, claim], {claim.id: [evidence]}, [], [])
    timeline = section(profile, "career_timeline")
    [entry] = timeline["entries"]

    assert profile["profile_kind"] == "ASSEMBLY_MEMBER"
    assert timeline["status"] == "PARTIAL"
    assert entry["title"] == claim.proposition
    assert entry["epistemic_status"] == "CLAIM"
    assert entry["details"]["asserted_as_true"] is False
    assert entry["details"]["career_semantics"] == "SOURCE_ATTRIBUTED_BIOGRAPHY"
    assert entry["date"] is None
    assert entry["details"]["career_period"] == {
        "start": "2024-01-01",
        "start_precision": "MONTH",
        "end": "2024-05-01",
        "end_precision": "MONTH",
        "point": None,
        "point_precision": "UNKNOWN",
        "ongoing": False,
    }
    assert entry["evidence_ids"] == [str(evidence.id)]
    assert entry["source_ids"] == [str(SOURCE_ID)]
    assert entry["evidence"][0]["snapshot_id"] == str(evidence.snapshot_id)
    assert entry["evidence"][0]["feeder_observation_id"] == str(evidence.feeder_observation_id)
    assert "not a public projection field" not in str(profile)


def test_former_only_member_term_preserves_past_party_and_does_not_create_current_role() -> None:
    claim = source_career_claim(
        "ASSEMBLY_HISTORICAL_TERM",
        term_start="2012-05-30",
        term_end="2016-05-29",
        party="당시정당",
        district="당시지역구",
        profile_unit_name="제19대",
    )
    profile = build_profile_projection(
        person(), [claim], {claim.id: [career_evidence(claim)]}, [], []
    )
    timeline = section(profile, "career_timeline")
    [entry] = timeline["entries"]

    assert timeline["status"] == "AVAILABLE"
    assert entry["epistemic_status"] == "FACT"
    assert entry["details"]["asserted_as_true"] is True
    assert entry["date"] == "2012-05-30"
    assert entry["details"]["career_period"]["end"] == "2016-05-29"
    assert entry["details"]["career_period"]["end_precision"] == "DAY"
    assert entry["details"]["historical_party"] == "당시정당"
    assert entry["details"]["historical_district"] == "당시지역구"
    assert entry["details"]["term_name"] == "제19대"
    assert section(profile, "summary")["entries"] == []
    assert section(profile, "current_power_tasks")["entries"] == []
    assert all(item["id"] != "current_role" for item in profile["sections"])


@pytest.mark.parametrize(
    "field_name,text", [("career1", "전 테스트기관 이사"), ("occupation", "기업인")]
)
def test_nec_undated_submitted_career_and_occupation_never_use_election_date(
    field_name, text
) -> None:
    claim = source_career_claim(
        "NEC_CANDIDATE_CAREER",
        field_name=field_name,
        election_id="20240410",
        current_marker="FORMER",
        date="2024-04-10",
    ).model_copy(update={"object_text": text})
    profile = build_profile_projection(
        person(), [claim], {claim.id: [career_evidence(claim)]}, [], []
    )
    [entry] = section(profile, "career_timeline")["entries"]

    assert entry["date"] is None
    assert entry["details"]["career_semantics"] == "CANDIDATE_SUBMITTED_CAREER"
    assert entry["details"]["asserted_as_true"] is False
    assert all(entry["details"]["career_period"][key] is None for key in ("start", "end", "point"))


@pytest.mark.parametrize("precision,value", [("YEAR", "1991-01-01"), ("DAY", "2020-04-03")])
def test_source_career_single_point_preserves_precision(precision, value) -> None:
    claim = source_career_claim(period_point=value, period_point_precision=precision)
    profile = build_profile_projection(
        person(), [claim], {claim.id: [career_evidence(claim)]}, [], []
    )
    [entry] = section(profile, "career_timeline")["entries"]
    assert entry["details"]["career_period"]["point"] == value
    assert entry["details"]["career_period"]["point_precision"] == precision
    assert entry["date"] == (value if precision == "DAY" else None)


@pytest.mark.parametrize("header", ["■ 경력:", "주요 경력：", "[약력]", "■ 학력:", ""])
def test_heading_only_biography_does_not_become_a_career_event(header) -> None:
    claim = source_career_claim().model_copy(update={"object_text": header})
    profile = build_profile_projection(
        person(), [claim], {claim.id: [career_evidence(claim)]}, [], []
    )
    assert section(profile, "career_timeline")["entries"] == []


@pytest.mark.parametrize(
    "case",
    [
        "draft",
        "withheld",
        "superseded",
        "other_person",
        "unresolved_person",
        "superseded_person",
        "missing_evidence",
        "other_claim_evidence",
        "refute_only",
        "wrong_contract",
    ],
)
def test_new_career_sources_fail_closed_outside_current_published_subject(case) -> None:
    claim = source_career_claim()
    subject = person()
    evidence = [career_evidence(claim)]
    if case in {"draft", "withheld"}:
        claim = claim.model_copy(update={"publication_status": PublicationStatus(case.upper())})
    elif case == "superseded":
        claim = claim.model_copy(update={"superseded_at": datetime(2026, 10, 8, tzinfo=UTC)})
    elif case == "other_person":
        claim = claim.model_copy(update={"person_id": UUID(int=123)})
    elif case == "unresolved_person":
        subject = subject.model_copy(update={"identity_status": IdentityStatus.REVIEW})
    elif case == "superseded_person":
        subject = subject.model_copy(update={"superseded_at": datetime(2026, 10, 8, tzinfo=UTC)})
    elif case == "missing_evidence":
        evidence = []
    elif case == "other_claim_evidence":
        evidence = [evidence[0].model_copy(update={"claim_id": UUID(int=123)})]
    elif case == "refute_only":
        evidence = [evidence[0].model_copy(update={"stance": EvidenceStance.REFUTE})]
    elif case == "wrong_contract":
        claim = claim.model_copy(update={"qualifiers": {"source_contract": "unapproved_source"}})
    profile = build_profile_projection(subject, [claim], {claim.id: evidence}, [], [])
    assert section(profile, "career_timeline")["entries"] == []


def test_career_conflict_and_published_unknown_remain_visible_without_truth_assertion() -> None:
    claim = source_career_claim().model_copy(
        update={
            "epistemic_status": EpistemicStatus.UNKNOWN,
            "resolution_note": "두 출처의 기간 기재가 상충하여 미해결입니다.",
        }
    )
    support = career_evidence(claim)
    refute = support.model_copy(
        update={"id": uuid5(claim.id, "REFUTE"), "stance": EvidenceStance.REFUTE}
    )
    profile = build_profile_projection(person(), [claim], {claim.id: [support, refute]}, [], [])
    timeline = section(profile, "career_timeline")
    [entry] = timeline["entries"]

    assert timeline["status"] == "PARTIAL"
    assert entry["epistemic_status"] == "UNKNOWN"
    assert entry["source_conflict"] is True
    assert entry["details"]["asserted_as_true"] is False
    assert entry["details"]["resolution_note"] == claim.resolution_note
    assert {item["stance"] for item in entry["evidence"]} == {"SUPPORT", "REFUTE"}


def test_career_dates_sort_before_undated_without_reordering_input_truth() -> None:
    dated = source_career_claim(period_start="2024-01-01", period_start_precision="MONTH")
    undated = source_career_claim("NEC_CANDIDATE_CAREER")
    claims = [undated, dated]
    profile = build_profile_projection(
        person(),
        claims,
        {item.id: [career_evidence(item)] for item in claims},
        [],
        [],
    )
    assert [item["claim_id"] for item in section(profile, "career_timeline")["entries"]] == [
        str(dated.id),
        str(undated.id),
    ]
    assert claims == [undated, dated]


@pytest.mark.parametrize(
    "qualifiers",
    [
        {"period_start": "2024-13-01", "period_start_precision": "DAY"},
        {"period_start": "2024-01-01", "period_start_precision": "UNKNOWN"},
        {
            "period_start": "2024-05-01",
            "period_start_precision": "MONTH",
            "period_end": "2024-01-01",
            "period_end_precision": "MONTH",
        },
    ],
)
def test_malformed_career_period_keeps_record_without_manufacturing_a_date(qualifiers) -> None:
    claim = source_career_claim(**qualifiers)
    profile = build_profile_projection(
        person(), [claim], {claim.id: [career_evidence(claim)]}, [], []
    )
    [entry] = section(profile, "career_timeline")["entries"]
    assert entry["date"] is None
    assert entry["details"]["career_period"]["start"] is None
    assert entry["title"] == claim.proposition

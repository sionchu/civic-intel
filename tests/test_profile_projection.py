from datetime import UTC, datetime
from uuid import UUID

from packages.domain.contracts import Claim, ClaimEvidence, Person
from packages.domain.enums import (
    EpistemicStatus,
    EvidenceStance,
    IdentityStatus,
    PublicationStatus,
)
from packages.rendering.profile_projection import (
    RECENT_LEGISLATIVE_ACTIVITY_LIMIT,
    SECTION_DEFINITIONS,
    build_people_discovery_projection,
    build_profile_projection,
)

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
    assert len(profile["sections"]) == 15
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
    assert [item["id"] for item in stakeholders["entries"]] == [
        "relationship:rel-appointment"
    ]
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


def _record_claim(
    owner: Person,
    number: int,
    predicate: str,
    value: str,
    qualifiers: dict[str, str] | None = None,
    *,
    factual: bool = False,
) -> Claim:
    return Claim(
        id=UUID(f"30000000-0000-0000-0000-{number:012d}"),
        person_id=owner.id,
        proposition=f"{owner.canonical_name}: {value}",
        subject=owner.canonical_name,
        predicate=predicate,
        object_text=value,
        qualifiers=qualifiers or {},
        epistemic_status=EpistemicStatus.FACT if factual else EpistemicStatus.CLAIM,
        publication_status=PublicationStatus.PUBLISHED,
        asserted_as_true=factual,
    )


def _record_evidence(claim: Claim, number: int) -> ClaimEvidence:
    return ClaimEvidence(
        id=UUID(f"40000000-0000-0000-0000-{number:012d}"),
        claim_id=claim.id,
        source_id=SOURCE_ID,
        stance=EvidenceStance.SUPPORT,
    )


def test_assembly_activity_shows_recent_twenty_with_whole_record_role_counts() -> None:
    owner = person()
    claims = [
        _record_claim(
            owner,
            500 + index,
            "ASSEMBLY_BILL_PARTICIPATION",
            f"법안 {index}",
            {
                "source_contract": "assembly_term_bill_participation",
                "provider_identity_namespace": "assembly_mona_cd",
                "bill_id": f"BILL-{index:03d}",
                "proposed_date": f"2026-09-{22 if index == 22 else index + 1:02d}",
                "participation_role": (
                    "REPRESENTATIVE_PROPOSER" if index % 2 == 0 else "CO_PROPOSER"
                ),
            },
            factual=True,
        )
        for index in range(23)
    ]
    evidence = {
        claim.id: [_record_evidence(claim, 500 + index)]
        for index, claim in enumerate(claims)
    }

    profile = build_profile_projection(owner, list(reversed(claims)), evidence, [], [])
    activity = section(profile, "legislative_activity")

    assert profile["profile_kind"] == "ASSEMBLY_MEMBER"
    assert activity["status"] == "AVAILABLE"
    assert len(activity["entries"]) == RECENT_LEGISLATIVE_ACTIVITY_LIMIT == 20
    assert [entry["claim_id"] for entry in activity["entries"]] == [
        str(claims[index].id) for index in [21, 22, *range(20, 2, -1)]
    ]
    assert activity["note"] == (
        "공식 의안정보 법안 참여 기록 23건(대표발의 12 · 공동발의 11) 가운데 "
        "최근 20건입니다. 정확한 MONA_CD 연결 Claim을 대표 발의와 공동 발의로 구분해 표시합니다."
    )
    for entry in activity["entries"]:
        claim_id = UUID(entry["claim_id"])
        [claim_evidence] = evidence[claim_id]
        assert entry["evidence_ids"] == [str(claim_evidence.id)]
        assert entry["evidence"][0]["id"] == str(claim_evidence.id)
        assert entry["source_ids"] == [str(claim_evidence.source_id)]


def test_assembly_background_records_keep_claim_status_and_exclude_heading() -> None:
    owner = person()
    roster = _record_claim(
        owner, 401, "HELD_ROLE", "국회의원",
        {"source_scope": "current_member_roster", "provider_record_key": "M-099"},
        factual=True,
    )
    bio_school = _record_claim(owner, 402, "ASSEMBLY_BIOGRAPHY_EDUCATION", "의학박사")
    nec_school = _record_claim(owner, 403, "NEC_CANDIDATE_EDUCATION", "대학 졸업")
    bio_career = _record_claim(owner, 404, "ASSEMBLY_BIOGRAPHY_CAREER", "의사")
    nec_career = _record_claim(owner, 405, "NEC_CANDIDATE_CAREER", "대표")
    heading = _record_claim(owner, 406, "ASSEMBLY_BIOGRAPHY_CAREER", " <대표경력> ")
    historical = _record_claim(
        owner, 407, "ASSEMBLY_HISTORICAL_TERM", "제20대 의원",
        {"term_start": "2016-05-30", "term_end": "2020-05-29"}, factual=True,
    )
    draft = _record_claim(owner, 408, "NEC_CANDIDATE_CAREER", "미공개 문구").model_copy(
        update={"publication_status": PublicationStatus.DRAFT}
    )
    superseded = _record_claim(owner, 409, "NEC_CANDIDATE_CAREER", "대체된 문구").model_copy(
        update={"superseded_at": datetime(2020, 1, 1, tzinfo=UTC)}
    )
    claims = [nec_career, heading, bio_career, roster, nec_school, bio_school, historical, draft, superseded]
    evidence = {claim.id: [_record_evidence(claim, 400 + index)] for index, claim in enumerate(claims)}

    profile = build_profile_projection(owner, claims, evidence, [], [])

    assert profile["profile_kind"] == "ASSEMBLY_MEMBER"
    assert profile["section_order"].index("background_records") == profile["section_order"].index("career_timeline") + 1
    background = section(profile, "background_records")
    assert background["label"] == "학력·경력 기재 사항"
    assert background["status"] == "PARTIAL"
    assert "국회 의원 프로필 / 선관위 후보자 제출 자료" in background["note"]
    assert [entry["claim_id"] for entry in background["entries"]] == [
        str(claim.id) for claim in (bio_school, nec_school, bio_career, nec_career)
    ]
    assert all(entry["epistemic_status"] == "CLAIM" for entry in background["entries"])
    assert all(entry["evidence_ids"] for entry in background["entries"])
    assert section(profile, "career_timeline")["entries"][0]["date"] == "2016-05-30"
    assert all(
        entry["details"].get("section_id") != "career_timeline"
        for entry in section(profile, "limitations")["entries"]
    )


def test_former_member_historical_terms_and_nec_records() -> None:
    owner = person()
    newer = _record_claim(
        owner, 411, "ASSEMBLY_HISTORICAL_TERM", "제18대 의원",
        {"term_start": "2008-05-30", "term_end": "2012-05-29"}, factual=True,
    )
    older = _record_claim(
        owner, 412, "ASSEMBLY_HISTORICAL_TERM", "제17대 의원",
        {"term_start": "2004-05-30", "term_end": "2008-05-29"}, factual=True,
    )
    career = _record_claim(owner, 413, "NEC_CANDIDATE_CAREER", "후보자 기재 경력")
    school = _record_claim(owner, 414, "NEC_CANDIDATE_EDUCATION", "후보자 기재 학력")
    claims = [newer, career, older, school]
    evidence = {claim.id: [_record_evidence(claim, 410 + index)] for index, claim in enumerate(claims)}

    profile = build_profile_projection(owner, claims, evidence, [], [])

    assert profile.get("profile_kind") != "ASSEMBLY_MEMBER"
    timeline = section(profile, "career_timeline")
    assert timeline["status"] == "AVAILABLE"
    assert [(entry["claim_id"], entry["date"]) for entry in timeline["entries"]] == [
        (str(older.id), "2004-05-30"), (str(newer.id), "2008-05-30")
    ]
    background = section(profile, "background_records")
    assert background["status"] == "PARTIAL"
    assert [entry["claim_id"] for entry in background["entries"]] == [str(school.id), str(career.id)]
    assert all(entry["epistemic_status"] == "CLAIM" for entry in background["entries"])


def test_people_discovery_uses_published_asserted_committee_memberships() -> None:
    owner = person()
    defense = _record_claim(
        owner, 421, "ASSEMBLY_COMMITTEE_MEMBERSHIP", "국방위원회",
        {"committee_code": "DEF", "committee_name": "국방위원회"}, factual=True,
    )
    information = _record_claim(
        owner, 422, "ASSEMBLY_COMMITTEE_MEMBERSHIP", "정보위원회",
        {"committee_code": "INT", "committee_name": "정보위원회"}, factual=True,
    )
    duplicate = _record_claim(
        owner, 423, "ASSEMBLY_COMMITTEE_MEMBERSHIP", "국방위원회",
        {"committee_code": "DEF", "committee_name": "국방위원회"}, factual=True,
    )
    draft = _record_claim(
        owner, 424, "ASSEMBLY_COMMITTEE_MEMBERSHIP", "교육위원회",
        {"committee_code": "EDU", "committee_name": "교육위원회"}, factual=True,
    ).model_copy(update={"publication_status": PublicationStatus.DRAFT})
    unsupported = _record_claim(
        owner, 425, "ASSEMBLY_COMMITTEE_MEMBERSHIP", "기획재정위원회",
        {"committee_code": "FIN", "committee_name": "기획재정위원회"}, factual=True,
    )
    superseded = _record_claim(
        owner, 426, "ASSEMBLY_COMMITTEE_MEMBERSHIP", "운영위원회",
        {"committee_code": "OPS", "committee_name": "운영위원회"}, factual=True,
    ).model_copy(update={"superseded_at": datetime(2020, 1, 1, tzinfo=UTC)})
    claims = [information, duplicate, draft, defense, superseded, unsupported]
    evidence = {claim.id: [_record_evidence(claim, 420 + index)] for index, claim in enumerate(claims[:-1])}

    discovery = build_people_discovery_projection(owner, claims, evidence)

    assert discovery["committee_memberships"] == [
        {
            "committee_code": "DEF", "committee_name": "국방위원회",
            "claim_id": str(defense.id), "evidence_ids": [str(evidence[defense.id][0].id)],
        },
        {
            "committee_code": "INT", "committee_name": "정보위원회",
            "claim_id": str(information.id), "evidence_ids": [str(evidence[information.id][0].id)],
        },
    ]


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

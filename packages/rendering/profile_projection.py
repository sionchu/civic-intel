from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID

from packages.domain.contracts import Claim, ClaimEvidence, Person
from packages.domain.enums import EpistemicStatus, IdentityStatus

SECTION_DEFINITIONS: tuple[tuple[str, str], ...] = (
    ("identity", "신원"),
    ("summary", "한눈에 보는 요약"),
    ("career_timeline", "경력 타임라인"),
    ("current_power_tasks", "현재 권한과 과업"),
    ("appointment_logic", "임명 논리"),
    ("decision_episodes", "의사결정 에피소드"),
    ("repeated_patterns", "반복 패턴"),
    ("stakeholders", "이해관계자와 관계"),
    ("controversies", "논란 및 반론"),
    ("hearing_questions", "인사청문·검증 질문"),
    ("forecast", "전망과 시나리오"),
    ("limitations", "한계 및 미확인"),
)

SUMMARY_PREDICATES = frozenset(
    {
        "NOMINATED_AS",
        "DESIGNATED_AS",
        "APPOINTED_AS",
        "ELECTED_AS",
        "CURRENT_OFFICE",
        "HOLDS_OFFICE",
    }
)
CAREER_PREDICATES = frozenset(
    {
        *SUMMARY_PREDICATES,
        "SERVED_AS",
        "HELD_ROLE",
        "WORKED_AS",
        "APPOINTED_TO",
    }
)
POWER_TASK_PREDICATES = frozenset(
    {
        "HAS_AUTHORITY",
        "RESPONSIBLE_FOR",
        "CURRENT_RESPONSIBILITY",
        "LEADS",
        "CHAIRS",
        "SUPERVISES",
    }
)
APPOINTMENT_LOGIC_PREDICATES = frozenset(
    {
        "APPOINTMENT_RATIONALE",
        "HAS_REPUTATION",
        "SELECTED_BECAUSE",
        "APPOINTMENT_LOGIC",
    }
)
CONTROVERSY_PREDICATES = frozenset(
    {
        "CONTROVERSY",
        "ALLEGATION",
        "DISPUTED_CLAIM",
        "CONTESTED_ASSERTION",
    }
)


def _ordered_unique(values: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _claim_entry(
    claim: Claim,
    evidence_by_claim: Mapping[UUID, Sequence[ClaimEvidence]],
) -> dict[str, Any]:
    evidence = tuple(evidence_by_claim.get(claim.id, ()))
    return {
        "id": f"claim:{claim.id}",
        "kind": "CLAIM",
        "title": claim.proposition,
        "epistemic_status": claim.epistemic_status.value,
        "claim_id": str(claim.id),
        "evidence_ids": [str(item.id) for item in evidence],
        "source_ids": _ordered_unique([str(item.source_id) for item in evidence]),
        "date": claim.qualifiers.get("date"),
        "details": {
            "predicate": claim.predicate,
            "object_text": claim.object_text,
            "publication_status": claim.publication_status.value,
            "asserted_as_true": claim.asserted_as_true,
            "resolution_note": claim.resolution_note,
        },
    }


def _claim_section_status(entries: Sequence[dict[str, Any]]) -> str:
    if not entries:
        return "UNKNOWN"
    if any(item.get("epistemic_status") != EpistemicStatus.FACT.value for item in entries):
        return "PARTIAL"
    return "AVAILABLE"


def _section(
    section_id: str,
    label: str,
    entries: Sequence[dict[str, Any]],
    *,
    status: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    selected_status = status or _claim_section_status(entries)
    return {
        "id": section_id,
        "label": label,
        "status": selected_status,
        "note": note,
        "entries": list(entries),
    }


def _claim_entries_for(
    claims: Sequence[Claim],
    evidence_by_claim: Mapping[UUID, Sequence[ClaimEvidence]],
    predicates: frozenset[str],
) -> list[dict[str, Any]]:
    selected = [claim for claim in claims if claim.predicate in predicates]
    selected.sort(key=lambda item: (item.qualifiers.get("date", ""), str(item.id)))
    return [_claim_entry(claim, evidence_by_claim) for claim in selected]


def _controversy_entries(
    claims: Sequence[Claim],
    evidence_by_claim: Mapping[UUID, Sequence[ClaimEvidence]],
) -> list[dict[str, Any]]:
    selected: list[Claim] = []
    for claim in claims:
        stances = {item.stance.value for item in evidence_by_claim.get(claim.id, ())}
        if claim.predicate in CONTROVERSY_PREDICATES or stances >= {"SUPPORT", "REFUTE"}:
            selected.append(claim)
    return [_claim_entry(claim, evidence_by_claim) for claim in selected]


def _decision_episode_entries(
    decision_episodes: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for episode in decision_episodes:
        entries.append(
            {
                "id": f"episode:{episode['id']}",
                "kind": "DECISION_EPISODE",
                "title": episode["description"],
                "epistemic_status": EpistemicStatus.FACT.value,
                "claim_id": None,
                "evidence_ids": [],
                "source_ids": _ordered_unique(
                    [str(item) for item in episode.get("source_ids", [])]
                ),
                "date": None,
                "details": {
                    "action": episode.get("action"),
                    "target": episode.get("target"),
                    "outcome": episode.get("outcome"),
                    "independent_origin_ids": [
                        str(item) for item in episode.get("independent_origin_ids", [])
                    ],
                },
            }
        )
    return entries


def _relationship_entries(
    relationships: Sequence[dict[str, Any]],
    evidence_by_claim: Mapping[UUID, Sequence[ClaimEvidence]],
) -> list[dict[str, Any]]:
    evidence_by_id = {
        str(item.id): item
        for claim_evidence in evidence_by_claim.values()
        for item in claim_evidence
    }
    entries: list[dict[str, Any]] = []
    for relationship in relationships:
        refs = relationship.get("evidence", [])
        typed_refs = [
            item for item in refs if item.get("evidence_type") not in {None, "CO_MENTION"}
        ]
        if not typed_refs:
            continue
        evidence_ids = [str(item["claim_evidence_id"]) for item in typed_refs]
        source_ids = _ordered_unique(
            [
                str(evidence_by_id[evidence_id].source_id)
                for evidence_id in evidence_ids
                if evidence_id in evidence_by_id
            ]
        )
        entries.append(
            {
                "id": f"relationship:{relationship['id']}",
                "kind": "RELATIONSHIP",
                "title": relationship.get("relationship_type", "typed relationship"),
                "epistemic_status": EpistemicStatus.FACT.value,
                "claim_id": None,
                "evidence_ids": evidence_ids,
                "source_ids": source_ids,
                "date": None,
                "details": {
                    "strength": relationship.get("strength"),
                    "related_person_id": relationship.get("related_person_id"),
                    "related_organization_id": relationship.get("related_organization_id"),
                    "evidence_types": _ordered_unique(
                        [str(item["evidence_type"]) for item in typed_refs]
                    ),
                },
            }
        )
    return entries


def build_profile_projection(
    person: Person,
    claims: Sequence[Claim],
    evidence_by_claim: Mapping[UUID, Sequence[ClaimEvidence]],
    relationships: Sequence[dict[str, Any]],
    decision_episodes: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    """Build a deterministic read model without creating new profile truth."""

    identity_entries: list[dict[str, Any]] = [
        {
            "id": f"identity:{person.id}",
            "kind": "IDENTITY",
            "title": person.canonical_name,
            "epistemic_status": None,
            "claim_id": None,
            "evidence_ids": [],
            "source_ids": [],
            "date": None,
            "details": {
                "identity_status": person.identity_status.value,
                "birth_date": person.birth_date.isoformat() if person.birth_date else None,
            },
        }
    ]
    identity_note = (
        None if person.birth_date else "검토된 현재 근거에서 생년월일은 확인되지 않았습니다."
    )

    summary_entries = _claim_entries_for(claims, evidence_by_claim, SUMMARY_PREDICATES)
    timeline_entries = _claim_entries_for(claims, evidence_by_claim, CAREER_PREDICATES)
    power_entries = _claim_entries_for(claims, evidence_by_claim, POWER_TASK_PREDICATES)
    appointment_logic_entries = _claim_entries_for(
        claims, evidence_by_claim, APPOINTMENT_LOGIC_PREDICATES
    )
    episode_entries = _decision_episode_entries(decision_episodes)
    stakeholder_entries = _relationship_entries(relationships, evidence_by_claim)
    controversy_entries = _controversy_entries(claims, evidence_by_claim)

    sections: list[dict[str, Any]] = [
        _section("identity", "신원", identity_entries, status="AVAILABLE", note=identity_note),
        _section(
            "summary",
            "한눈에 보는 요약",
            summary_entries,
            note=(
                "명시적 공직 상태·인선 사실만 투영합니다."
                if summary_entries
                else "검토된 요약용 공직 상태 근거가 없습니다."
            ),
        ),
        _section(
            "career_timeline",
            "경력 타임라인",
            timeline_entries,
            note=(
                "날짜가 있는 명시적 경력·인선 predicate만 사용합니다."
                if timeline_entries
                else "검토된 경력 타임라인 근거가 없습니다."
            ),
        ),
        _section(
            "current_power_tasks",
            "현재 권한과 과업",
            power_entries,
            note=(
                "지명·내정만으로 현재 권한을 생성하지 않습니다."
                if not power_entries
                else "명시적으로 검증된 현재 권한·책임만 표시합니다."
            ),
        ),
        _section(
            "appointment_logic",
            "임명 논리",
            appointment_logic_entries,
            note=(
                "출처가 귀속된 임명 논리·평판 주장만 표시합니다."
                if appointment_logic_entries
                else "검토된 임명 논리 근거가 없습니다."
            ),
        ),
        _section(
            "decision_episodes",
            "의사결정 에피소드",
            episode_entries,
            status="AVAILABLE" if episode_entries else "UNKNOWN",
            note=None if episode_entries else "검토된 의사결정 에피소드가 없습니다.",
        ),
        _section(
            "repeated_patterns",
            "반복 패턴",
            [],
            status="UNKNOWN",
            note=(
                "반복 패턴은 별도 검토된 패턴 근거가 필요하며, 최소 2개의 독립 "
                "의사결정 에피소드만으로도 자동 생성하지 않습니다."
            ),
        ),
        _section(
            "stakeholders",
            "이해관계자와 관계",
            stakeholder_entries,
            status="AVAILABLE" if stakeholder_entries else "UNKNOWN",
            note=(
                "CO_MENTION만 있는 관계는 이해관계자 관계로 승격하지 않습니다."
                if stakeholder_entries
                else "CO_MENTION을 제외한 검토된 typed relationship이 없습니다."
            ),
        ),
        _section(
            "controversies",
            "논란 및 반론",
            controversy_entries,
            status="PARTIAL" if controversy_entries else "UNKNOWN",
            note=(
                "명시적 논란 predicate 또는 SUPPORT/REFUTE가 함께 있는 주장만 표시합니다."
                if controversy_entries
                else "검토된 논란·반론 근거가 없습니다."
            ),
        ),
        _section(
            "hearing_questions",
            "인사청문·검증 질문",
            [],
            status="UNKNOWN",
            note="검토된 질문 artifact가 아직 없습니다.",
        ),
        _section(
            "forecast",
            "전망과 시나리오",
            [],
            status="UNKNOWN",
            note="검토된 가설·시나리오 artifact가 아직 없습니다.",
        ),
    ]

    limitations_entries: list[dict[str, Any]] = []
    for section in sections:
        if section["status"] == "UNKNOWN":
            limitations_entries.append(
                {
                    "id": f"limitation:section:{section['id']}",
                    "kind": "LIMITATION",
                    "title": f"{section['label']}: 검토된 근거 부족",
                    "epistemic_status": EpistemicStatus.UNKNOWN.value,
                    "claim_id": None,
                    "evidence_ids": [],
                    "source_ids": [],
                    "date": None,
                    "details": {"section_id": section["id"]},
                }
            )
    if person.identity_status != IdentityStatus.RESOLVED:
        limitations_entries.append(
            {
                "id": "limitation:identity-status",
                "kind": "LIMITATION",
                "title": f"Identity status is {person.identity_status.value}",
                "epistemic_status": EpistemicStatus.ENTITY_UNRESOLVED.value,
                "claim_id": None,
                "evidence_ids": [],
                "source_ids": [],
                "date": None,
                "details": {"identity_status": person.identity_status.value},
            }
        )
    for claim in claims:
        if claim.epistemic_status in {
            EpistemicStatus.UNKNOWN,
            EpistemicStatus.ENTITY_UNRESOLVED,
        }:
            limitations_entries.append(_claim_entry(claim, evidence_by_claim))

    sections.append(
        _section(
            "limitations",
            "한계 및 미확인",
            limitations_entries,
            status="AVAILABLE" if limitations_entries else "UNKNOWN",
            note=(
                "미확인 영역을 숨기지 않고 section coverage와 UNKNOWN claim을 그대로 "
                "노출합니다."
            ),
        )
    )

    statuses = [section["status"] for section in sections]
    return {
        "section_order": [section_id for section_id, _ in SECTION_DEFINITIONS],
        "sections": sections,
        "coverage": {
            "available": statuses.count("AVAILABLE"),
            "partial": statuses.count("PARTIAL"),
            "unknown": statuses.count("UNKNOWN"),
        },
        "semantics": "DERIVED_READ_MODEL_FROM_CANONICAL_EVIDENCE",
    }

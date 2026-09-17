from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any
from uuid import UUID

from packages.connectors.open_assembly_historical import (
    HISTORICAL_REVIEWED_INPUT_SCOPE,
    SOURCE_RECORD_IDENTITY_UNAVAILABLE,
)
from packages.domain.contracts import Claim, ClaimEvidence, Person, Source, SourcePolicy
from packages.domain.enums import (
    EpistemicStatus,
    EvidenceStance,
    IdentityStatus,
    PublicationStatus,
)
from packages.verification.assembly_base_profile import (
    ASSEMBLY_BASE_PROFILE_FIELDS,
    ASSEMBLY_BASE_PROFILE_SCOPE,
    ASSEMBLY_BASE_PROFILE_SEMANTIC_SCOPE,
    ASSEMBLY_BASE_PROFILE_SOURCE_CONTRACT,
)
from packages.verification.assembly_legislative_activity import (
    ASSEMBLY_LEGISLATIVE_PARTICIPATION_PREDICATE,
    ASSEMBLY_LEGISLATIVE_SOURCE_CONTRACT,
)

CHANGE_METHOD_VERSION = "change.role-sequence.v1"

SECTION_DEFINITIONS: tuple[tuple[str, str], ...] = (
    ("identity", "신원"),
    ("assembly_base_profile", "국회 기본 프로필"),
    ("summary", "한눈에 보는 요약"),
    ("career_timeline", "경력 타임라인"),
    ("recent_changes", "최근 변화"),
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

ASSEMBLY_MEMBER_SECTION_DEFINITIONS: tuple[tuple[str, str], ...] = (
    ("overview", "개요"),
    ("current_role", "현재 역할"),
    ("career_timeline", "경력 타임라인"),
    ("legislative_activity", "입법 활동"),
    ("recent_changes", "최근 변화"),
    ("limitations", "근거 범위와 한계"),
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
        "RESPONSE_TO_ALLEGATION",
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
    stances = {item.stance.value for item in evidence}
    details: dict[str, Any] = {
        "predicate": claim.predicate,
        "object_text": claim.object_text,
        "field_name": claim.qualifiers.get("field_name"),
        "publication_status": claim.publication_status.value,
        "asserted_as_true": claim.asserted_as_true,
        "resolution_note": claim.resolution_note,
    }
    if claim.predicate == ASSEMBLY_LEGISLATIVE_PARTICIPATION_PREDICATE:
        for key in (
            "bill_no",
            "proposed_date",
            "committee",
            "committee_id",
            "process_result",
            "detail_url",
            "participation_role",
        ):
            value = claim.qualifiers.get(key)
            if value is not None:
                details[key] = value
    return {
        "id": f"claim:{claim.id}",
        "kind": "CLAIM",
        "title": claim.proposition,
        "epistemic_status": claim.epistemic_status.value,
        "claim_id": str(claim.id),
        "evidence_ids": [str(item.id) for item in evidence],
        "source_ids": _ordered_unique([str(item.source_id) for item in evidence]),
        "evidence": [_evidence_trace(item) for item in evidence],
        "source_conflict": {"SUPPORT", "REFUTE"} <= stances,
        "date": claim.qualifiers.get("date") or claim.qualifiers.get("proposed_date"),
        "details": details,
    }


def _evidence_trace(item: ClaimEvidence) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "stance": item.stance.value,
        "source_id": str(item.source_id),
        "snapshot_id": str(item.snapshot_id) if item.snapshot_id else None,
        "feeder_observation_id": (
            str(item.feeder_observation_id) if item.feeder_observation_id else None
        ),
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


def _assembly_base_profile_entries(
    claims: Sequence[Claim],
    evidence_by_claim: Mapping[UUID, Sequence[ClaimEvidence]],
) -> list[dict[str, Any]]:
    field_order = {item.name: index for index, item in enumerate(ASSEMBLY_BASE_PROFILE_FIELDS)}
    selected = [
        claim
        for claim in claims
        if claim.qualifiers.get("source_contract") == ASSEMBLY_BASE_PROFILE_SOURCE_CONTRACT
        and claim.qualifiers.get("field_name") in field_order
    ]
    selected.sort(
        key=lambda item: (
            field_order[item.qualifiers["field_name"]],
            str(item.id),
        )
    )
    return [_claim_entry(claim, evidence_by_claim) for claim in selected]


def _discovery_facet_entry(
    claim: Claim,
    evidence_by_claim: Mapping[UUID, Sequence[ClaimEvidence]],
) -> dict[str, Any] | None:
    value = claim.object_text.strip()
    evidence = tuple(evidence_by_claim.get(claim.id, ()))
    if not value or not evidence:
        return None
    return {
        "value": value,
        "claim_id": str(claim.id),
        "evidence_ids": [str(item.id) for item in evidence],
        "source_ids": _ordered_unique([str(item.source_id) for item in evidence]),
        "as_of": claim.valid_from.date().isoformat(),
    }


def build_people_discovery_projection(
    person: Person,
    claims: Sequence[Claim],
    evidence_by_claim: Mapping[UUID, Sequence[ClaimEvidence]],
) -> dict[str, Any]:
    """Build the bounded list projection from already publication-gated Claim/Evidence.

    This intentionally accepts canonical Claims and ClaimEvidence rather than observations. A
    facet is available only when exactly one current, asserted Assembly roster Claim supplies its
    value. Multiple current Claims are ambiguous, even when their text happens to match.
    """

    field_definitions = {item.name: item for item in ASSEMBLY_BASE_PROFILE_FIELDS}
    field_claims: dict[str, list[Claim]] = {name: [] for name in field_definitions}
    role_claims: list[Claim] = []
    for claim in claims:
        if (
            claim.person_id != person.id
            or claim.superseded_at is not None
            or claim.publication_status != PublicationStatus.PUBLISHED
            or claim.epistemic_status != EpistemicStatus.FACT
            or not claim.asserted_as_true
        ):
            continue
        is_current_assembly_roster_claim = (
            claim.qualifiers.get("source_contract") == ASSEMBLY_BASE_PROFILE_SOURCE_CONTRACT
            and claim.qualifiers.get("source_scope") == ASSEMBLY_BASE_PROFILE_SCOPE
            and claim.qualifiers.get("semantic_scope") == ASSEMBLY_BASE_PROFILE_SEMANTIC_SCOPE
        )
        if is_current_assembly_roster_claim:
            field_name = claim.qualifiers.get("field_name")
            definition = field_definitions.get(field_name or "")
            if (
                isinstance(field_name, str)
                and definition is not None
                and claim.predicate == definition.predicate
            ):
                field_claims[field_name].append(claim)
            elif (
                claim.predicate == "HELD_ROLE"
                and claim.qualifiers.get("provider_record_key")
            ):
                role_claims.append(claim)
        elif (
            claim.predicate == "HELD_ROLE"
            and claim.qualifiers.get("source_contract")
            in {None, ASSEMBLY_BASE_PROFILE_SOURCE_CONTRACT}
            and claim.qualifiers.get("source_scope") == ASSEMBLY_BASE_PROFILE_SCOPE
            and claim.qualifiers.get("provider_record_key")
            and claim.qualifiers.get("semantic_scope")
            in {None, ASSEMBLY_BASE_PROFILE_SEMANTIC_SCOPE}
        ):
            role_claims.append(claim)

    facets: dict[str, dict[str, Any] | None] = {
        "role": None,
        **{name: None for name in field_definitions},
    }
    missing_fields: list[str] = []
    ambiguous_fields: list[str] = []

    if len(role_claims) == 1:
        facets["role"] = _discovery_facet_entry(role_claims[0], evidence_by_claim)
        if facets["role"] is None:
            missing_fields.append("role")
    elif not role_claims:
        missing_fields.append("role")
    else:
        ambiguous_fields.append("role")

    for field_definition in ASSEMBLY_BASE_PROFILE_FIELDS:
        candidates = field_claims[field_definition.name]
        if len(candidates) == 1:
            facets[field_definition.name] = _discovery_facet_entry(
                candidates[0], evidence_by_claim
            )
            if facets[field_definition.name] is None:
                missing_fields.append(field_definition.name)
        elif not candidates:
            missing_fields.append(field_definition.name)
        else:
            ambiguous_fields.append(field_definition.name)

    selected_facets = [item for item in facets.values() if item is not None]
    as_of_values = {item["as_of"] for item in selected_facets}
    as_of = next(iter(as_of_values)) if len(as_of_values) == 1 else None
    evidence_ids = _ordered_unique(
        [evidence_id for item in selected_facets for evidence_id in item["evidence_ids"]]
    )
    source_ids = _ordered_unique(
        [source_id for item in selected_facets for source_id in item["source_ids"]]
    )
    return {
        "facets": facets,
        "as_of": as_of,
        "evidence_ids": evidence_ids,
        "source_ids": source_ids,
        "missing_fields": missing_fields,
        "ambiguous_fields": ambiguous_fields,
    }


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
    claims: Sequence[Claim],
    evidence_by_claim: Mapping[UUID, Sequence[ClaimEvidence]],
) -> list[dict[str, Any]]:
    claims_by_id = {str(claim.id): claim for claim in claims}
    entries: list[dict[str, Any]] = []
    for episode in decision_episodes:
        claim_id = episode.get("claim_id")
        raw_evidence_ids = [str(item) for item in episode.get("evidence_ids", [])]
        if not claim_id or not raw_evidence_ids or len(set(raw_evidence_ids)) != len(
            raw_evidence_ids
        ):
            continue
        claim = claims_by_id.get(str(claim_id))
        if claim is None or claim.publication_status.value != "PUBLISHED":
            continue

        evidence_by_id = {
            str(item.id): item for item in evidence_by_claim.get(claim.id, ())
        }
        selected_evidence = tuple(
            evidence_by_id[item_id]
            for item_id in raw_evidence_ids
            if item_id in evidence_by_id
        )
        if len(selected_evidence) != len(raw_evidence_ids):
            continue

        entry = _claim_entry(claim, {claim.id: selected_evidence})
        entry.update(
            {
                "id": f"episode:{episode['id']}",
                "kind": "DECISION_EPISODE",
                "title": episode["description"],
                "details": entry["details"]
                | {
                    "action": episode.get("action"),
                    "target": episode.get("target"),
                    "outcome": episode.get("outcome"),
                    "independent_origin_ids": [
                        str(item) for item in episode.get("independent_origin_ids", [])
                    ],
                },
            }
        )
        entries.append(entry)
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
        if any(evidence_id not in evidence_by_id for evidence_id in evidence_ids):
            continue
        source_ids = _ordered_unique(
            [str(evidence_by_id[evidence_id].source_id) for evidence_id in evidence_ids]
        )
        if not source_ids:
            continue
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


def _explicit_claim_date(claim: Claim) -> date | None:
    value = claim.qualifiers.get("date")
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _assembly_role_entries(
    claims: Sequence[Claim],
    evidence_by_claim: Mapping[UUID, Sequence[ClaimEvidence]],
) -> list[dict[str, Any]]:
    selected = [
        claim
        for claim in claims
        if claim.predicate == "HELD_ROLE"
        and claim.qualifiers.get("source_contract")
        in {None, ASSEMBLY_BASE_PROFILE_SOURCE_CONTRACT}
        and claim.qualifiers.get("source_scope") == ASSEMBLY_BASE_PROFILE_SCOPE
        and claim.qualifiers.get("provider_record_key")
    ]
    selected.sort(key=lambda item: (item.qualifiers.get("date", ""), str(item.id)))
    return [_claim_entry(claim, evidence_by_claim) for claim in selected]


def _assembly_dated_career_entries(
    claims: Sequence[Claim],
    evidence_by_claim: Mapping[UUID, Sequence[ClaimEvidence]],
) -> list[dict[str, Any]]:
    selected: list[Claim] = []
    for claim in claims:
        if claim.predicate not in CAREER_PREDICATES:
            continue
        if _explicit_claim_date(claim) is None:
            continue
        if (
            claim.qualifiers.get("source_contract") == ASSEMBLY_BASE_PROFILE_SOURCE_CONTRACT
            and claim.qualifiers.get("source_scope") == ASSEMBLY_BASE_PROFILE_SCOPE
        ):
            continue
        selected.append(claim)
    selected.sort(key=lambda item: (_explicit_claim_date(item) or date.min, str(item.id)))
    return [_claim_entry(claim, evidence_by_claim) for claim in selected]


def _assembly_activity_entries(
    claims: Sequence[Claim],
    evidence_by_claim: Mapping[UUID, Sequence[ClaimEvidence]],
) -> list[dict[str, Any]]:
    selected = [
        claim
        for claim in claims
        if claim.predicate == ASSEMBLY_LEGISLATIVE_PARTICIPATION_PREDICATE
        and claim.qualifiers.get("source_contract") == ASSEMBLY_LEGISLATIVE_SOURCE_CONTRACT
        and claim.qualifiers.get("provider_identity_namespace") == "assembly_mona_cd"
    ]
    selected.sort(
        key=lambda item: (
            item.qualifiers.get("proposed_date", ""),
            item.qualifiers.get("bill_id", ""),
            item.qualifiers.get("participation_role", ""),
            str(item.id),
        )
    )
    return [_claim_entry(claim, evidence_by_claim) for claim in selected]


def _assembly_limitation(
    limitation_id: str,
    title: str,
    *,
    section_id: str,
) -> dict[str, Any]:
    return {
        "id": f"limitation:{limitation_id}",
        "kind": "LIMITATION",
        "title": title,
        "epistemic_status": EpistemicStatus.UNKNOWN.value,
        "claim_id": None,
        "evidence_ids": [],
        "source_ids": [],
        "date": None,
        "details": {"section_id": section_id},
    }


def _normalized_role_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _eligible_assembly_change_claims(
    person: Person,
    claims: Sequence[Claim],
    evidence_by_claim: Mapping[UUID, Sequence[ClaimEvidence]],
    sources: Mapping[UUID, Source] | None,
    policies: Mapping[UUID, SourcePolicy] | None,
) -> list[tuple[Claim, date, tuple[ClaimEvidence, ...]]]:
    if person.identity_status != IdentityStatus.RESOLVED:
        return []
    if sources is None or policies is None:
        return []

    eligible: list[tuple[Claim, date, tuple[ClaimEvidence, ...]]] = []
    for claim in claims:
        if claim.person_id != person.id:
            continue
        if (
            claim.superseded_at is not None
            or claim.publication_status != PublicationStatus.PUBLISHED
            or claim.epistemic_status != EpistemicStatus.FACT
            or not claim.asserted_as_true
            or claim.predicate not in {"HELD_ROLE", "APPOINTED_AS"}
            or not _normalized_role_text(claim.object_text)
            or claim.qualifiers.get("change_input_scope")
            != HISTORICAL_REVIEWED_INPUT_SCOPE
            or claim.qualifiers.get("provider_record_identity")
            != SOURCE_RECORD_IDENTITY_UNAVAILABLE
            or not claim.qualifiers.get("mona_cd")
            or not claim.qualifiers.get("profile_unit_cd")
            or not claim.qualifiers.get("source_record_fingerprint")
        ):
            continue
        claim_date = _explicit_claim_date(claim)
        if claim_date is None:
            continue

        evidence = tuple(evidence_by_claim.get(claim.id, ()))
        stances = {item.stance for item in evidence}
        if EvidenceStance.REFUTE in stances:
            continue
        supporting = tuple(
            item
            for item in evidence
            if item.stance == EvidenceStance.SUPPORT
            and item.snapshot_id is not None
            and item.feeder_observation_id is not None
        )
        if not supporting:
            continue
        permitted_supporting = tuple(
            item
            for item in supporting
            if (
                (source := sources.get(item.source_id)) is not None
                and (policy := policies.get(source.policy_id)) is not None
                and policy.can_store_metadata
            )
        )
        if not permitted_supporting:
            continue
        eligible.append((claim, claim_date, evidence))
    eligible.sort(key=lambda item: (item[1], str(item[0].id)))
    return eligible


def _same_provider_term(earlier: Claim, later: Claim) -> bool:
    return (
        earlier.qualifiers.get("mona_cd") == later.qualifiers.get("mona_cd")
        and earlier.qualifiers.get("profile_unit_cd")
        == later.qualifiers.get("profile_unit_cd")
    )


def _change_input(
    claim: Claim,
    claim_date: date,
    evidence: Sequence[ClaimEvidence],
) -> dict[str, Any]:
    return {
        "claim_id": str(claim.id),
        "date": claim_date.isoformat(),
        "predicate": claim.predicate,
        "role_text": claim.object_text,
        "profile_unit_cd": claim.qualifiers.get("profile_unit_cd"),
        "profile_unit_nm": claim.qualifiers.get("profile_unit_nm"),
        "publication_status": claim.publication_status.value,
        "epistemic_status": claim.epistemic_status.value,
        "asserted_as_true": claim.asserted_as_true,
        "evidence_ids": [str(item.id) for item in evidence],
        "source_ids": _ordered_unique([str(item.source_id) for item in evidence]),
        "evidence": [_evidence_trace(item) for item in evidence],
    }


def _assembly_role_sequence_changes(
    person: Person,
    claims: Sequence[Claim],
    evidence_by_claim: Mapping[UUID, Sequence[ClaimEvidence]],
    sources: Mapping[UUID, Source] | None,
    policies: Mapping[UUID, SourcePolicy] | None,
) -> tuple[list[dict[str, Any]], int]:
    eligible = _eligible_assembly_change_claims(
        person, claims, evidence_by_claim, sources, policies
    )
    changes: list[dict[str, Any]] = []
    for left_index, (earlier, earlier_date, earlier_evidence) in enumerate(eligible):
        for later, later_date, later_evidence in eligible[left_index + 1 :]:
            if later_date <= earlier_date:
                continue
            if _same_provider_term(earlier, later):
                continue
            if earlier.qualifiers.get("mona_cd") != later.qualifiers.get("mona_cd"):
                continue
            if _normalized_role_text(earlier.object_text) == _normalized_role_text(
                later.object_text
            ):
                continue

            ordered_claim_ids = f"{earlier.id}|{later.id}"
            presentation_key = hashlib.sha256(
                f"{CHANGE_METHOD_VERSION}|{ordered_claim_ids}".encode()
            ).hexdigest()
            earlier_input = _change_input(earlier, earlier_date, earlier_evidence)
            later_input = _change_input(later, later_date, later_evidence)
            evidence = [*earlier_evidence, *later_evidence]
            evidence_ids = _ordered_unique([str(item.id) for item in evidence])
            source_ids = _ordered_unique([str(item.source_id) for item in evidence])
            changes.append(
                {
                    "id": f"change:{presentation_key}",
                    "kind": "CHANGE",
                    "title": "국회 이력 표시값의 변화",
                    "epistemic_status": None,
                    "claim_id": None,
                    "evidence_ids": evidence_ids,
                    "source_ids": source_ids,
                    "evidence": [_evidence_trace(item) for item in evidence],
                    "source_conflict": False,
                    "date": later_date.isoformat(),
                    "details": {
                        "presentation_key": presentation_key,
                        "method_version": CHANGE_METHOD_VERSION,
                        "person_id": str(person.id),
                        "derived_type": "ROLE_SEQUENCE_CHANGE",
                        "earlier": earlier_input,
                        "later": later_input,
                        "provider_identity": {
                            "namespace": "open.assembly.go.kr",
                            "mona_cd": earlier.qualifiers.get("mona_cd"),
                        },
                        "input_scope": {
                            "mode": HISTORICAL_REVIEWED_INPUT_SCOPE,
                            "provider_record_identity": SOURCE_RECORD_IDENTITY_UNAVAILABLE,
                            "term_codes": [
                                earlier.qualifiers.get("profile_unit_cd"),
                                later.qualifiers.get("profile_unit_cd"),
                            ],
                            "correction_semantics": "IMMUTABLE_SNAPSHOT_ONLY",
                        },
                        "coverage": {
                            "eligible_claim_count": len(eligible),
                            "comparison": "different explicit dates and different PROFILE_SJ display text",
                        },
                        "derived_reason": (
                            f"{earlier_date.isoformat()} {earlier.qualifiers.get('profile_unit_nm', '')} "
                            f"PROFILE_SJ '{earlier.object_text}' → "
                            f"{later_date.isoformat()} {later.qualifiers.get('profile_unit_nm', '')} "
                            f"PROFILE_SJ '{later.object_text}'"
                        ).strip(),
                        "limitations": [
                            "이 결과는 두 snapshot의 날짜가 있는 PROFILE_SJ 표시값 순서 차이만 나타냅니다.",
                            "provider row ID와 correction/replacement 의미를 추정하지 않으며, 원래 Claim을 수정하지 않습니다.",
                            "실제 후속 인사 상태나 배경, 정당·지역구의 별도 변화는 확정하지 않습니다.",
                        ],
                    },
                }
            )
    return changes, len(eligible)


def build_profile_projection(
    person: Person,
    claims: Sequence[Claim],
    evidence_by_claim: Mapping[UUID, Sequence[ClaimEvidence]],
    relationships: Sequence[dict[str, Any]],
    decision_episodes: Sequence[dict[str, Any]],
    *,
    sources: Mapping[UUID, Source] | None = None,
    policies: Mapping[UUID, SourcePolicy] | None = None,
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

    assembly_base_profile_entries = _assembly_base_profile_entries(claims, evidence_by_claim)
    summary_entries = _claim_entries_for(claims, evidence_by_claim, SUMMARY_PREDICATES)
    timeline_entries = _claim_entries_for(claims, evidence_by_claim, CAREER_PREDICATES)
    recent_changes, eligible_change_claim_count = _assembly_role_sequence_changes(
        person, claims, evidence_by_claim, sources, policies
    )
    power_entries = _claim_entries_for(claims, evidence_by_claim, POWER_TASK_PREDICATES)
    appointment_logic_entries = _claim_entries_for(
        claims, evidence_by_claim, APPOINTMENT_LOGIC_PREDICATES
    )
    episode_entries = _decision_episode_entries(decision_episodes, claims, evidence_by_claim)
    stakeholder_entries = _relationship_entries(relationships, evidence_by_claim)
    controversy_entries = _controversy_entries(claims, evidence_by_claim)

    assembly_role_entries = _assembly_role_entries(claims, evidence_by_claim)
    assembly_career_entries = _assembly_dated_career_entries(claims, evidence_by_claim)
    assembly_activity_entries = _assembly_activity_entries(claims, evidence_by_claim)
    is_assembly_member = bool(
        assembly_base_profile_entries or assembly_role_entries or assembly_activity_entries
    )

    if is_assembly_member:
        overview_entries = [
            item
            for item in assembly_base_profile_entries
            if item.get("details", {}).get("field_name") in {"party", "district", "reelection"}
        ]
        committee_entries = [
            item
            for item in assembly_base_profile_entries
            if item.get("details", {}).get("field_name") == "committees"
        ]
        overview_fields = {
            item.get("details", {}).get("field_name") for item in overview_entries
        }
        current_role_entries = [*assembly_role_entries, *committee_entries]
        current_role_fields: set[str] = set()
        if assembly_role_entries:
            current_role_fields.add("role")
        if committee_entries:
            current_role_fields.add("committees")
        assembly_sections: list[dict[str, Any]] = [
            _section(
                "overview",
                "개요",
                overview_entries,
                status=(
                    "AVAILABLE"
                    if overview_fields >= {"party", "district", "reelection"}
                    else "PARTIAL"
                    if overview_entries
                    else "UNKNOWN"
                ),
                note=(
                    "현재 published Assembly Base Profile Claim만 빠른 개요로 투영합니다."
                    if overview_entries
                    else "현재 published Assembly Base Profile 개요 Claim이 없습니다."
                ),
            ),
            _section(
                "current_role",
                "현재 역할",
                current_role_entries,
                status=(
                    "AVAILABLE"
                    if current_role_fields >= {"role", "committees"}
                    else "PARTIAL"
                    if current_role_entries
                    else "UNKNOWN"
                ),
                note=(
                    "현재 역할과 위원회 소속만 published Claim에서 표시하며, 정책 성향이나 영향력은 해석하지 않습니다."
                    if current_role_entries
                    else "현재 역할·위원회 published Claim이 없습니다."
                ),
            ),
            _section(
                "career_timeline",
                "경력 타임라인",
                assembly_career_entries,
                status="AVAILABLE" if assembly_career_entries else "PARTIAL",
                note=(
                    "명시적 날짜가 있는 reviewed career Claim만 시간순으로 표시합니다."
                    if assembly_career_entries
                    else "현재 roster는 현직 상태만 나타내며, 과거 경력 전체를 의미하지 않습니다."
                ),
            ),
            _section(
                "legislative_activity",
                "입법 활동",
                assembly_activity_entries,
                status="AVAILABLE" if assembly_activity_entries else "UNKNOWN",
                note=(
                    "공식 의안정보의 정확한 MONA_CD 연결 Claim을 대표 발의와 공동 발의로 구분해 표시합니다."
                    if assembly_activity_entries
                    else "현재 published 법안 참여 Claim이 없습니다."
                ),
            ),
        ]
        if recent_changes:
            assembly_sections.append(
                _section(
                    "recent_changes",
                    "최근 변화",
                    recent_changes,
                    status="AVAILABLE",
                    note="서로 다른 날짜의 reviewed historical Claim 쌍에서만 변화로 표시합니다.",
                )
            )

        assembly_limitations: list[dict[str, Any]] = []
        for field_name, label in (
            ("party", "정당"),
            ("district", "지역구"),
            ("reelection", "초선·재선"),
        ):
            if field_name not in overview_fields:
                assembly_limitations.append(
                    _assembly_limitation(
                        f"overview-{field_name}",
                        f"개요의 {label} Claim이 현재 공개 profile에 없습니다.",
                        section_id="overview",
                    )
                )
        if "committees" not in current_role_fields:
            assembly_limitations.append(
                _assembly_limitation(
                    "current-role-committees",
                    "현재 위원회 Claim이 현재 공개 profile에 없습니다.",
                    section_id="current_role",
                )
            )
        if not assembly_career_entries:
            assembly_limitations.append(
                _assembly_limitation(
                    "career-coverage",
                    "국회 historical career coverage가 없어 현직 roster를 경력 전체로 표시하지 않습니다.",
                    section_id="career_timeline",
                )
            )
        if not recent_changes:
            assembly_limitations.append(
                _assembly_limitation(
                    "recent-changes-none",
                    "확인된 최근 변경 기록 없음",
                    section_id="recent_changes",
                )
            )
        if not assembly_activity_entries:
            assembly_limitations.append(
                _assembly_limitation(
                    "legislative-activity-none",
                    "현재 공개된 법안 참여 Claim이 없습니다.",
                    section_id="legislative_activity",
                )
            )
        for claim in claims:
            if claim.epistemic_status in {
                EpistemicStatus.UNKNOWN,
                EpistemicStatus.ENTITY_UNRESOLVED,
            }:
                assembly_limitations.append(_claim_entry(claim, evidence_by_claim))
        assembly_sections.append(
            _section(
                "limitations",
                "근거 범위와 한계",
                assembly_limitations,
                status="AVAILABLE" if assembly_limitations else "UNKNOWN",
                note="공개 화면은 현재 published Claim/Evidence 범위만 표시하며, 빈 값을 추론으로 채우지 않습니다.",
            )
        )
        statuses = [section["status"] for section in assembly_sections]
        return {
            "profile_kind": "ASSEMBLY_MEMBER",
            "section_order": [section["id"] for section in assembly_sections],
            "sections": assembly_sections,
            "coverage": {
                "available": statuses.count("AVAILABLE"),
                "partial": statuses.count("PARTIAL"),
                "unknown": statuses.count("UNKNOWN"),
            },
            "semantics": "DERIVED_READ_MODEL_FROM_CANONICAL_EVIDENCE",
        }

    sections: list[dict[str, Any]] = [
        _section("identity", "신원", identity_entries, status="AVAILABLE", note=identity_note),
        _section(
            "assembly_base_profile",
            "국회 기본 프로필",
            assembly_base_profile_entries,
            status=(
                "AVAILABLE"
                if len(
                    {
                        item.get("details", {}).get("field_name")
                        for item in assembly_base_profile_entries
                    }
                ) == len(ASSEMBLY_BASE_PROFILE_FIELDS)
                else "PARTIAL"
                if assembly_base_profile_entries
                else "UNKNOWN"
            ),
            note=(
                "현재 국회 명부에서 제공된 기본 필드만 표시하며, 빠진 값은 추론하지 않습니다."
                if assembly_base_profile_entries
                else "현재 국회 명부 기본 프로필 Claim이 없습니다."
            ),
        ),
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
            "recent_changes",
            "최근 변화",
            recent_changes,
            status=(
                "AVAILABLE"
                if recent_changes
                else "PARTIAL"
                if eligible_change_claim_count >= 2
                else "UNKNOWN"
            ),
            note=(
                "서로 다른 날짜의 Assembly historical PROFILE_SJ 표시값을 비교한 읽기 전용 결과입니다."
                if recent_changes
                else (
                    "검토된 Assembly historical packet에서 비교 가능한 두 개의 날짜 있는 Claim이 "
                    "없거나, 같은 provider term·동일 표시값만 있습니다."
                    if eligible_change_claim_count
                    else "검토된 Assembly historical packet의 CHANGE 입력 근거가 없습니다."
                )
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

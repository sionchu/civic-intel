from __future__ import annotations

from dataclasses import dataclass

from packages.domain.enums import IdentityStatus

from .cross_lane_identity import (
    CrossLaneIdentityDecision,
    CrossLaneIdentityEvidence,
    resolve_cross_lane_identity,
)
from .identity import IdentityCandidate


class ProfileTargetBuildError(ValueError):
    pass


def _ordered_unique(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if value))


@dataclass(frozen=True)
class ProfileTargetObservation:
    lane: str
    candidate: IdentityCandidate
    source_refs: tuple[str, ...]
    discovery_reasons: tuple[str, ...] = ()
    appointment_target_slugs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.lane.strip():
            raise ValueError("profile target observation requires lane")
        if not self.source_refs or any(not item.strip() for item in self.source_refs):
            raise ValueError("profile target observation requires non-empty source_refs")
        if any(not item.strip() for item in self.discovery_reasons):
            raise ValueError("discovery reasons cannot contain blank values")
        if any(not item.strip() for item in self.appointment_target_slugs):
            raise ValueError("appointment target slugs cannot contain blank values")

    def to_dict(self) -> dict[str, object]:
        return {
            "lane": self.lane,
            "canonical_name": self.candidate.canonical_name,
            "aliases": list(self.candidate.aliases),
            "birth_date": self.candidate.birth_date.isoformat() if self.candidate.birth_date else None,
            "office": self.candidate.office,
            "organization": self.candidate.organization,
            "career_anchors": list(self.candidate.career_anchors),
            "source_refs": list(self.source_refs),
            "discovery_reasons": list(self.discovery_reasons),
            "appointment_target_slugs": list(self.appointment_target_slugs),
        }


@dataclass(frozen=True)
class ProfileTargetLink:
    observation: ProfileTargetObservation
    evidence: tuple[CrossLaneIdentityEvidence, ...]


@dataclass(frozen=True)
class ResolvedProfileTargetLink:
    observation: ProfileTargetObservation
    evidence: tuple[CrossLaneIdentityEvidence, ...]
    decision: CrossLaneIdentityDecision

    def to_dict(self) -> dict[str, object]:
        return {
            "observation": self.observation.to_dict(),
            "identity": {
                "status": self.decision.status.value,
                "decision_class": self.decision.decision_class.value,
                "decision_scope": "RESEARCH_IDENTITY_ONLY",
                "reasons": list(self.decision.reasons),
                "evidence_types": [item.value for item in self.decision.evidence_types],
                "evidence_source_refs": list(
                    _ordered_unique(tuple(item.source_ref for item in self.evidence))
                ),
            },
        }


@dataclass(frozen=True)
class ProfileResearchTarget:
    primary: ProfileTargetObservation
    linked: tuple[ResolvedProfileTargetLink, ...]
    source_lanes: tuple[str, ...]
    source_refs: tuple[str, ...]
    discovery_reasons: tuple[str, ...]
    appointment_target_slugs: tuple[str, ...]

    @property
    def canonical_name(self) -> str:
        return self.primary.candidate.canonical_name

    def to_dict(self) -> dict[str, object]:
        return {
            "canonical_name": self.canonical_name,
            "identity_status": IdentityStatus.RESOLVED.value,
            "primary": self.primary.to_dict(),
            "linked_observations": [item.to_dict() for item in self.linked],
            "source_lanes": list(self.source_lanes),
            "source_refs": list(self.source_refs),
            "discovery_reasons": list(self.discovery_reasons),
            "appointment_target_slugs": list(self.appointment_target_slugs),
            "semantics": (
                "Resolved feeder observations form a profiler research target only. "
                "They do not create a Person merge, appointment probability, or publishable FACT by themselves."
            ),
        }


def build_profile_research_target(
    primary: ProfileTargetObservation,
    links: tuple[ProfileTargetLink, ...] = (),
) -> ProfileResearchTarget:
    resolved_links: list[ResolvedProfileTargetLink] = []
    observations = [primary]
    evidence_source_refs: list[str] = []

    for link in links:
        decision = resolve_cross_lane_identity(
            primary.candidate,
            link.observation.candidate,
            link.evidence,
        )
        if decision.status != IdentityStatus.RESOLVED:
            raise ProfileTargetBuildError(
                "profile research target requires every cross-lane observation to be RESOLVED"
            )
        resolved_links.append(
            ResolvedProfileTargetLink(
                observation=link.observation,
                evidence=link.evidence,
                decision=decision,
            )
        )
        observations.append(link.observation)
        evidence_source_refs.extend(item.source_ref for item in link.evidence)

    source_lanes = _ordered_unique(tuple(item.lane for item in observations))
    source_refs = _ordered_unique(
        tuple(ref for item in observations for ref in item.source_refs)
        + tuple(evidence_source_refs)
    )
    discovery_reasons = _ordered_unique(
        tuple(reason for item in observations for reason in item.discovery_reasons)
    )
    appointment_target_slugs = _ordered_unique(
        tuple(slug for item in observations for slug in item.appointment_target_slugs)
    )

    return ProfileResearchTarget(
        primary=primary,
        linked=tuple(resolved_links),
        source_lanes=source_lanes,
        source_refs=source_refs,
        discovery_reasons=discovery_reasons,
        appointment_target_slugs=appointment_target_slugs,
    )

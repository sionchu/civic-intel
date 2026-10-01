from __future__ import annotations

from uuid import UUID

from packages.application.ports import UnitOfWork
from packages.domain.contracts import ClaimEvidence
from packages.domain.enums import IdentityStatus
from packages.domain.source_contracts import ALIO_ITEM12_SOURCE_CONTRACT
from packages.rendering.alio_organization_content import (
    ALIO_CLASSIFICATION_PREDICATE,
    ALIO_EXECUTIVE_PREDICATE,
)
from packages.rendering.governance_ontology import (
    add_reviewed_person_roles,
    build_organization_governance_ontology,
    build_person_governance_ontology,
)
from packages.rendering.gukgam_organization_binding_review import (
    GukgamOrganizationBindingPreflightError,
    build_gukgam_organization_binding_preflight,
    build_gukgam_organization_binding_review,
)
from packages.rendering.gukgam_organization_claim import (
    GUKGAM_AUDIT_TARGET_PREDICATE,
    build_gukgam_audit_target_projection,
)
from packages.rendering.gukgam_schedule_review import (
    GukgamScheduleReviewReport,
    load_current_gukgam_schedule_review,
)
from packages.rendering.money_projection import build_alio_head_expense_money_from_claims
from packages.rendering.profile_projection import (
    build_people_discovery_projection,
    build_profile_projection,
)
from packages.verification.claims import validate_claim_publication


class PublicApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message


class DirectoryView:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    def person_or_404(self, person_id: UUID, *, public: bool = False):
        person = self.uow.public.person(person_id)
        if not person or (
            public
            and (
                person.identity_status != IdentityStatus.RESOLVED
                or person.superseded_at is not None
                or (not self.uow.public.person_is_public(person.id))
            )
        ):
            raise PublicApiError(404, "PUBLIC_RECORD_NOT_FOUND", "The public record was not found.")
        return person

    def organization_or_404(self, organization_id: UUID, *, public: bool = False):
        organization = self.uow.public.organization(organization_id)
        if not organization or (public and organization.superseded_at is not None):
            raise PublicApiError(404, "PUBLIC_RECORD_NOT_FOUND", "The public record was not found.")
        return organization

    def policy_summary(self, policy) -> dict[str, str]:
        collection_permitted = policy.can_fetch and policy.collection_mode.value not in {
            "BLOCKED",
            "DISCOVERY_ONLY",
        }
        return {
            "collection": "PERMITTED" if collection_permitted else "NOT_PERMITTED",
            "metadata_storage": "PERMITTED" if policy.can_store_metadata else "NOT_PERMITTED",
            "fulltext_storage": "PERMITTED" if policy.can_store_fulltext else "NOT_PERMITTED",
            "excerpt_display": "PERMITTED" if policy.can_show_excerpt else "NOT_PERMITTED",
        }

    def source_payload(self, source, policy) -> dict:
        return {
            "id": str(source.id),
            "url": str(source.url),
            "title": source.title,
            "publisher": source.publisher,
            "published_at": source.published_at.isoformat() if source.published_at else None,
            "source_class": policy.source_class,
            "license": policy.license,
            "terms_checked_at": policy.terms_checked_at.isoformat()
            if policy.terms_checked_at
            else None,
            "policy_summary": self.policy_summary(policy),
        }

    def claim_payload(self, claim, evidence=None) -> dict:
        selected_evidence = self.uow.public.evidence_for(claim.id) if evidence is None else evidence
        sources = self.uow.public.sources(item.source_id for item in selected_evidence)
        policies = self.uow.public.policies(source.policy_id for source in sources.values())
        if claim.person_id is not None:
            subject = self.person_or_404(claim.person_id)
        elif claim.organization_id is not None:
            subject = self.organization_or_404(claim.organization_id)
        else:
            raise PublicApiError(
                503, "SERVICE_UNAVAILABLE", "The public data service is temporarily unavailable."
            )
        gate = validate_claim_publication(claim, subject, selected_evidence, sources, policies)
        if not gate.publishable:
            raise PublicApiError(
                503, "SERVICE_UNAVAILABLE", "The public data service is temporarily unavailable."
            )
        stances = {item.stance.value for item in selected_evidence}
        return claim.model_dump(mode="json") | {
            "evidence": [item.model_dump(mode="json") for item in selected_evidence],
            "source_ids": sorted({str(item.source_id) for item in selected_evidence}),
            "source_conflict": {"SUPPORT", "REFUTE"} <= stances,
        }

    def people(self) -> list[dict]:
        public_people = self.uow.public.public_people()
        contexts = self.uow.public.published_person_claim_contexts(
            item.id for item in public_people
        )
        all_evidence = [
            evidence
            for _, evidence_by_claim in contexts.values()
            for evidence in evidence_by_claim.values()
        ]
        source_map = self.uow.public.sources(
            item.source_id for evidence in all_evidence for item in evidence
        )
        policy_map = self.uow.public.policies(source.policy_id for source in source_map.values())
        payload: list[dict] = []
        for item in public_people:
            claims, evidence_by_claim = contexts.get(item.id, ((), {}))
            eligible_claims = []
            eligible_evidence = {}
            for claim in claims:
                evidence = list(evidence_by_claim.get(claim.id, ()))
                if validate_claim_publication(
                    claim, item, evidence, source_map, policy_map
                ).publishable:
                    eligible_claims.append(claim)
                    eligible_evidence[claim.id] = tuple(evidence)
            payload.append(
                item.model_dump(mode="json")
                | {
                    "discovery": build_people_discovery_projection(
                        item, eligible_claims, eligible_evidence
                    )
                }
            )
        return payload

    def person(self, person_id: UUID) -> dict:
        item = self.person_or_404(person_id, public=True)
        published_claims = self.uow.public.claims(person_id, True, current_only=True)
        evidence_by_claim = {
            claim.id: self.uow.public.evidence_for(claim.id) for claim in published_claims
        }
        person_claims = [
            self.claim_payload(claim, evidence_by_claim[claim.id]) for claim in published_claims
        ]
        source_ids = {
            item.source_id
            for claim_evidence in evidence_by_claim.values()
            for item in claim_evidence
        }
        source_map = self.uow.public.sources(source_ids)
        policy_map = self.uow.public.policies(source.policy_id for source in source_map.values())
        relationships = self.uow.public.relationships(person_id)
        decision_episodes = self.uow.public.decision_episodes(person_id)
        profile = build_profile_projection(
            item,
            published_claims,
            evidence_by_claim,
            relationships,
            decision_episodes,
            sources=source_map,
            policies=policy_map,
        )
        return item.model_dump(mode="json") | {
            "claims": person_claims,
            "profile": profile,
            "relationship_ids": [relationship["id"] for relationship in relationships],
            "asset_disclosure_ids": [],
        }

    def reviewed_role_graph(self, graph, *, person_id=None, organization_id=None):
        contexts = self.uow.public.reviewed_person_role_contexts(
            person_id=person_id, organization_id=organization_id
        )
        evidence = [item for _, _, _, items in contexts for item in items]
        sources = self.uow.public.sources(item.source_id for item in evidence)
        policies = self.uow.public.policies(item.policy_id for item in sources.values())
        eligible = [
            context
            for context in contexts
            if validate_claim_publication(
                context[0], context[1], list(context[3]), sources, policies
            ).publishable
        ]
        return add_reviewed_person_roles(graph, eligible).to_dict()

    def person_ontology(self, person_id: UUID) -> dict:
        item = self.person_or_404(person_id, public=True)
        contexts = self.uow.public.published_person_claim_contexts([person_id])
        claims, evidence_by_claim = contexts.get(person_id, ((), {}))
        all_evidence = [
            evidence for evidence_items in evidence_by_claim.values() for evidence in evidence_items
        ]
        source_map = self.uow.public.sources(evidence.source_id for evidence in all_evidence)
        policy_map = self.uow.public.policies(source.policy_id for source in source_map.values())
        eligible_claims = []
        eligible_evidence = {}
        for claim in claims:
            evidence = list(evidence_by_claim.get(claim.id, ()))
            if validate_claim_publication(
                claim, item, evidence, source_map, policy_map
            ).publishable:
                eligible_claims.append(claim)
                eligible_evidence[claim.id] = tuple(evidence)
        return self.reviewed_role_graph(
            build_person_governance_ontology(item, eligible_claims, eligible_evidence),
            person_id=person_id,
        )

    def organization_ontology(self, organization_id: UUID) -> dict:
        item = self.organization_or_404(organization_id, public=True)
        contexts = self.uow.public.published_organization_claim_contexts([organization_id])
        claims, evidence_by_claim = contexts.get(organization_id, ((), {}))
        all_evidence = [
            evidence for evidence_items in evidence_by_claim.values() for evidence in evidence_items
        ]
        source_map = self.uow.public.sources(evidence.source_id for evidence in all_evidence)
        policy_map = self.uow.public.policies(source.policy_id for source in source_map.values())
        eligible_claims = []
        eligible_evidence = {}
        for claim in claims:
            evidence = list(evidence_by_claim.get(claim.id, ()))
            if validate_claim_publication(
                claim, item, evidence, source_map, policy_map
            ).publishable:
                eligible_claims.append(claim)
                eligible_evidence[claim.id] = tuple(evidence)
        return self.reviewed_role_graph(
            build_organization_governance_ontology(item, eligible_claims, eligible_evidence),
            organization_id=organization_id,
        )

    def organizations(self) -> list[dict]:
        current_organizations = self.uow.public.public_organizations()
        contexts = self.uow.public.published_organization_claim_contexts(
            item.id for item in current_organizations
        )
        all_evidence = [
            evidence
            for _, evidence_by_claim in contexts.values()
            for evidence_items in evidence_by_claim.values()
            for evidence in evidence_items
        ]
        source_map = self.uow.public.sources(evidence.source_id for evidence in all_evidence)
        policy_map = self.uow.public.policies(source.policy_id for source in source_map.values())
        payload: list[dict] = []
        for item in current_organizations:
            claims, evidence_by_claim = contexts.get(item.id, ((), {}))
            eligible_claims = [
                claim
                for claim in claims
                if validate_claim_publication(
                    claim, item, list(evidence_by_claim.get(claim.id, ())), source_map, policy_map
                ).publishable
            ]
            if not eligible_claims:
                continue
            classification = next(
                (
                    claim
                    for claim in eligible_claims
                    if claim.predicate == ALIO_CLASSIFICATION_PREDICATE
                ),
                None,
            )
            executive_count = sum(
                claim.predicate == ALIO_EXECUTIVE_PREDICATE for claim in eligible_claims
            )
            as_of_values = sorted(
                {
                    claim.qualifiers["as_of"]
                    for claim in eligible_claims
                    if claim.qualifiers.get("as_of")
                }
            )
            payload.append(
                {
                    "id": str(item.id),
                    "name": item.name,
                    "classification": classification.object_text if classification else None,
                    "classification_code": classification.qualifiers.get("classification")
                    if classification
                    else None,
                    "executive_count": executive_count,
                    "published_claim_count": len(eligible_claims),
                    "as_of": as_of_values[-1] if as_of_values else None,
                    "evidence_count": sum(
                        len(evidence_by_claim.get(claim.id, ())) for claim in eligible_claims
                    ),
                }
            )
        return sorted(payload, key=lambda item: (item["name"], item["id"]))

    def gukgam_2026_targets(self) -> dict:
        current_organizations = self.uow.public.public_organizations()
        contexts = self.uow.public.published_organization_claim_contexts(
            item.id for item in current_organizations
        )
        gukgam_contexts = {}
        all_evidence: list[ClaimEvidence] = []
        for organization_id, (claims, evidence_by_claim) in contexts.items():
            candidate_claims = tuple(
                claim for claim in claims if claim.predicate == GUKGAM_AUDIT_TARGET_PREDICATE
            )
            if not candidate_claims:
                continue
            candidate_evidence = {
                claim.id: evidence_by_claim.get(claim.id, ()) for claim in candidate_claims
            }
            gukgam_contexts[organization_id] = (candidate_claims, candidate_evidence)
            all_evidence.extend(
                evidence for items in candidate_evidence.values() for evidence in items
            )
        source_map = self.uow.public.sources(evidence.source_id for evidence in all_evidence)
        policy_map = self.uow.public.policies(source.policy_id for source in source_map.values())
        return build_gukgam_audit_target_projection(
            current_organizations,
            gukgam_contexts,
            sources=source_map,
            policies=policy_map,
            year=2026,
        ).to_dict()

    def claims(self, person_id: UUID) -> list[dict]:
        self.person_or_404(person_id, public=True)
        return [
            self.claim_payload(item)
            for item in self.uow.public.claims(person_id, True, current_only=True)
        ]

    def organization(self, organization_id: UUID) -> dict:
        item = self.organization_or_404(organization_id, public=True)
        published_claims = self.uow.public.claims(
            published_only=True, current_only=True, organization_id=organization_id
        )
        return item.model_dump(mode="json") | {
            "claims": [self.claim_payload(claim) for claim in published_claims]
        }

    def organization_claims(self, organization_id: UUID) -> list[dict]:
        self.organization_or_404(organization_id, public=True)
        return [
            self.claim_payload(item)
            for item in self.uow.public.claims(
                published_only=True, current_only=True, organization_id=organization_id
            )
        ]

    def organization_money(
        self, organization_id: UUID, earlier_fiscal_year: int = 2024, later_fiscal_year: int = 2025
    ) -> dict:
        if earlier_fiscal_year >= later_fiscal_year:
            raise PublicApiError(
                422, "INVALID_INPUT", "The earlier fiscal year must precede the later fiscal year."
            )
        organization = self.organization_or_404(organization_id, public=True)
        published_claims = self.uow.public.claims(
            published_only=True, current_only=True, organization_id=organization_id
        )
        candidate_claims = [
            claim
            for claim in published_claims
            if claim.predicate == "DISCLOSED_BUSINESS_EXPENSE"
            and claim.qualifiers.get("source_contract") == ALIO_ITEM12_SOURCE_CONTRACT
        ]
        if not candidate_claims:
            raise PublicApiError(
                422,
                "INSUFFICIENT_ELIGIBLE_INPUTS",
                "Eligible published annual Claims are insufficient for this comparison.",
            )
        available_years = {claim.qualifiers.get("fiscal_year") for claim in candidate_claims}
        if {str(earlier_fiscal_year), str(later_fiscal_year)} - available_years:
            raise PublicApiError(
                422,
                "INSUFFICIENT_ELIGIBLE_INPUTS",
                "Eligible published annual Claims are insufficient for this comparison.",
            )
        evidence_by_claim = {
            claim.id: self.uow.public.evidence_for(claim.id) for claim in candidate_claims
        }
        snapshot_ids = {
            item.snapshot_id
            for claim_evidence in evidence_by_claim.values()
            for item in claim_evidence
            if item.snapshot_id is not None
        }
        source_ids = {
            item.source_id
            for claim_evidence in evidence_by_claim.values()
            for item in claim_evidence
        }
        observations_by_id = {}
        all_evidence = [
            item for claim_evidence in evidence_by_claim.values() for item in claim_evidence
        ]
        for evidence in all_evidence:
            if evidence.feeder_observation_id is None:
                continue
            observation = self.uow.acquisition.feeder_observation(evidence.feeder_observation_id)
            if observation is None:
                continue
            observations_by_id[observation.id] = observation
            snapshot_ids.add(observation.snapshot_id)
            for version in self.uow.acquisition.feeder_observations(
                observation.feeder, observation.scope_key, observation.provider_record_key
            ):
                observations_by_id[version.id] = version
                snapshot_ids.add(version.snapshot_id)
        snapshots = {
            snapshot_id: snapshot
            for snapshot_id in snapshot_ids
            if (snapshot := self.uow.public.source_snapshot(snapshot_id)) is not None
        }
        source_ids.update(snapshot.source_id for snapshot in snapshots.values())
        sources = self.uow.public.sources(source_ids)
        policies = self.uow.public.policies(source.policy_id for source in sources.values())
        try:
            return build_alio_head_expense_money_from_claims(
                organization,
                candidate_claims,
                evidence_by_claim,
                observations=list(observations_by_id.values()),
                snapshots=snapshots,
                sources=sources,
                policies=policies,
                earlier_fiscal_year=earlier_fiscal_year,
                later_fiscal_year=later_fiscal_year,
            )
        except ValueError as exc:
            raise PublicApiError(
                409,
                "SOURCE_VERSION_CONFLICT",
                "Conflicting source versions prevent this comparison.",
            ) from exc

    def relationships(self, person_id: UUID) -> list[dict]:
        self.person_or_404(person_id, public=True)
        return self.uow.public.relationships(person_id)

    def assets(self, person_id: UUID) -> list:
        self.person_or_404(person_id, public=True)
        return []

    def get_source(self, source_id: UUID) -> dict:
        source = self.uow.public.public_source(source_id)
        if not source:
            raise PublicApiError(404, "PUBLIC_RECORD_NOT_FOUND", "The public record was not found.")
        policy = self.uow.public.policies([source.policy_id])[source.policy_id]
        return self.source_payload(source, policy)

    def review_item_payload(self, item) -> dict:
        observation = self.uow.acquisition.feeder_observation(item.observation_id)
        candidate = (
            self.uow.public.person(item.candidate_person_id) if item.candidate_person_id else None
        )
        provenance = None
        if observation is not None:
            snapshot = self.uow.public.source_snapshot(observation.snapshot_id)
            if snapshot is not None:
                source = self.uow.public.source(snapshot.source_id)
                if source is not None:
                    policy = self.uow.public.policies([source.policy_id])[source.policy_id]
                    provenance = {
                        "source": {
                            "id": str(source.id),
                            "title": source.title,
                            "publisher": source.publisher,
                            "url": str(source.url),
                            "source_class": policy.source_class,
                            "license": policy.license,
                            "policy_summary": self.policy_summary(policy),
                        },
                        "snapshot": {
                            "id": str(snapshot.id),
                            "source_id": str(snapshot.source_id),
                            "fetched_at": snapshot.fetched_at.isoformat(),
                            "content_hash": snapshot.content_hash,
                        },
                    }
        action = item.details.get("action")
        if action not in {"REVIEW_REQUIRED", "HARD_CONFLICT"}:
            action = None
        return {
            "id": str(item.id),
            "status": item.status.value,
            "action": action,
            "reason_code": item.reason_code,
            "reasons": [
                reason for reason in item.details.get("reasons", []) if isinstance(reason, str)
            ],
            "candidate_person": {
                "id": str(candidate.id),
                "canonical_name": candidate.canonical_name,
                "identity_status": candidate.identity_status.value,
            }
            if candidate is not None
            else None,
            "observation": {
                "id": str(observation.id),
                "feeder": observation.feeder,
                "scope_key": observation.scope_key,
                "semantic_scope": observation.semantic_scope,
                "provider_record_key": observation.provider_record_key,
                "run_id": str(observation.run_id),
                "recorded_at": observation.recorded_at.isoformat(),
                "provider_observed_at": observation.provider_observed_at.isoformat()
                if observation.provider_observed_at
                else None,
            }
            if observation is not None
            else None,
            "provenance": provenance,
            "resolution_note": item.resolution_note,
        }

    def current_gukgam_schedule_review(self) -> GukgamScheduleReviewReport:
        return load_current_gukgam_schedule_review(self.uow.acquisition)

    def gukgam_2026_schedule_review(self) -> dict:
        return self.current_gukgam_schedule_review().to_dict()

    def gukgam_2026_organization_binding_candidates(self) -> dict:
        return build_gukgam_organization_binding_review(
            self.current_gukgam_schedule_review(), self.uow.public.organizations(current_only=True)
        ).to_dict()

    def gukgam_2026_organization_binding_preflight(
        self, review_key: str, organization_id: UUID
    ) -> dict:
        try:
            return build_gukgam_organization_binding_preflight(
                self.current_gukgam_schedule_review(),
                self.uow.public.organizations(current_only=True),
                review_key=review_key,
                organization_id=organization_id,
            ).to_dict()
        except GukgamOrganizationBindingPreflightError as exc:
            raise PublicApiError(
                422, "INVALID_INPUT", "The requested Gukgam binding preflight is invalid."
            ) from exc

    def review_report(self) -> dict:
        unresolved = [
            str(item.id)
            for item in self.uow.public.people()
            if item.identity_status != IdentityStatus.RESOLVED
        ]
        unpublishable: list[str] = []
        contradictions: list[str] = []
        for claim in self.uow.public.claims(published_only=True):
            evidence = self.uow.public.evidence_for(claim.id)
            sources = self.uow.public.sources(item.source_id for item in evidence)
            policies = self.uow.public.policies(source.policy_id for source in sources.values())
            if claim.person_id is not None:
                subject = self.person_or_404(claim.person_id)
            elif claim.organization_id is not None:
                subject = self.organization_or_404(claim.organization_id)
            else:
                unpublishable.append(str(claim.id))
                continue
            gate = validate_claim_publication(claim, subject, evidence, sources, policies)
            if not gate.publishable:
                unpublishable.append(str(claim.id))
            if {item.stance.value for item in evidence} >= {"SUPPORT", "REFUTE"}:
                contradictions.append(str(claim.id))
        return {
            "unresolved_identities": unresolved,
            "unpublishable_claims": unpublishable,
            "origin_candidates": [],
            "contradictions": contradictions,
            "source_policy_blocks": [
                str(item.id)
                for item in self.uow.public.policies().values()
                if item.collection_mode.value in {"BLOCKED", "DISCOVERY_ONLY"}
            ],
            "review_items": [
                self.review_item_payload(item) for item in self.uow.review.identity_review_items()
            ],
        }

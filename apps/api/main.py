from __future__ import annotations

from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import FastAPI, HTTPException

from packages.domain.enums import IdentityStatus
from packages.persistence import SqlAlchemyRepository, bootstrap_repository, repository
from packages.rendering.profile_projection import build_profile_projection
from packages.verification.claims import validate_claim_publication


def create_app(
    target_repository: SqlAlchemyRepository | None = None,
    *,
    enable_review_surface: bool = False,
) -> FastAPI:
    target = target_repository or repository

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        bootstrap_repository(target)
        yield

    app = FastAPI(title="Civic Intel API", version="0.4.0", lifespan=lifespan)

    def person_or_404(person_id: UUID, *, public: bool = False):
        person = target.person(person_id)
        if not person or (
            public
            and (
                person.identity_status != IdentityStatus.RESOLVED
                or person.superseded_at is not None
            )
        ):
            raise HTTPException(404, "person not found")
        return person

    def organization_or_404(organization_id: UUID, *, public: bool = False):
        organization = target.organization(organization_id)
        if not organization or (public and organization.superseded_at is not None):
            raise HTTPException(404, "organization not found")
        return organization

    def policy_summary(policy) -> dict[str, str]:
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

    def source_payload(source, policy) -> dict:
        return source.model_dump(mode="json") | {
            "policy": policy.model_dump(mode="json"),
            "policy_summary": policy_summary(policy),
        }

    def claim_payload(claim, evidence=None) -> dict:
        selected_evidence = target.evidence_for(claim.id) if evidence is None else evidence
        sources = target.sources(item.source_id for item in selected_evidence)
        policies = target.policies(source.policy_id for source in sources.values())
        if claim.person_id is not None:
            subject = person_or_404(claim.person_id)
        elif claim.organization_id is not None:
            subject = organization_or_404(claim.organization_id)
        else:
            raise HTTPException(500, "claim has no subject")
        gate = validate_claim_publication(claim, subject, selected_evidence, sources, policies)
        if not gate.publishable:
            raise HTTPException(500, f"publication invariant violated: {gate.failures}")
        stances = {item.stance.value for item in selected_evidence}
        return claim.model_dump(mode="json") | {
            "evidence": [item.model_dump(mode="json") for item in selected_evidence],
            "source_ids": sorted({str(item.source_id) for item in selected_evidence}),
            "source_conflict": {"SUPPORT", "REFUTE"} <= stances,
        }

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/people")
    def people() -> list[dict]:
        return [item.model_dump(mode="json") for item in target.public_people()]

    @app.get("/people/{person_id}")
    def person(person_id: UUID) -> dict:
        item = person_or_404(person_id, public=True)
        published_claims = target.claims(person_id, True, current_only=True)
        evidence_by_claim = {
            claim.id: target.evidence_for(claim.id) for claim in published_claims
        }
        person_claims = [
            claim_payload(claim, evidence_by_claim[claim.id]) for claim in published_claims
        ]
        source_ids = {
            item.source_id
            for claim_evidence in evidence_by_claim.values()
            for item in claim_evidence
        }
        source_map = target.sources(source_ids)
        policy_map = target.policies(source.policy_id for source in source_map.values())
        relationships = target.relationships(person_id)
        decision_episodes = target.decision_episodes(person_id)
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

    @app.get("/people/{person_id}/claims")
    def claims(person_id: UUID) -> list[dict]:
        person_or_404(person_id, public=True)
        return [claim_payload(item) for item in target.claims(person_id, True, current_only=True)]

    @app.get("/organizations/{organization_id}")
    def organization(organization_id: UUID) -> dict:
        item = organization_or_404(organization_id, public=True)
        published_claims = target.claims(
            published_only=True,
            current_only=True,
            organization_id=organization_id,
        )
        return item.model_dump(mode="json") | {
            "claims": [claim_payload(claim) for claim in published_claims]
        }

    @app.get("/organizations/{organization_id}/claims")
    def organization_claims(organization_id: UUID) -> list[dict]:
        organization_or_404(organization_id, public=True)
        return [
            claim_payload(item)
            for item in target.claims(
                published_only=True,
                current_only=True,
                organization_id=organization_id,
            )
        ]

    @app.get("/people/{person_id}/relationships")
    def relationships(person_id: UUID) -> list[dict]:
        person_or_404(person_id, public=True)
        return target.relationships(person_id)

    @app.get("/people/{person_id}/assets")
    def assets(person_id: UUID) -> list:
        person_or_404(person_id, public=True)
        return []

    @app.get("/sources/{source_id}")
    def get_source(source_id: UUID) -> dict:
        source = target.source(source_id)
        if not source:
            raise HTTPException(404, "source not found")
        policy = target.policies([source.policy_id])[source.policy_id]
        return source_payload(source, policy)

    def review_item_payload(item) -> dict:
        observation = target.feeder_observation(item.observation_id)
        candidate = (
            target.person(item.candidate_person_id) if item.candidate_person_id else None
        )
        provenance = None
        if observation is not None:
            snapshot = target.source_snapshot(observation.snapshot_id)
            if snapshot is not None:
                source = target.source(snapshot.source_id)
                if source is not None:
                    policy = target.policies([source.policy_id])[source.policy_id]
                    provenance = {
                        "source": {
                            "id": str(source.id),
                            "title": source.title,
                            "publisher": source.publisher,
                            "url": str(source.url),
                            "source_class": policy.source_class,
                            "license": policy.license,
                            "policy_summary": policy_summary(policy),
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
            "candidate_person": (
                {
                    "id": str(candidate.id),
                    "canonical_name": candidate.canonical_name,
                    "identity_status": candidate.identity_status.value,
                }
                if candidate is not None
                else None
            ),
            "observation": (
                {
                    "id": str(observation.id),
                    "feeder": observation.feeder,
                    "scope_key": observation.scope_key,
                    "semantic_scope": observation.semantic_scope,
                    "provider_record_key": observation.provider_record_key,
                    "run_id": str(observation.run_id),
                    "recorded_at": observation.recorded_at.isoformat(),
                    "provider_observed_at": (
                        observation.provider_observed_at.isoformat()
                        if observation.provider_observed_at
                        else None
                    ),
                }
                if observation is not None
                else None
            ),
            "provenance": provenance,
            "resolution_note": item.resolution_note,
        }

    if enable_review_surface:

        @app.get("/admin/review")
        def review_report() -> dict:
            unresolved = [
                str(item.id)
                for item in target.people()
                if item.identity_status != IdentityStatus.RESOLVED
            ]
            unpublishable: list[str] = []
            contradictions: list[str] = []
            for claim in target.claims(published_only=True):
                evidence = target.evidence_for(claim.id)
                sources = target.sources(item.source_id for item in evidence)
                policies = target.policies(source.policy_id for source in sources.values())
                if claim.person_id is not None:
                    subject = person_or_404(claim.person_id)
                elif claim.organization_id is not None:
                    subject = organization_or_404(claim.organization_id)
                else:
                    unpublishable.append(str(claim.id))
                    continue
                gate = validate_claim_publication(
                    claim, subject, evidence, sources, policies
                )
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
                    for item in target.policies().values()
                    if item.collection_mode.value in {"BLOCKED", "DISCOVERY_ONLY"}
                ],
                "review_items": [
                    review_item_payload(item) for item in target.identity_review_items()
                ],
            }

    return app


app = create_app()

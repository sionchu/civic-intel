from __future__ import annotations

from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import FastAPI, HTTPException

from packages.domain.enums import IdentityStatus
from packages.rendering.profile_projection import build_profile_projection
from packages.verification.claims import validate_claim_publication

from .repository import SqlAlchemyRepository, bootstrap_repository, repository


def create_app(target_repository: SqlAlchemyRepository | None = None) -> FastAPI:
    target = target_repository or repository

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        bootstrap_repository(target)
        yield

    app = FastAPI(title="Civic Intel API", version="0.4.0", lifespan=lifespan)

    def person_or_404(person_id: UUID):
        person = target.person(person_id)
        if not person:
            raise HTTPException(404, "person not found")
        return person

    def claim_payload(claim, evidence=None) -> dict:
        selected_evidence = target.evidence_for(claim.id) if evidence is None else evidence
        sources = target.sources(item.source_id for item in selected_evidence)
        policies = target.policies(source.policy_id for source in sources.values())
        person = person_or_404(claim.person_id)
        gate = validate_claim_publication(
            claim, person, selected_evidence, sources, policies
        )
        if not gate.publishable:
            raise HTTPException(500, f"publication invariant violated: {gate.failures}")
        return claim.model_dump(mode="json") | {
            "evidence": [item.model_dump(mode="json") for item in selected_evidence],
            "source_ids": sorted({str(item.source_id) for item in selected_evidence}),
        }

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/people")
    def people() -> list[dict]:
        return [item.model_dump(mode="json") for item in target.people()]

    @app.get("/people/{person_id}")
    def person(person_id: UUID) -> dict:
        item = person_or_404(person_id)
        published_claims = target.claims(person_id, True)
        evidence_by_claim = {
            claim.id: target.evidence_for(claim.id) for claim in published_claims
        }
        person_claims = [
            claim_payload(claim, evidence_by_claim[claim.id]) for claim in published_claims
        ]
        relationships = target.relationships(person_id)
        decision_episodes = target.decision_episodes(person_id)
        profile = build_profile_projection(
            item,
            published_claims,
            evidence_by_claim,
            relationships,
            decision_episodes,
        )
        return item.model_dump(mode="json") | {
            "claims": person_claims,
            "profile": profile,
            "relationship_ids": [relationship["id"] for relationship in relationships],
            "asset_disclosure_ids": [],
        }

    @app.get("/people/{person_id}/claims")
    def claims(person_id: UUID) -> list[dict]:
        person_or_404(person_id)
        return [claim_payload(item) for item in target.claims(person_id, True)]

    @app.get("/people/{person_id}/relationships")
    def relationships(person_id: UUID) -> list[dict]:
        person_or_404(person_id)
        return target.relationships(person_id)

    @app.get("/people/{person_id}/assets")
    def assets(person_id: UUID) -> list:
        person_or_404(person_id)
        return []

    @app.get("/sources/{source_id}")
    def get_source(source_id: UUID) -> dict:
        source = target.source(source_id)
        if not source:
            raise HTTPException(404, "source not found")
        policy = target.policies([source.policy_id])[source.policy_id]
        return source.model_dump(mode="json") | {"policy": policy.model_dump(mode="json")}

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
            gate = validate_claim_publication(
                claim, person_or_404(claim.person_id), evidence, sources, policies
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
        }

    return app


app = create_app()

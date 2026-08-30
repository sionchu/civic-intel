from __future__ import annotations

from uuid import UUID

from fastapi import FastAPI, HTTPException

from packages.domain.enums import IdentityStatus
from packages.verification.claims import validate_claim_publication

from .repository import repository

app = FastAPI(title="Civic Intel API", version="0.2.0")


def person_or_404(person_id: UUID):
    person = repository.person(person_id)
    if not person:
        raise HTTPException(404, "person not found")
    return person


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/people")
def people() -> list[dict]:
    return [item.model_dump(mode="json") for item in repository.people()]


def claim_payload(claim) -> dict:
    evidence = repository.evidence_for(claim.id)
    sources = repository.sources(item.source_id for item in evidence)
    policies = repository.policies(source.policy_id for source in sources.values())
    person = person_or_404(claim.person_id)
    gate = validate_claim_publication(claim, person, evidence, sources, policies)
    if not gate.publishable:
        raise HTTPException(500, f"publication invariant violated: {gate.failures}")
    return claim.model_dump(mode="json") | {
        "evidence": [item.model_dump(mode="json") for item in evidence],
        "source_ids": sorted({str(item.source_id) for item in evidence}),
    }


@app.get("/people/{person_id}")
def person(person_id: UUID) -> dict:
    item = person_or_404(person_id)
    person_claims = [claim_payload(claim) for claim in repository.claims(person_id, True)]
    relationships = repository.relationships(person_id)
    return item.model_dump(mode="json") | {
        "claims": person_claims,
        "relationship_ids": [relationship["id"] for relationship in relationships],
        "asset_disclosure_ids": [],
    }


@app.get("/people/{person_id}/claims")
def claims(person_id: UUID) -> list[dict]:
    person_or_404(person_id)
    return [claim_payload(item) for item in repository.claims(person_id, True)]


@app.get("/people/{person_id}/relationships")
def relationships(person_id: UUID) -> list[dict]:
    person_or_404(person_id)
    return repository.relationships(person_id)


@app.get("/people/{person_id}/assets")
def assets(person_id: UUID) -> list:
    person_or_404(person_id)
    return []


@app.get("/sources/{source_id}")
def get_source(source_id: UUID) -> dict:
    source = repository.source(source_id)
    if not source:
        raise HTTPException(404, "source not found")
    policy = repository.policies([source.policy_id])[source.policy_id]
    return source.model_dump(mode="json") | {"policy": policy.model_dump(mode="json")}


@app.get("/admin/review")
def review_report() -> dict:
    unresolved = [
        str(item.id)
        for item in repository.people()
        if item.identity_status != IdentityStatus.RESOLVED
    ]
    unpublishable: list[str] = []
    contradictions: list[str] = []
    for claim in repository.claims(published_only=True):
        evidence = repository.evidence_for(claim.id)
        sources = repository.sources(item.source_id for item in evidence)
        policies = repository.policies(source.policy_id for source in sources.values())
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
            for item in repository.policies().values()
            if item.collection_mode.value in {"BLOCKED", "DISCOVERY_ONLY"}
        ],
    }

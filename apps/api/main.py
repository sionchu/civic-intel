from __future__ import annotations

from uuid import UUID

from fastapi import FastAPI, HTTPException

from packages.verification.claims import validate_claim_publication

from .store import ASSETS, CLAIMS, EVIDENCE, PEOPLE, POLICIES, RELATIONSHIPS, SOURCES

app = FastAPI(title="Civic Intel API", version="0.1.0")


def person_or_404(person_id: UUID):
    person = PEOPLE.get(person_id)
    if not person:
        raise HTTPException(404, "person not found")
    return person


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/people")
def people() -> list[dict]:
    return [item.model_dump(mode="json") for item in PEOPLE.values()]


@app.get("/people/{person_id}")
def person(person_id: UUID) -> dict:
    item = person_or_404(person_id)
    person_claims = [
        claim_payload(c) for c in CLAIMS.values() if c.person_id == person_id and c.published
    ]
    return item.model_dump(mode="json") | {
        "claims": person_claims,
        "relationship_ids": [],
        "asset_disclosure_ids": [],
    }


def claim_payload(claim) -> dict:
    evidence = [item for item in EVIDENCE.values() if item.claim_id == claim.id]
    gate = validate_claim_publication(claim, PEOPLE[claim.person_id], evidence, SOURCES, POLICIES)
    if not gate.publishable:
        raise HTTPException(500, f"publication invariant violated: {gate.failures}")
    return claim.model_dump(mode="json") | {
        "evidence": [item.model_dump(mode="json") for item in evidence],
        "source_ids": sorted({str(item.source_id) for item in evidence}),
    }


@app.get("/people/{person_id}/claims")
def claims(person_id: UUID) -> list[dict]:
    person_or_404(person_id)
    return [
        claim_payload(item)
        for item in CLAIMS.values()
        if item.person_id == person_id and item.published
    ]


@app.get("/people/{person_id}/relationships")
def relationships(person_id: UUID) -> list:
    person_or_404(person_id)
    return RELATIONSHIPS.get(person_id, [])


@app.get("/people/{person_id}/assets")
def assets(person_id: UUID) -> list:
    person_or_404(person_id)
    return ASSETS.get(person_id, [])


@app.get("/sources/{source_id}")
def get_source(source_id: UUID) -> dict:
    source = SOURCES.get(source_id)
    if not source:
        raise HTTPException(404, "source not found")
    policy = POLICIES[source.policy_id]
    return source.model_dump(mode="json") | {"policy": policy.model_dump(mode="json")}


@app.get("/admin/review")
def review_report() -> dict:
    unresolved = [str(item.id) for item in PEOPLE.values() if item.identity_status != "RESOLVED"]
    unpublishable = []
    for claim in CLAIMS.values():
        evidence = [item for item in EVIDENCE.values() if item.claim_id == claim.id]
        if not validate_claim_publication(
            claim, PEOPLE[claim.person_id], evidence, SOURCES, POLICIES
        ).publishable:
            unpublishable.append(str(claim.id))
    return {
        "unresolved_identities": unresolved,
        "unpublishable_claims": unpublishable,
        "origin_candidates": [],
        "contradictions": [],
        "source_policy_blocks": [],
    }

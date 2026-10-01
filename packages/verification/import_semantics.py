from collections.abc import Sequence

from packages.domain.contracts import Claim, ClaimEvidence


def _person_claim_import_semantics(claim: Claim) -> dict:
    return {
        "person_id": claim.person_id,
        "organization_id": claim.organization_id,
        "proposition": claim.proposition,
        "subject": claim.subject,
        "predicate": claim.predicate,
        "object_text": claim.object_text,
        "qualifiers": claim.qualifiers,
        "epistemic_status": claim.epistemic_status,
        "publication_status": claim.publication_status,
        "asserted_as_true": claim.asserted_as_true,
        "resolution_note": claim.resolution_note,
    }


def _evidence_import_semantics(evidence: Sequence[ClaimEvidence]) -> list[tuple]:
    values = [
        (item.source_id, item.snapshot_id, item.feeder_observation_id, item.stance, item.excerpt)
        for item in evidence
    ]
    return sorted(
        values, key=lambda item: tuple("" if value is None else str(value) for value in item)
    )


class OrganizationClaimImportError(ValueError):
    pass

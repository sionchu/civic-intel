from __future__ import annotations

import json
from datetime import date
from uuid import UUID

import pytest

import workers.alio_cross_lane_identity_candidates as worker
from packages.domain.contracts import Claim, ClaimEvidence, Organization, Person
from packages.domain.enums import (
    EpistemicStatus,
    EvidenceStance,
    IdentityStatus,
    PublicationStatus,
)
from packages.rendering.alio_organization_content import (
    ALIO_EXECUTIVE_PREDICATE,
    ALIO_EXECUTIVE_SCOPE,
    ALIO_EXECUTIVE_SEMANTIC_SCOPE,
    ALIO_EXECUTIVE_SOURCE_CONTRACT,
)
from packages.verification.alio_person_candidates import (
    DISCOVERY_REASON,
    AlioCandidatePipelineError,
    generate_alio_cross_lane_candidates,
)


def stable_id(value: int) -> UUID:
    return UUID(f"00000000-0000-0000-0000-{value:012d}")


class FakeCandidateRepository:
    def __init__(
        self,
        organizations: tuple[Organization, ...],
        contexts: dict[UUID, tuple[tuple[Claim, ...], dict[UUID, tuple[ClaimEvidence, ...]]]],
        people: tuple[Person, ...],
    ) -> None:
        self._organizations = organizations
        self._contexts = contexts
        self._people = people
        self.calls: list[str] = []

    def assert_ready(self) -> None:
        self.calls.append("assert_ready")

    def public_organizations(self) -> list[Organization]:
        self.calls.append("public_organizations")
        return list(self._organizations)

    def published_organization_claim_contexts(
        self, organization_ids: object
    ) -> dict[UUID, tuple[tuple[Claim, ...], dict[UUID, tuple[ClaimEvidence, ...]]]]:
        self.calls.append("published_organization_claim_contexts")
        requested = tuple(organization_ids)  # type: ignore[arg-type]
        return {organization_id: self._contexts[organization_id] for organization_id in requested}

    def public_people(self) -> list[Person]:
        self.calls.append("public_people")
        return list(self._people)


def alio_claim(
    organization: Organization,
    *,
    claim_number: int,
    name: str,
    position: str = "사장",
    predicate: str = ALIO_EXECUTIVE_PREDICATE,
    source_contract: str = ALIO_EXECUTIVE_SOURCE_CONTRACT,
) -> tuple[Claim, ClaimEvidence]:
    claim_id = stable_id(100 + claim_number)
    claim = Claim(
        id=claim_id,
        organization_id=organization.id,
        proposition=f"{organization.name}는 {name}을 공개한다.",
        subject=organization.name,
        predicate=predicate,
        object_text=f"{position} · {name or '공석'}",
        qualifiers={
            "canonical_name": name,
            "position_text": position,
            "alio_apba_id": f"C{claim_number:04d}",
            "term_start": "2025-01-02",
            "term_end": "2028-01-01",
            "source_contract": source_contract,
            "source_scope": ALIO_EXECUTIVE_SCOPE,
            "semantic_scope": ALIO_EXECUTIVE_SEMANTIC_SCOPE,
        },
        epistemic_status=EpistemicStatus.FACT,
        publication_status=PublicationStatus.PUBLISHED,
        asserted_as_true=True,
    )
    evidence = ClaimEvidence(
        id=stable_id(200 + claim_number),
        claim_id=claim.id,
        source_id=stable_id(300 + claim_number),
        stance=EvidenceStance.SUPPORT,
    )
    return claim, evidence


def repository_for(
    claim_specs: tuple[tuple[Organization, dict[str, object]], ...],
    people: tuple[Person, ...],
) -> FakeCandidateRepository:
    grouped: dict[UUID, list[tuple[Claim, ClaimEvidence]]] = {}
    organizations: list[Organization] = []
    for organization, spec in claim_specs:
        organizations.append(organization)
        claim, evidence = alio_claim(organization, **spec)  # type: ignore[arg-type]
        grouped.setdefault(organization.id, []).append((claim, evidence))
    contexts = {
        organization_id: (
            tuple(claim for claim, _ in items),
            {claim.id: (evidence,) for claim, evidence in items},
        )
        for organization_id, items in grouped.items()
    }
    return FakeCandidateRepository(tuple(organizations), contexts, people)


def test_exact_name_overlap_generates_one_review_candidate() -> None:
    organization = Organization(id=stable_id(1), name="테스트기관")
    person = Person(
        id=stable_id(2),
        canonical_name="김테스트",
        birth_date=date(1980, 1, 2),
        identity_status=IdentityStatus.RESOLVED,
    )
    repository = repository_for(
        ((organization, {"claim_number": 1, "name": "김테스트"}),),
        (person,),
    )

    result = generate_alio_cross_lane_candidates(repository)  # type: ignore[arg-type]

    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.discovery_reason == DISCOVERY_REASON
    assert candidate.identity_status == IdentityStatus.REVIEW
    assert candidate.decision_class.value == "CONTEXT_REVIEW"
    assert "cross_lane_bridge_evidence_missing" in candidate.identity_reasons
    assert repository.calls == [
        "assert_ready",
        "public_organizations",
        "published_organization_claim_contexts",
        "public_people",
    ]


def test_different_name_generates_no_pair() -> None:
    organization = Organization(id=stable_id(3), name="테스트기관")
    person = Person(id=stable_id(4), canonical_name="이테스트", identity_status=IdentityStatus.RESOLVED)
    repository = repository_for(
        ((organization, {"claim_number": 2, "name": "김테스트"}),),
        (person,),
    )

    result = generate_alio_cross_lane_candidates(repository)  # type: ignore[arg-type]

    assert result.alio_executive_claims_considered == 1
    assert result.public_people_considered == 1
    assert result.candidates == ()


def test_same_name_with_different_roles_stays_review() -> None:
    organization = Organization(id=stable_id(5), name="다른기관")
    person = Person(id=stable_id(6), canonical_name="김테스트", identity_status=IdentityStatus.RESOLVED)
    repository = repository_for(
        ((organization, {"claim_number": 3, "name": "김테스트", "position": "비상임이사"}),),
        (person,),
    )

    candidate = generate_alio_cross_lane_candidates(repository).candidates[0]  # type: ignore[arg-type]

    assert candidate.position_text == "비상임이사"
    assert candidate.organization_name == "다른기관"
    assert candidate.identity_status == IdentityStatus.REVIEW
    assert candidate.decision_class.value == "CONTEXT_REVIEW"


def test_distinct_alio_claim_ids_remain_distinct_candidate_observations() -> None:
    organization = Organization(id=stable_id(7), name="중복기관")
    person = Person(id=stable_id(8), canonical_name="김테스트", identity_status=IdentityStatus.RESOLVED)
    first = alio_claim(organization, claim_number=4, name="김테스트", position="사장")
    second = alio_claim(organization, claim_number=5, name="김테스트", position="상임이사")
    repository = FakeCandidateRepository(
        (organization,),
        (
            {
                organization.id: (
                    (first[0], second[0]),
                    {first[0].id: (first[1],), second[0].id: (second[1],)},
                )
            }
        ),
        (person,),
    )

    result = generate_alio_cross_lane_candidates(repository)  # type: ignore[arg-type]

    assert len(result.candidates) == 2
    assert {item.alio_claim_id for item in result.candidates} == {first[0].id, second[0].id}
    assert len({item.candidate_key for item in result.candidates}) == 2


def test_masked_or_vacant_row_without_public_name_is_excluded() -> None:
    organization = Organization(id=stable_id(9), name="공석기관")
    person = Person(id=stable_id(10), canonical_name="공석", identity_status=IdentityStatus.RESOLVED)
    repository = repository_for(
        ((organization, {"claim_number": 6, "name": ""}),),
        (person,),
    )

    result = generate_alio_cross_lane_candidates(repository)  # type: ignore[arg-type]

    assert result.alio_executive_claims_considered == 0
    assert result.candidates == ()


def test_non_alio_organization_claim_is_excluded() -> None:
    organization = Organization(id=stable_id(11), name="분류기관")
    person = Person(id=stable_id(12), canonical_name="김테스트", identity_status=IdentityStatus.RESOLVED)
    repository = repository_for(
        (
            (
                organization,
                {
                    "claim_number": 7,
                    "name": "김테스트",
                    "predicate": "ALIO_INSTITUTION_CLASSIFICATION",
                },
            ),
        ),
        (person,),
    )

    result = generate_alio_cross_lane_candidates(repository)  # type: ignore[arg-type]

    assert result.candidates == ()
    assert result.alio_executive_claims_considered == 0


def test_non_current_or_unpublished_alio_claim_is_excluded() -> None:
    organization = Organization(id=stable_id(19), name="비공개기관")
    person = Person(id=stable_id(20), canonical_name="김테스트", identity_status=IdentityStatus.RESOLVED)
    claim, evidence = alio_claim(organization, claim_number=11, name="김테스트")
    claim = claim.model_copy(update={"publication_status": PublicationStatus.DRAFT})
    repository = FakeCandidateRepository(
        (organization,),
        ({organization.id: ((claim,), {claim.id: (evidence,)})}),
        (person,),
    )

    result = generate_alio_cross_lane_candidates(repository)  # type: ignore[arg-type]

    assert result.alio_executive_claims_considered == 0
    assert result.candidates == ()


def test_command_is_read_only_and_has_no_commit_option(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    organization = Organization(id=stable_id(13), name="읽기기관")
    person = Person(id=stable_id(14), canonical_name="김테스트", identity_status=IdentityStatus.RESOLVED)
    repository = repository_for(
        ((organization, {"claim_number": 8, "name": "김테스트"}),),
        (person,),
    )
    before = (repository._organizations, repository._contexts, repository._people)
    monkeypatch.setattr(worker, "SqlAlchemyRepository", lambda _url: repository)

    assert worker.main(["--database-url", "sqlite:///read-only.db"]) == 0
    report = json.loads(capsys.readouterr().out)

    assert report["status"] == "REVIEW_ONLY"
    assert report["candidate_pairs"] == 1
    assert (repository._organizations, repository._contexts, repository._people) == before
    assert repository.calls.count("public_organizations") == 1
    assert repository.calls.count("published_organization_claim_contexts") == 1
    assert repository.calls.count("public_people") == 1
    with pytest.raises(SystemExit):
        worker.build_parser().parse_args(["--commit"])


def test_identical_runs_have_byte_equivalent_json() -> None:
    organization = Organization(id=stable_id(15), name="결정기관")
    person = Person(id=stable_id(16), canonical_name="김테스트", identity_status=IdentityStatus.RESOLVED)
    first_repository = repository_for(
        ((organization, {"claim_number": 9, "name": "김테스트"}),),
        (person,),
    )
    second_repository = repository_for(
        ((organization, {"claim_number": 9, "name": "김테스트"}),),
        (person,),
    )

    first = json.dumps(
        generate_alio_cross_lane_candidates(first_repository).to_dict(),  # type: ignore[arg-type]
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    second = json.dumps(
        generate_alio_cross_lane_candidates(second_repository).to_dict(),  # type: ignore[arg-type]
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )

    assert first == second


def test_resolved_without_bridge_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    organization = Organization(id=stable_id(17), name="차단기관")
    person = Person(id=stable_id(18), canonical_name="김테스트", identity_status=IdentityStatus.RESOLVED)
    repository = repository_for(
        ((organization, {"claim_number": 10, "name": "김테스트"}),),
        (person,),
    )

    class UnexpectedResolution:
        status = IdentityStatus.RESOLVED
        decision_class = next(iter(()), None)
        reasons = ("name_match",)

    monkeypatch.setattr(
        "packages.verification.alio_person_candidates.resolve_cross_lane_identity",
        lambda *_args, **_kwargs: UnexpectedResolution(),
    )

    with pytest.raises(AlioCandidatePipelineError, match="bridge evidence"):
        generate_alio_cross_lane_candidates(repository)  # type: ignore[arg-type]

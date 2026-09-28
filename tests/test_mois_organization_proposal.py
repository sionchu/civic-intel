from datetime import UTC, datetime
from uuid import UUID

import pytest

from packages.domain.contracts import FeederObservation, Organization
from packages.rendering.gukgam_organization_binding_review import (
    EXACT_ONE,
    NO_EXACT,
    GukgamOrganizationBindingReviewItem,
    GukgamOrganizationBindingReviewReport,
    OrganizationBindingCandidate,
)
from packages.rendering.mois_organization_proposal import (
    MOIS_ORGANIZATION_PROPOSAL_SEMANTICS,
    MoisOrganizationProposalError,
    build_mois_organization_proposal,
    mois_organization_proposal_provider_row,
)

OBS1 = UUID("11111111-1111-1111-1111-111111111111")
OBS2 = UUID("22222222-2222-2222-2222-222222222222")
ORG1 = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
SNAPSHOT = UUID("33333333-3333-3333-3333-333333333333")
RUN = UUID("44444444-4444-4444-4444-444444444444")


def observation(
    *,
    observation_id: UUID,
    name: str,
    code: str,
    semantic_scope: str = "current_organization_code_registry",
) -> FeederObservation:
    return FeederObservation(
        id=observation_id,
        feeder="mois_standard_organization_codes",
        scope_key="current:stop_selt=0",
        provider_record_key=code,
        snapshot_id=SNAPSHOT,
        run_id=RUN,
        recorded_at=datetime(2026, 9, 28, tzinfo=UTC),
        semantic_scope=semantic_scope,
        identity_hints={
            "record_kind": "organization_registry_record",
            "external_ids": {"mois_org_cd": code},
            "organization_name": name,
            "materialization": "REVIEW_ONLY",
        },
        normalized={
            "org_code": code,
            "full_name": name,
            "lowest_name": name,
            "type_big": "중앙행정기관",
            "type_mid": None,
            "parent_org_code": "0000000",
            "top_org_code": code,
            "representative_org_code": code,
            "base_date": "2026-09-28",
            "changed_date": "2026-09-28",
            "stop_selector": "0",
            "identity_semantics": (
                "PROVIDER_ORGANIZATION_KEY_NOT_CANONICAL_ORGANIZATION"
            ),
        },
        content_hash="a" * 64,
    )


def review_item(
    *,
    key: str,
    name: str,
    observation_id: UUID,
    match_class: str = NO_EXACT,
    candidates: tuple[OrganizationBindingCandidate, ...] = (),
) -> GukgamOrganizationBindingReviewItem:
    return GukgamOrganizationBindingReviewItem(
        review_key=key,
        committee_name="테스트위원회",
        audit_date="2026-10-20",
        provider_record_key=key.split(":audited-target:")[0],
        observation_id=observation_id,
        audited_target=name,
        match_class=match_class,
        candidates=candidates,
    )


def test_builds_exact_full_name_review_only_proposal() -> None:
    provider_rows = [
        mois_organization_proposal_provider_row(
            observation(
                observation_id=OBS1,
                name="행정안전부",
                code="1741000",
            )
        ),
        mois_organization_proposal_provider_row(
            observation(
                observation_id=OBS2,
                name="미사용기관",
                code="1999999",
            )
        ),
    ]
    review = GukgamOrganizationBindingReviewReport(
        organization_universe_count=0,
        items=(
            review_item(
                key="row-b:audited-target:2",
                name="행정안전부",
                observation_id=OBS2,
            ),
            review_item(
                key="row-a:audited-target:1",
                name="행정안전부",
                observation_id=OBS1,
            ),
            review_item(
                key="row-c:audited-target:1",
                name="없는기관",
                observation_id=OBS1,
            ),
        ),
    )

    report = build_mois_organization_proposal(
        provider_rows,
        provider_universe_count=3,
        gukgam_review=review,
        organizations=[],
    )
    payload = report.to_dict()

    assert payload["semantics"] == MOIS_ORGANIZATION_PROPOSAL_SEMANTICS
    assert payload["status"] == "REVIEW_ONLY"
    assert payload["proposal_count"] == 1
    assert payload["gukgam_occurrence_count"] == 2
    assert payload["gukgam_no_exact_distinct_target_count"] == 2
    assert payload["unmatched_distinct_target_count"] == 1
    assert payload["ambiguous_distinct_target_count"] == 0
    assert report.items[0].organization_name == "행정안전부"
    assert report.items[0].provider.org_code == "1741000"
    assert report.items[0].provider.observation_id == OBS1
    assert [item.review_key for item in report.items[0].occurrences] == [
        "row-a:audited-target:1",
        "row-b:audited-target:2",
    ]
    assert payload["items"][0]["proposal_status"] == "REVIEW_REQUIRED_NO_WRITE"


def test_exact_one_gukgam_items_are_not_proposed() -> None:
    candidate = OrganizationBindingCandidate(organization_id=ORG1, name="행정안전부")
    review = GukgamOrganizationBindingReviewReport(
        organization_universe_count=1,
        items=(
            review_item(
                key="row-a:audited-target:1",
                name="행정안전부",
                observation_id=OBS1,
                match_class=EXACT_ONE,
                candidates=(candidate,),
            ),
        ),
    )
    provider_rows = [
        mois_organization_proposal_provider_row(
            observation(
                observation_id=OBS1,
                name="행정안전부",
                code="1741000",
            )
        )
    ]

    report = build_mois_organization_proposal(
        provider_rows,
        provider_universe_count=1,
        gukgam_review=review,
        organizations=[Organization(id=ORG1, name="행정안전부")],
    )

    assert report.items == ()
    assert report.ambiguous_items == ()


def test_multiple_exact_mois_names_are_withheld_as_ambiguous() -> None:
    rows = [
        mois_organization_proposal_provider_row(
            observation(observation_id=OBS1, name="동일기관", code="1111111")
        ),
        mois_organization_proposal_provider_row(
            observation(observation_id=OBS2, name="동일기관", code="2222222")
        ),
    ]
    review = GukgamOrganizationBindingReviewReport(
        organization_universe_count=0,
        items=(
            review_item(
                key="row-a:audited-target:1",
                name="동일기관",
                observation_id=OBS1,
            ),
        ),
    )

    report = build_mois_organization_proposal(
        rows,
        provider_universe_count=2,
        gukgam_review=review,
        organizations=[],
    )

    assert report.items == ()
    assert len(report.ambiguous_items) == 1
    assert report.ambiguous_items[0].provider_org_codes == ("1111111", "2222222")
    assert report.unmatched_distinct_target_count == 0


def test_current_canonical_name_conflict_fails_closed() -> None:
    review = GukgamOrganizationBindingReviewReport(
        organization_universe_count=1,
        items=(
            review_item(
                key="row-a:audited-target:1",
                name="행정안전부",
                observation_id=OBS1,
            ),
        ),
    )
    rows = [
        mois_organization_proposal_provider_row(
            observation(observation_id=OBS1, name="행정안전부", code="1741000")
        )
    ]

    with pytest.raises(MoisOrganizationProposalError, match="already uses NO_EXACT"):
        build_mois_organization_proposal(
            rows,
            provider_universe_count=1,
            gukgam_review=review,
            organizations=[Organization(name="행정안전부")],
        )


def test_duplicate_provider_key_fails_closed() -> None:
    first = mois_organization_proposal_provider_row(
        observation(observation_id=OBS1, name="기관A", code="1111111")
    )
    duplicate = mois_organization_proposal_provider_row(
        observation(observation_id=OBS2, name="기관B", code="1111111")
    )
    review = GukgamOrganizationBindingReviewReport(
        organization_universe_count=0,
        items=(),
    )

    with pytest.raises(MoisOrganizationProposalError, match="provider_record_key"):
        build_mois_organization_proposal(
            [first, duplicate],
            provider_universe_count=2,
            gukgam_review=review,
            organizations=[],
        )


def test_observation_contract_drift_fails_closed() -> None:
    bad = observation(
        observation_id=OBS1,
        name="행정안전부",
        code="1741000",
        semantic_scope="wrong_scope",
    )
    with pytest.raises(MoisOrganizationProposalError, match="unexpected MOIS"):
        mois_organization_proposal_provider_row(bad)

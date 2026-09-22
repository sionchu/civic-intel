from uuid import UUID

import pytest

from packages.connectors.orggo_top_level_organizations import OrgGoTopLevelOrganizationRecord
from packages.domain.contracts import Organization
from packages.rendering.gukgam_organization_binding_review import (
    EXACT_ONE,
    NO_EXACT,
    GukgamOrganizationBindingReviewItem,
    GukgamOrganizationBindingReviewReport,
    OrganizationBindingCandidate,
)
from packages.rendering.orggo_organization_proposal import (
    ORGGO_ORGANIZATION_PROPOSAL_SEMANTICS,
    OrgGoOrganizationProposalError,
    build_orggo_organization_proposal,
)

OBS1 = UUID("11111111-1111-1111-1111-111111111111")
OBS2 = UUID("22222222-2222-2222-2222-222222222222")
ORG1 = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


def provider(name: str, code: str, chart: str) -> OrgGoTopLevelOrganizationRecord:
    return OrgGoTopLevelOrganizationRecord(
        organization_name=name,
        category="중앙행정기관",
        org_code=code,
        chart_id=chart,
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


def test_builds_deterministic_review_only_proposals() -> None:
    rows = [
        provider("행정안전부", "1741000", "55"),
        provider("과학기술정보통신부", "1721000", "60"),
        provider("미사용기관", "1999999", "99"),
    ]
    review = GukgamOrganizationBindingReviewReport(
        organization_universe_count=0,
        items=(
            review_item(
                key="row-b:audited-target:2",
                name="과학기술정보통신부",
                observation_id=OBS2,
            ),
            review_item(
                key="row-a:audited-target:1",
                name="행정안전부",
                observation_id=OBS1,
            ),
            review_item(
                key="row-c:audited-target:3",
                name="행정안전부",
                observation_id=OBS2,
            ),
        ),
    )
    report = build_orggo_organization_proposal(rows, review, [])
    payload = report.to_dict()
    assert payload["semantics"] == ORGGO_ORGANIZATION_PROPOSAL_SEMANTICS
    assert payload["status"] == "REVIEW_ONLY"
    assert payload["proposal_count"] == 2
    assert payload["gukgam_occurrence_count"] == 3
    assert [item.organization_name for item in report.items] == [
        "과학기술정보통신부",
        "행정안전부",
    ]
    assert [x.review_key for x in report.items[1].occurrences] == [
        "row-a:audited-target:1",
        "row-c:audited-target:3",
    ]
    assert "orgCode=1741000" in report.items[1].source_locator
    assert "chartId=55" in report.items[1].source_locator


def test_exact_one_and_nonmatching_provider_rows_are_ignored() -> None:
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
            review_item(
                key="row-b:audited-target:1",
                name="없는기관",
                observation_id=OBS2,
            ),
        ),
    )
    report = build_orggo_organization_proposal(
        [provider("행정안전부", "1741000", "55")],
        review,
        [Organization(id=ORG1, name="행정안전부")],
    )
    assert report.items == ()


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
    with pytest.raises(OrgGoOrganizationProposalError, match="already uses exact name"):
        build_orggo_organization_proposal(
            [provider("행정안전부", "1741000", "55")],
            review,
            [Organization(name="행정안전부")],
        )


def test_duplicate_provider_code_or_name_fails_closed() -> None:
    empty_review = GukgamOrganizationBindingReviewReport(
        organization_universe_count=0,
        items=(),
    )
    with pytest.raises(OrgGoOrganizationProposalError, match="duplicate org_code"):
        build_orggo_organization_proposal(
            [
                provider("기관A", "1111111", "1"),
                provider("기관B", "1111111", "2"),
            ],
            empty_review,
            [],
        )
    with pytest.raises(OrgGoOrganizationProposalError, match="name is not unique"):
        build_orggo_organization_proposal(
            [
                provider("기관A", "1111111", "1"),
                provider("기관A", "2222222", "2"),
            ],
            empty_review,
            [],
        )


def test_no_exact_item_with_candidates_fails_closed() -> None:
    review = GukgamOrganizationBindingReviewReport(
        organization_universe_count=0,
        items=(
            review_item(
                key="row-a:audited-target:1",
                name="행정안전부",
                observation_id=OBS1,
                candidates=(OrganizationBindingCandidate(organization_id=ORG1, name="행정안전부"),),
            ),
        ),
    )
    with pytest.raises(OrgGoOrganizationProposalError, match="unexpectedly contains candidates"):
        build_orggo_organization_proposal(
            [provider("행정안전부", "1741000", "55")],
            review,
            [],
        )

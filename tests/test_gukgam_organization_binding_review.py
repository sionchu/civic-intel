from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from packages.domain.contracts import Organization
from packages.rendering.gukgam_organization_binding_review import (
    EXACT_MULTIPLE,
    EXACT_ONE,
    GUKGAM_ORGANIZATION_BINDING_REVIEW_SEMANTICS,
    NO_EXACT,
    build_gukgam_organization_binding_review,
)
from packages.rendering.gukgam_schedule_review import (
    GukgamCommitteeScheduleReview,
    GukgamScheduleReviewReport,
    GukgamScheduleReviewRow,
    GukgamScheduleReviewSource,
)


def schedule_report() -> GukgamScheduleReviewReport:
    source = GukgamScheduleReviewSource(
        source_id=uuid4(),
        snapshot_id=uuid4(),
        url="https://test.na.go.kr/plan.pdf",
        title="2026년도 국정감사계획서.pdf — 테스트위원회",
        publisher="대한민국 국회 테스트위원회",
        attachment_sha256="a" * 64,
        rights_mark="KOGL_TYPE_1",
        source_class="official_reviewed_committee_attachment",
    )
    row = GukgamScheduleReviewRow(
        observation_id=uuid4(),
        provider_record_key="test:schedule:1",
        audit_date="2026-10-06",
        time_text="10:00",
        venue="국회",
        section="감사일정",
        audited_targets=("기관 A", "기관 B", "기관 C"),
        page_number=3,
    )
    return GukgamScheduleReviewReport(
        committees=(
            GukgamCommitteeScheduleReview(
                committee_name="테스트위원회",
                source_published_date="2026-09-15",
                source=source,
                rows=(row,),
            ),
        )
    )


def test_exact_name_overlap_is_review_discovery_only() -> None:
    organization_a = Organization(name="기관 A")
    duplicate_b1 = Organization(name="기관 B")
    duplicate_b2 = Organization(name="기관 B")
    report = build_gukgam_organization_binding_review(
        schedule_report(),
        [organization_a, duplicate_b1, duplicate_b2, Organization(name="기관C")],
    ).to_dict()

    assert report["semantics"] == GUKGAM_ORGANIZATION_BINDING_REVIEW_SEMANTICS
    assert report["match_rule"] == "EXACT_CANONICAL_NAME_EQUALITY_DISCOVERY_ONLY"
    assert report["mention_count"] == 3
    assert report["distinct_target_count"] == 3
    assert report["mention_match_classes"] == {
        EXACT_MULTIPLE: 1,
        EXACT_ONE: 1,
        NO_EXACT: 1,
    }

    items = {item["audited_target"]: item for item in report["items"]}
    assert items["기관 A"]["match_class"] == EXACT_ONE
    assert items["기관 A"]["candidates"] == [
        {"organization_id": str(organization_a.id), "name": "기관 A"}
    ]
    assert items["기관 B"]["match_class"] == EXACT_MULTIPLE
    assert len(items["기관 B"]["candidates"]) == 2
    assert items["기관 C"]["match_class"] == NO_EXACT
    assert items["기관 C"]["candidates"] == []
    for item in report["items"]:
        assert set(item) == {
            "review_key",
            "committee_name",
            "audit_date",
            "provider_record_key",
            "observation_id",
            "audited_target",
            "match_class",
            "candidates",
        }
        for candidate in item["candidates"]:
            assert set(candidate) == {"organization_id", "name"}


def test_superseded_organization_is_not_a_binding_candidate() -> None:
    timestamp = datetime.now(UTC)
    current = Organization(name="기관 A", recorded_at=timestamp)
    superseded = Organization(
        name="기관 A",
        recorded_at=timestamp,
        superseded_at=timestamp,
    )
    report = build_gukgam_organization_binding_review(
        schedule_report(),
        [current, superseded],
    ).to_dict()

    item = next(item for item in report["items"] if item["audited_target"] == "기관 A")
    assert item["match_class"] == EXACT_ONE
    assert item["candidates"] == [
        {"organization_id": str(current.id), "name": current.name}
    ]

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

from apps.api import operator_review
from packages.domain.contracts import Claim, FeederObservation, Organization
from packages.domain.enums import EpistemicStatus, PublicationStatus, SourceRunStatus
from packages.rendering.gukgam_organization_binding_review import (
    EXACT_ONE,
    NO_EXACT,
    GukgamOrganizationBindingReviewItem,
    GukgamOrganizationBindingReviewReport,
    OrganizationBindingCandidate,
)
from packages.rendering.gukgam_organization_claim import GUKGAM_AUDIT_TARGET_PREDICATE
from packages.rendering.mois_organization_proposal import (
    MOIS_FEEDER,
    MOIS_IDENTITY_SEMANTICS,
    MOIS_ORGANIZATION_PROPOSAL_SEMANTICS,
    MOIS_SCOPE_KEY,
    MOIS_SEMANTIC_SCOPE,
)

ORG_ID = UUID("10000000-0000-0000-0000-000000000001")
GUKGAM_OBSERVATION_ID = UUID("20000000-0000-0000-0000-000000000001")
MOIS_OBSERVATION_ID = UUID("30000000-0000-0000-0000-000000000001")


class FakeReviewRepository:
    def __init__(
        self,
        *,
        claims: list[Claim] | None = None,
        checkpoint: object | None = None,
        run: object | None = None,
        hash_manifest: list[tuple[str, str]] | None = None,
        observations: dict[UUID, FeederObservation] | None = None,
    ) -> None:
        self._claims = claims or []
        self._checkpoint = checkpoint
        self._run = run
        self._hash_manifest = hash_manifest or []
        self._observations = observations or {}

    def claims(self, **_: object) -> list[Claim]:
        return list(self._claims)

    def source_checkpoint(self, feeder: str, scope_key: str):
        assert feeder == MOIS_FEEDER
        assert scope_key == MOIS_SCOPE_KEY
        return self._checkpoint

    def source_run(self, run_id: UUID):
        assert self._checkpoint is not None
        assert run_id == self._checkpoint.last_run_id
        return self._run

    def feeder_observation_hash_manifest(
        self, feeder: str, scope_key: str
    ) -> list[tuple[str, str]]:
        assert feeder == MOIS_FEEDER
        assert scope_key == MOIS_SCOPE_KEY
        return list(self._hash_manifest)

    def feeder_observation(self, observation_id: UUID) -> FeederObservation | None:
        return self._observations.get(observation_id)
def _review_item(
    *,
    review_key: str,
    name: str,
    match_class: str,
    organization_id: UUID | None = None,
    observation_id: UUID = GUKGAM_OBSERVATION_ID,
) -> GukgamOrganizationBindingReviewItem:
    candidates = (
        ()
        if organization_id is None
        else (
            OrganizationBindingCandidate(
                organization_id=organization_id,
                name=name,
            ),
        )
    )
    return GukgamOrganizationBindingReviewItem(
        review_key=review_key,
        committee_name="테스트위원회",
        audit_date="2026-10-01",
        provider_record_key=review_key.split(":audited-target:", 1)[0],
        observation_id=observation_id,
        audited_target=name,
        match_class=match_class,
        candidates=candidates,
    )


def _published_gukgam_claim(review_key: str) -> Claim:
    return Claim(
        organization_id=ORG_ID,
        proposition="공식 계획서에 피감대상으로 기재되어 있다.",
        subject="기존기관",
        predicate=GUKGAM_AUDIT_TARGET_PREDICATE,
        object_text="테스트위원회 · 2026-10-01 피감대상",
        qualifiers={"provider_record_key": review_key},
        epistemic_status=EpistemicStatus.FACT,
        publication_status=PublicationStatus.PUBLISHED,
        asserted_as_true=True,
    )


def test_gukgam_current_review_excludes_existing_claim_and_keeps_no_write() -> None:
    organization = Organization(id=ORG_ID, name="기존기관")
    pending_key = "schedule:1:audited-target:1"
    existing_key = "schedule:2:audited-target:1"
    review = GukgamOrganizationBindingReviewReport(
        organization_universe_count=1,
        items=(
            _review_item(
                review_key=pending_key,
                name=organization.name,
                match_class=EXACT_ONE,
                organization_id=organization.id,
            ),
            _review_item(
                review_key=existing_key,
                name=organization.name,
                match_class=EXACT_ONE,
                organization_id=organization.id,
            ),
        ),
    )
    repository = FakeReviewRepository(
        claims=[_published_gukgam_claim(existing_key)]
    )

    result = operator_review._gukgam_claim_review_inspection(
        repository, [organization], review
    )

    assert result["status"] == "HUMAN_REVIEW_REQUIRED_NO_WRITE"
    assert result["item_count"] == 1
    assert result["organization_count"] == 1
    assert result["existing_gukgam_claim_count"] == 1
    assert result["claim_commit_authorized"] is False
    assert result["items"][0]["review_key"] == pending_key
    assert len(result["manifest_sha256"]) == 64
def _mois_observation() -> FeederObservation:
    return FeederObservation(
        id=MOIS_OBSERVATION_ID,
        feeder=MOIS_FEEDER,
        scope_key=MOIS_SCOPE_KEY,
        provider_record_key="A000001",
        snapshot_id=UUID("40000000-0000-0000-0000-000000000001"),
        run_id=UUID("50000000-0000-0000-0000-000000000001"),
        semantic_scope=MOIS_SEMANTIC_SCOPE,
        identity_hints={
            "record_kind": "organization_registry_record",
            "external_ids": {"mois_org_cd": "A000001"},
            "organization_name": "새기관",
            "materialization": "REVIEW_ONLY",
        },
        normalized={
            "org_code": "A000001",
            "full_name": "새기관",
            "lowest_name": "새기관",
            "type_big": "산하기관",
            "type_mid": "정부출연기관",
            "parent_org_code": "P000001",
            "top_org_code": "T000001",
            "representative_org_code": "R000001",
            "base_date": "2026-01-01",
            "changed_date": "2026-02-01",
            "stop_selector": "0",
            "identity_semantics": MOIS_IDENTITY_SEMANTICS,
        },
        content_hash="a" * 64,
    )


def _mois_artifact() -> dict[str, object]:
    provider = operator_review.mois_organization_proposal_provider_row(
        _mois_observation()
    ).to_dict()
    occurrence = {
        "review_key": "schedule:3:audited-target:1",
        "committee_name": "테스트위원회",
        "audit_date": "2026-10-01",
        "provider_record_key": "schedule:3",
        "observation_id": str(GUKGAM_OBSERVATION_ID),
        "audited_target": "새기관",
    }
    return {
        "semantics": MOIS_ORGANIZATION_PROPOSAL_SEMANTICS,
        "status": "REVIEW_ONLY",
        "provider_universe_count": 1,
        "candidate_provider_row_count": 1,
        "current_organization_count": 0,
        "gukgam_no_exact_distinct_target_count": 2,
        "proposal_count": 1,
        "gukgam_occurrence_count": 1,
        "ambiguous_distinct_target_count": 0,
        "unmatched_distinct_target_count": 1,
        "canonical_name_conflict_count": 0,
        "items": [
            {
                "proposal_status": "REVIEW_REQUIRED_NO_WRITE",
                "organization_name": "새기관",
                "provider": provider,
                "current_exact_canonical_match_count": 0,
                "occurrence_count": 1,
                "gukgam_occurrences": [occurrence],
            }
        ],
        "ambiguous_items": [],
        "limitations": [],
    }
def _mois_review() -> GukgamOrganizationBindingReviewReport:
    return GukgamOrganizationBindingReviewReport(
        organization_universe_count=0,
        items=(
            _review_item(
                review_key="schedule:3:audited-target:1",
                name="새기관",
                match_class=NO_EXACT,
            ),
            _review_item(
                review_key="schedule:4:audited-target:1",
                name="아직없는기관",
                match_class=NO_EXACT,
                observation_id=UUID(
                    "20000000-0000-0000-0000-000000000002"
                ),
            ),
        ),
    )


def _mois_repository() -> FakeReviewRepository:
    observation = _mois_observation()
    manifest = [(observation.provider_record_key, observation.content_hash)]
    run_id = UUID("50000000-0000-0000-0000-000000000099")
    checkpoint = SimpleNamespace(
        cursor="1",
        last_run_id=run_id,
        metadata={
            "total_count": 1,
            "seen_provider_count": 1,
            "seen_provider_manifest_sha256": operator_review._provider_manifest_sha256(
                manifest
            ),
            "expected_pages": 1,
            "source_contract": "mois_standard_organization_code_v1",
            "stop_selt": "0",
        },
    )
    run = SimpleNamespace(
        id=run_id,
        feeder=MOIS_FEEDER,
        scope_key=MOIS_SCOPE_KEY,
        status=SourceRunStatus.SUCCESS,
        checkpoint_after="1",
        metadata={
            "source_contract": "mois_standard_organization_code_v1",
            "stop_selt": "0",
        },
    )
    return FakeReviewRepository(
        checkpoint=checkpoint,
        run=run,
        hash_manifest=manifest,
        observations={observation.id: observation},
    )


def test_mois_current_review_revalidates_provider_and_occurrences(
    tmp_path: Path, monkeypatch
) -> None:
    artifact_path = tmp_path / "mois-proposal.json"
    artifact_path.write_text(
        json.dumps(_mois_artifact(), ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.setattr(operator_review, "MOIS_PROPOSAL", artifact_path)

    result = operator_review._mois_review_inspection(
        _mois_repository(), [], _mois_review()
    )

    assert result["status"] == "HUMAN_REVIEW_REQUIRED_NO_WRITE"
    assert result["proposal_count"] == 1
    assert result["occurrence_count"] == 1
    assert result["unmatched_distinct_target_count"] == 1
    assert result["ambiguous_distinct_target_count"] == 0
    assert result["materialization_authorized"] is False
    item = result["items"][0]
    assert item["organization_name"] == "새기관"
    assert item["type_big"] == "산하기관"
    assert item["representative_org_code"] == "R000001"
    assert item["base_date"] == "2026-01-01"
    assert item["changed_date"] == "2026-02-01"
    assert item["occurrences"] == [
        {
            "review_key": "schedule:3:audited-target:1",
            "committee_name": "테스트위원회",
            "audit_date": "2026-10-01",
            "audited_target": "새기관",
            "observation_id": str(GUKGAM_OBSERVATION_ID),
        }
    ]
def test_mois_current_review_fails_closed_when_no_exact_set_drifts(
    tmp_path: Path, monkeypatch
) -> None:
    artifact_path = tmp_path / "mois-proposal.json"
    artifact_path.write_text(
        json.dumps(_mois_artifact(), ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.setattr(operator_review, "MOIS_PROPOSAL", artifact_path)
    changed_review = GukgamOrganizationBindingReviewReport(
        organization_universe_count=0,
        items=(
            _review_item(
                review_key="schedule:3:audited-target:1",
                name="새기관",
                match_class=NO_EXACT,
            ),
        ),
    )

    result = operator_review._mois_review_inspection(
        _mois_repository(), [], changed_review
    )

    assert result["status"] == "CURRENT_REVIEW_DRIFT"
    assert result["write_performed"] is False
    assert result["items"] == []

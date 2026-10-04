from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from test_gukgam_reviewed_claim_import import migrated_repository

import packages.rendering.gukgam_committee_members as projection_module
from packages.domain.db import ClaimEvidenceRow, ClaimRow, OrganizationRow, PersonRow
from packages.persistence import SqlAlchemyRepository
from packages.rendering.gukgam_committee_members import (
    GUKGAM_COMMITTEE_ROSTER_PREDICATES,
    build_gukgam_committee_members_projection,
)
from packages.rendering.gukgam_organization_claim import (
    GukgamAuditTargetProjection,
    GukgamAuditTargetProjectionItem,
)

NOW = datetime(2026, 9, 1, tzinfo=UTC)
COMMITTEE = "국방위원회"


def _claim_row(subject: dict, predicate: str, text: str, *, status: str = "PUBLISHED",
               superseded: bool = False, qualifiers: dict | None = None) -> ClaimRow:
    return ClaimRow(
        id=str(uuid4()),
        proposition=f"{predicate} {text}",
        subject="subject",
        predicate=predicate,
        object_text=text,
        qualifiers=qualifiers or {},
        epistemic_status="FACT",
        publication_status=status,
        asserted_as_true=True,
        resolution_note=None,
        valid_from=NOW,
        valid_to=None,
        recorded_at=NOW,
        superseded_at=NOW if superseded else None,
        person_id=subject.get("person_id"),
        organization_id=subject.get("organization_id"),
    )


def _evidence_row(claim: ClaimRow) -> ClaimEvidenceRow:
    return ClaimEvidenceRow(
        id=str(uuid4()),
        claim_id=claim.id,
        source_id=str(uuid4()),
        snapshot_id=None,
        feeder_observation_id=None,
        stance="SUPPORT",
        excerpt=None,
    )


def _seed(repository: SqlAlchemyRepository) -> tuple[list[UUID], list[UUID]]:
    """Two People and two Organizations; claims of mixed predicate/status/evidence."""

    person_ids: list[UUID] = []
    organization_ids: list[UUID] = []
    with repository.sessions() as session:
        for index in range(2):
            person_id = str(uuid4())
            person_ids.append(UUID(person_id))
            session.add(
                PersonRow(
                    id=person_id, canonical_name=f"의원{index}", birth_date=None,
                    identity_status="RESOLVED", valid_from=NOW, valid_to=None,
                    recorded_at=NOW, superseded_at=None,
                )
            )
            organization_id = str(uuid4())
            organization_ids.append(UUID(organization_id))
            session.add(
                OrganizationRow(
                    id=organization_id, name=f"기관{index}", valid_from=NOW, valid_to=None,
                    recorded_at=NOW, superseded_at=None,
                )
            )
        session.flush()
        for person_id, organization_id in zip(person_ids, organization_ids, strict=True):
            for subject in ({"person_id": str(person_id)}, {"organization_id": str(organization_id)}):
                is_person = "person_id" in subject
                wanted = (
                    ("ASSEMBLY_COMMITTEES", f"운영위원회, {COMMITTEE}"),
                    ("ASSEMBLY_PARTY", "테스트정당"),
                ) if is_person else (("LISTED_AS_GUKGAM_AUDIT_TARGET", "target"),)
                rows = [_claim_row(subject, p, t, qualifiers={"k": p}) for p, t in wanted]
                rows += [
                    _claim_row(subject, "NOISE", "noise"),
                    _claim_row(subject, wanted[0][0], "draft", status="DRAFT"),
                    _claim_row(subject, wanted[0][0], "old", superseded=True),
                ]
                for row in rows:
                    session.add(row)
                session.flush()
                for row in rows[:-1]:  # the last (superseded) claim is never read
                    session.add(_evidence_row(row))
                # one published claim deliberately has no Evidence rows at all
                session.add(_claim_row(subject, "NO_EVIDENCE", "bare"))
        session.commit()
    return person_ids, organization_ids


def _reference_contexts(repository, ids, *, organization: bool):
    """The per-subject semantics, computed through the simple one-subject read paths."""

    result = {}
    for subject_id in ids:
        claims = (
            repository.claims(organization_id=subject_id, published_only=True, current_only=True)
            if organization
            else repository.claims(subject_id, True, current_only=True)
        )
        result[subject_id] = (
            tuple(claims),
            {claim.id: tuple(repository.evidence_for(claim.id)) for claim in claims},
        )
    return result


def _normalised(contexts):
    return {
        subject_id: (
            [claim.id for claim in claims],
            {claim_id: sorted(item.id for item in items) for claim_id, items in evidence.items()},
        )
        for subject_id, (claims, evidence) in contexts.items()
    }


def test_person_contexts_match_reference_and_predicate_filter_is_a_pure_subset(
    tmp_path: Path,
) -> None:
    repository, _ = migrated_repository(tmp_path / "contexts.db")
    person_ids, _ = _seed(repository)

    full = repository.published_person_claim_contexts(person_ids)
    assert _normalised(full) == _normalised(
        _reference_contexts(repository, person_ids, organization=False)
    )
    # claims without Evidence keep an (empty) evidence entry, as before
    assert any(not evidence for _, per_claim in full.values() for evidence in per_claim.values())

    narrowed = repository.published_person_claim_contexts(
        person_ids, predicates=GUKGAM_COMMITTEE_ROSTER_PREDICATES
    )
    assert set(narrowed) == set(person_ids)
    for person_id in person_ids:
        claims, evidence = full[person_id]
        keep = [c for c in claims if c.predicate in GUKGAM_COMMITTEE_ROSTER_PREDICATES]
        assert keep
        assert [c.id for c in narrowed[person_id][0]] == [c.id for c in keep]
        assert narrowed[person_id][1] == {c.id: evidence[c.id] for c in keep}


def test_organization_contexts_match_reference_and_predicate_filter_is_a_pure_subset(
    tmp_path: Path,
) -> None:
    repository, _ = migrated_repository(tmp_path / "org-contexts.db")
    _, organization_ids = _seed(repository)

    full = repository.published_organization_claim_contexts(organization_ids)
    assert _normalised(full) == _normalised(
        _reference_contexts(repository, organization_ids, organization=True)
    )

    narrowed = repository.published_organization_claim_contexts(
        organization_ids, predicates=("LISTED_AS_GUKGAM_AUDIT_TARGET",)
    )
    for organization_id in organization_ids:
        claims, evidence = full[organization_id]
        keep = [c for c in claims if c.predicate == "LISTED_AS_GUKGAM_AUDIT_TARGET"]
        assert keep
        assert [c.id for c in narrowed[organization_id][0]] == [c.id for c in keep]
        assert narrowed[organization_id][1] == {c.id: evidence[c.id] for c in keep}

    assert repository.published_organization_claim_contexts([]) == {}
    assert repository.published_person_claim_contexts([], predicates=("X",)) == {}


def test_committee_projection_is_identical_with_narrowed_contexts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        projection_module,
        "validate_claim_publication",
        lambda *args, **kwargs: SimpleNamespace(publishable=True, failures=()),
    )
    repository, _ = migrated_repository(tmp_path / "projection.db")
    person_ids, _ = _seed(repository)
    # the seeded roster claims need the roster contract qualifiers to pass the fail-closed check
    with repository.sessions() as session:
        for row in session.query(ClaimRow).filter(
            ClaimRow.predicate.in_(GUKGAM_COMMITTEE_ROSTER_PREDICATES)
        ):
            row.qualifiers = {
                "source_contract": "assembly_member_roster",
                "field_name": "committees" if row.predicate == "ASSEMBLY_COMMITTEES" else "party",
            }
        session.commit()

    ids = uuid4()
    item = GukgamAuditTargetProjectionItem(
        organization_id=uuid4(), organization_name="기관", committee_name=COMMITTEE,
        audit_date="2026-10-14", time_text=None, venue=None, section="s", page_number=1,
        source_published_date="2026-09-20", claim_id=uuid4(), evidence_ids=(ids,),
        source_ids=(ids,), snapshot_ids=(ids,), observation_ids=(ids,),
    )
    targets = GukgamAuditTargetProjection(year=2026, items=(item,))
    people = repository.public_people()

    def build(contexts):
        return build_gukgam_committee_members_projection(
            targets, people, contexts, sources={}, policies={}
        ).to_dict()

    full = build(repository.published_person_claim_contexts(person_ids))
    narrowed = build(
        repository.published_person_claim_contexts(
            person_ids, predicates=GUKGAM_COMMITTEE_ROSTER_PREDICATES
        )
    )
    assert full == narrowed
    assert full["committees"][0]["member_count"] == 2

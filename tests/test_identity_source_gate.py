import pytest

from packages.persistence.models import (
    FeederObservationRow,
    SourcePolicyRow,
    SourceRow,
    SourceSnapshotRow,
)
from packages.verification.materialization import MaterializationError
from tests.test_materialization import (
    OnePageRoster,
    enumerate_rows,
    member_row,
    migrated_repository,
)


def counts(db):
    with db(read_only=True) as uow:
        return (
            len(uow.public.people()),
            len(uow.public.claims()),
            len(uow.identity.person_observation_links()),
            len(uow.review.identity_review_items()),
        )


@pytest.mark.parametrize("branch", ["create", "link", "review"])
def test_revoked_metadata_policy_blocks_every_identity_write(tmp_path, branch):
    db = migrated_repository(tmp_path / (branch + ".db"))
    rows = [member_row("M-001", "동명이인")]
    if branch == "review":
        rows.append(member_row("M-002", "동명이인"))
    roster = OnePageRoster(rows)
    observations = enumerate_rows(db, roster)
    observation = observations[0]
    if branch in {"link", "review"}:
        db.application.identity.materialize_feeder_observation(observation.id)
        if branch == "review":
            observation = observations[1]
        else:
            roster.rows[0] = member_row("M-001", "동명이인", party="변경정당")
            observation = next(
                item
                for item in enumerate_rows(db, roster)
                if item.content_hash != observation.content_hash
            )
    before = counts(db)
    with db.sessions() as session:
        snapshot = session.get(SourceSnapshotRow, str(observation.snapshot_id))
        source = session.get(SourceRow, snapshot.source_id)
        session.get(SourcePolicyRow, source.policy_id).can_store_metadata = False
        session.commit()
    with pytest.raises(MaterializationError, match="does not permit metadata storage"):
        db.application.identity.materialize_feeder_observation(observation.id)
    assert counts(db) == before


@pytest.mark.parametrize("mismatch", ["policy", "snapshot", "source", "scope", "provider"])
def test_spoofed_assembly_provenance_cannot_authorize_identity(tmp_path, mismatch):
    db = migrated_repository(tmp_path / (mismatch + ".db"))
    observation = enumerate_rows(db, OnePageRoster([member_row("M-001", "가의원")]))[0]
    before = counts(db)
    with db.sessions() as session:
        row = session.get(FeederObservationRow, str(observation.id))
        snapshot = session.get(SourceSnapshotRow, str(observation.snapshot_id))
        source = session.get(SourceRow, snapshot.source_id)
        if mismatch == "policy":
            session.get(SourcePolicyRow, source.policy_id).source_class = "unreviewed"
        elif mismatch == "snapshot":
            snapshot.metadata_json = {"api_code": "unreviewed"}
        elif mismatch == "source":
            source.url = "https://open.assembly.go.kr/unreviewed"
        elif mismatch == "scope":
            row.scope_key = "unreviewed_scope"
        else:
            row.normalized_json = dict(row.normalized_json) | {"member_code": "OTHER-KEY"}
        session.commit()
    with pytest.raises(MaterializationError):
        db.application.identity.materialize_feeder_observation(observation.id)
    assert counts(db) == before

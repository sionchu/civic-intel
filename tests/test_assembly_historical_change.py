from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from apps.api.main import create_app
from packages.connectors.base import ConnectorDocument
from packages.connectors.open_assembly_historical import (
    HISTORICAL_API_CODE,
    HISTORICAL_FEEDER,
    HISTORICAL_REVIEWED_INPUT_SCOPE,
    AssemblyHistoricalCareerError,
    AssemblyHistoricalCareerRecord,
    parse_historical_career_records,
    validate_reviewed_packet,
)
from packages.domain.contracts import (
    ClaimEvidence,
    FeederObservation,
    Person,
    Source,
    SourcePolicy,
    SourceSnapshot,
)
from packages.domain.enums import (
    EvidenceStance,
    SourceCollectionMode,
    SourceRunStatus,
)
from packages.persistence import SqlAlchemyRepository
from packages.rendering.profile_projection import (
    CHANGE_METHOD_VERSION,
    build_profile_projection,
)
from packages.verification.assembly_historical_review import (
    build_reviewed_assembly_career_claim,
)
from packages.verification.identity import IdentityCandidate
from packages.verification.person_onboarding import ReviewedPersonBundle, ReviewedPersonImportError
from packages.verification.profile_target import (
    ProfileTargetObservation,
    build_profile_research_target,
)
from workers.ingest import IngestionPipeline

FIXTURE = Path(__file__).parent / "fixtures" / "assembly_historical_known_positive_001.json"
PERSON_ID = UUID("00000000-0000-0000-0000-000000009301")
POLICY_ID = UUID("10000000-0000-0000-0000-000000009301")


def migrated_repository(database: Path) -> SqlAlchemyRepository:
    database_url = f"sqlite:///{database.as_posix()}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")
    return SqlAlchemyRepository(database_url)


def fixture_payload() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def fixture_policy() -> SourcePolicy:
    return SourcePolicy(
        id=POLICY_ID,
        domain="open.assembly.go.kr::nfzegpkvaclgtscxt",
        source_class="official_assembly_historical_reviewed_packet",
        collection_mode=SourceCollectionMode.DISCOVERY_ONLY,
        can_fetch=False,
        can_store_metadata=True,
        can_store_fulltext=False,
        can_send_to_ai=False,
        can_show_excerpt=False,
        can_commercialize=False,
        terms_checked_at=datetime(2026, 9, 13, tzinfo=UTC),
        policy_note=(
            "Bounded reviewed packet only. The historical service remains L1 with L3 blocked; "
            "no live fetch, complete-universe claim or correction interpretation is permitted."
        ),
    )


def source_document(record: AssemblyHistoricalCareerRecord) -> ConnectorDocument:
    body = json.dumps(
        {
            HISTORICAL_API_CODE: [
                {"head": [{"list_total_count": "1"}]},
                {
                    "row": [
                        {
                            "HG_NM": record.name_ko,
                            "MONA_CD": record.member_code,
                            "PROFILE_UNIT_CD": record.profile_unit_code,
                            "PROFILE_UNIT_NM": record.profile_unit_name,
                            "FRTO_DATE": record.frto_date,
                            "PROFILE_SJ": record.profile_sj,
                        }
                    ]
                },
            ]
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return ConnectorDocument(
        url=(
            "https://open.assembly.go.kr/portal/openapi/"
            f"{HISTORICAL_API_CODE}?Type=json&pIndex=1&pSize=100&"
            f"PROFILE_UNIT_CD={record.profile_unit_code}"
        ),
        title=f"국회 역대 국회의원 의원이력 {record.profile_unit_name}",
        publisher="국회 국회사무처",
        published_at=None,
        body=body,
        metadata={
            "capture": "bounded_reviewed_packet",
            "fixture": "ASSEMBLY_HISTORICAL_KNOWN_POSITIVE_001",
            "profile_unit_cd": record.profile_unit_code,
            "source_record_identity": "PROVIDER_ROW_ID_UNAVAILABLE",
        },
    )


def fixture_document() -> ConnectorDocument:
    payload = fixture_payload()
    return ConnectorDocument(
        url=f"https://open.assembly.go.kr/portal/openapi/{HISTORICAL_API_CODE}",
        title="국회 역대 국회의원 의원이력 bounded fixture",
        publisher="국회 국회사무처",
        published_at=None,
        body=json.dumps(
            {HISTORICAL_API_CODE: [{"row": payload["records"]}]},
            ensure_ascii=False,
            sort_keys=True,
        ),
        metadata={"capture": "bounded_reviewed_packet"},
    )


def stage_record(
    repository: SqlAlchemyRepository,
    record: AssemblyHistoricalCareerRecord,
    policy: SourcePolicy,
) -> tuple[Source, SourceSnapshot, FeederObservation]:
    document = source_document(record)
    ingestion = IngestionPipeline(connector=None).ingest_document(document, policy)  # type: ignore[arg-type]
    scope_key = f"reviewed:{record.provider_record_key}"
    run = repository.start_source_run(
        HISTORICAL_FEEDER,
        scope_key,
        metadata={
            "capture": "bounded_reviewed_packet",
            "automation_ceiling": "L1",
            "provider_record_identity": "PROVIDER_ROW_ID_UNAVAILABLE",
        },
    )
    observation = record.to_observation(
        run_id=run.id,
        snapshot_id=ingestion.snapshot.id,
        scope_key=scope_key,
    )
    commit = repository.commit_source_page(
        run_id=run.id,
        policy=policy,
        source=ingestion.source,
        snapshot=ingestion.snapshot,
        observations=[observation],
        cursor=record.profile_unit_code,
        checkpoint_metadata={
            "capture": "bounded_reviewed_packet",
            "provider_record_identity": "PROVIDER_ROW_ID_UNAVAILABLE",
        },
    )
    repository.finish_source_run(run.id, SourceRunStatus.SUCCESS)
    persisted = repository.feeder_observation(commit.observation_ids[0])
    assert persisted is not None
    return ingestion.source, ingestion.snapshot, persisted


def load_records() -> tuple[AssemblyHistoricalCareerRecord, ...]:
    return validate_reviewed_packet(parse_historical_career_records(fixture_document()))


def load_reviewed_bundle(
    sources: tuple[Source, ...],
    snapshots: tuple[SourceSnapshot, ...],
    observations: tuple[FeederObservation, ...],
) -> ReviewedPersonBundle:
    payload = fixture_payload()
    person = Person.model_validate(payload["person"])
    source_refs = tuple(str(item.url) for item in sources)
    target = build_profile_research_target(
        ProfileTargetObservation(
            lane="ASSEMBLY_HISTORICAL_CAREER_REVIEW",
            candidate=IdentityCandidate(
                canonical_name=person.canonical_name,
                career_anchors=(f"assembly_mona_cd:{payload['member_code']}",),
            ),
            source_refs=source_refs,
            discovery_reasons=("BOUNDED_REVIEWED_SOURCE_PACKET",),
        )
    )
    claims = tuple(
        build_reviewed_assembly_career_claim(record, person_id=person.id).model_copy(
            update={"id": UUID(f"30000000-0000-0000-0000-0000000093{index:02d}")}
        )
        for index, record in enumerate(load_records(), start=1)
    )
    evidence = tuple(
        ClaimEvidence(
            id=UUID(f"40000000-0000-0000-0000-0000000093{index:02d}"),
            claim_id=claim.id,
            source_id=sources[index - 1].id,
            snapshot_id=snapshots[index - 1].id,
            feeder_observation_id=observations[index - 1].id,
            stance=EvidenceStance.SUPPORT,
        )
        for index, claim in enumerate(claims, start=1)
    )
    return ReviewedPersonBundle(
        person=person,
        profile_target=target,
        claims=claims,
        evidence=evidence,
    )


def test_parser_preserves_source_fields_and_does_not_invent_row_identity() -> None:
    records = load_records()
    assert [record.profile_unit_code for record in records] == ["100019", "100020"]
    assert records[0].valid_from.isoformat() == "2012-05-30"
    assert records[1].valid_from.isoformat() == "2016-05-30"
    assert records[0].provider_record_key == "XQ98168F:100019"
    assert records[0].normalized()["provider_record_identity"] == "PROVIDER_ROW_ID_UNAVAILABLE"
    assert records[0].normalized()["source_fields"]["PROFILE_SJ"] == "새누리당 울산 울주군"
    assert records[1].normalized()["source_fields"]["PROFILE_SJ"] == "무소속 울산 울주군"


def test_repeated_person_term_group_fails_closed_without_row_key() -> None:
    records = load_records()
    duplicate = AssemblyHistoricalCareerRecord(
        member_code=records[0].member_code,
        name_ko=records[0].name_ko,
        profile_unit_code=records[0].profile_unit_code,
        profile_unit_name=records[0].profile_unit_name,
        frto_date=records[0].frto_date,
        profile_sj="다른 snapshot 표시값",
        valid_from=records[0].valid_from,
        valid_to=records[0].valid_to,
    )
    with pytest.raises(AssemblyHistoricalCareerError, match="row identity is unavailable"):
        validate_reviewed_packet((records[0], duplicate))


def test_bounded_observation_claim_evidence_and_derived_change_vertical_slice(
    tmp_path: Path,
) -> None:
    repository = migrated_repository(tmp_path / "assembly-historical-change.db")
    policy = fixture_policy()
    records = load_records()
    staged = tuple(stage_record(repository, record, policy) for record in records)
    sources = tuple(item[0] for item in staged)
    snapshots = tuple(item[1] for item in staged)
    observations = tuple(item[2] for item in staged)

    repository.import_reviewed_person(load_reviewed_bundle(sources, snapshots, observations))

    claims = repository.claims(PERSON_ID, published_only=True, current_only=True)
    evidence = {claim.id: repository.evidence_for(claim.id)[0] for claim in claims}
    assert len(claims) == 2
    assert all(item.feeder_observation_id in {observation.id for observation in observations} for item in evidence.values())
    assert all(item.snapshot_id in {snapshot.id for snapshot in snapshots} for item in evidence.values())
    assert [item.status for item in repository.source_runs(HISTORICAL_FEEDER)] == [
        SourceRunStatus.SUCCESS,
        SourceRunStatus.SUCCESS,
    ]

    with TestClient(create_app(repository)) as client:
        response = client.get(f"/people/{PERSON_ID}")
    assert response.status_code == 200
    payload = response.json()
    sections = {item["id"]: item for item in payload["profile"]["sections"]}
    changes = sections["recent_changes"]
    assert changes["status"] == "AVAILABLE"
    assert len(changes["entries"]) == 1
    change = changes["entries"][0]
    assert change["kind"] == "CHANGE"
    assert change["epistemic_status"] is None
    assert change["details"]["method_version"] == CHANGE_METHOD_VERSION
    assert change["details"]["provider_identity"]["mona_cd"] == "XQ98168F"
    assert change["details"]["input_scope"]["correction_semantics"] == "IMMUTABLE_SNAPSHOT_ONLY"
    assert change["details"]["earlier"]["date"] == "2012-05-30"
    assert change["details"]["later"]["date"] == "2016-05-30"
    assert change["details"]["earlier"]["role_text"] == "새누리당 울산 울주군"
    assert change["details"]["later"]["role_text"] == "무소속 울산 울주군"
    assert change["evidence_ids"] == [str(evidence[claims[0].id].id), str(evidence[claims[1].id].id)]
    assert all(trace["feeder_observation_id"] for trace in change["evidence"])
    assert "퇴임" not in json.dumps(change, ensure_ascii=False)
    assert "원인" not in json.dumps(change, ensure_ascii=False)
    assert HISTORICAL_REVIEWED_INPUT_SCOPE in json.dumps(change, ensure_ascii=False)


def test_changed_same_group_is_new_immutable_observation_and_not_an_automatic_change(
    tmp_path: Path,
) -> None:
    repository = migrated_repository(tmp_path / "assembly-historical-version.db")
    policy = fixture_policy()
    original = load_records()[0]
    stage_record(repository, original, policy)
    corrected = AssemblyHistoricalCareerRecord(
        member_code=original.member_code,
        name_ko=original.name_ko,
        profile_unit_code=original.profile_unit_code,
        profile_unit_name=original.profile_unit_name,
        frto_date=original.frto_date,
        profile_sj="표시값 수정 후보",
        valid_from=original.valid_from,
        valid_to=original.valid_to,
    )
    stage_record(repository, corrected, policy)

    observations = repository.feeder_observations(
        HISTORICAL_FEEDER,
        f"reviewed:{original.provider_record_key}",
        original.provider_record_key,
    )
    assert len(observations) == 2
    assert observations[0].id != observations[1].id
    assert observations[0].normalized["source_fields"]["PROFILE_SJ"] == "새누리당 울산 울주군"
    assert observations[1].normalized["source_fields"]["PROFILE_SJ"] == "표시값 수정 후보"
    assert all(
        item.normalized["provider_record_identity"] == "PROVIDER_ROW_ID_UNAVAILABLE"
        for item in observations
    )


def test_reviewed_import_requires_snapshot_for_observation_provenance(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "assembly-historical-provenance.db")
    policy = fixture_policy()
    staged = tuple(stage_record(repository, record, policy) for record in load_records())
    sources = tuple(item[0] for item in staged)
    snapshots = tuple(item[1] for item in staged)
    observations = tuple(item[2] for item in staged)
    bundle = load_reviewed_bundle(sources, snapshots, observations)
    invalid_evidence = bundle.evidence[0].model_copy(update={"snapshot_id": None})
    invalid_bundle = replace(bundle, evidence=(invalid_evidence, *bundle.evidence[1:]))

    with pytest.raises(ReviewedPersonImportError, match="requires a snapshot"):
        repository.import_reviewed_person(invalid_bundle)

    assert repository.person(PERSON_ID) is None


def test_reviewed_import_rejects_mismatched_observation_snapshot(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "assembly-historical-mismatch.db")
    policy = fixture_policy()
    staged = tuple(stage_record(repository, record, policy) for record in load_records())
    sources = tuple(item[0] for item in staged)
    snapshots = tuple(item[1] for item in staged)
    observations = tuple(item[2] for item in staged)
    bundle = load_reviewed_bundle(sources, snapshots, observations)
    invalid_evidence = bundle.evidence[0].model_copy(update={"snapshot_id": snapshots[1].id})
    invalid_bundle = replace(bundle, evidence=(invalid_evidence, *bundle.evidence[1:]))

    with pytest.raises(ReviewedPersonImportError, match="snapshot does not match"):
        repository.import_reviewed_person(invalid_bundle)

    assert repository.person(PERSON_ID) is None


def test_same_group_versions_are_excluded_from_change_projection() -> None:
    policy = fixture_policy()
    record = load_records()[0]
    corrected = AssemblyHistoricalCareerRecord(
        member_code=record.member_code,
        name_ko=record.name_ko,
        profile_unit_code=record.profile_unit_code,
        profile_unit_name=record.profile_unit_name,
        frto_date=record.frto_date,
        profile_sj="표시값 수정 후보",
        valid_from=record.valid_from,
        valid_to=record.valid_to,
    )
    source = Source(
        url="https://open.assembly.go.kr/portal/openapi/nfzegpkvaclgtscxt?fixture=version",
        title="역대 국회의원 의원이력 version fixture",
        publisher="국회 국회사무처",
        policy_id=policy.id,
    )
    snapshots = (
        SourceSnapshot(
            id=UUID("21000000-0000-0000-0000-000000009301"),
            source_id=source.id,
            content_hash="a" * 64,
            metadata={"fixture": "version-1"},
        ),
        SourceSnapshot(
            id=UUID("21000000-0000-0000-0000-000000009302"),
            source_id=source.id,
            content_hash="b" * 64,
            metadata={"fixture": "version-2"},
        ),
    )
    observations = (
        record.to_observation(
            run_id=UUID("06577921-2808-4c95-9ddf-6b69070490bc"),
            snapshot_id=snapshots[0].id,
            scope_key="reviewed:XQ98168F:100019",
        ),
        corrected.to_observation(
            run_id=UUID("c8b1c9b7-3033-432f-8167-45d5023a4731"),
            snapshot_id=snapshots[1].id,
            scope_key="reviewed:XQ98168F:100019",
        ),
    )
    claims = (
        build_reviewed_assembly_career_claim(record, person_id=PERSON_ID),
        build_reviewed_assembly_career_claim(corrected, person_id=PERSON_ID),
    )
    evidence = tuple(
        ClaimEvidence(
            claim_id=claim.id,
            source_id=source.id,
            snapshot_id=snapshots[index].id,
            feeder_observation_id=observations[index].id,
            stance=EvidenceStance.SUPPORT,
        )
        for index, claim in enumerate(claims)
    )
    profile = build_profile_projection(
        Person.model_validate(fixture_payload()["person"]),
        claims,
        {claim.id: [item] for claim, item in zip(claims, evidence, strict=True)},
        [],
        [],
        sources={source.id: source},
        policies={policy.id: policy},
    )
    changes = next(item for item in profile["sections"] if item["id"] == "recent_changes")
    assert changes["status"] == "PARTIAL"
    assert changes["entries"] == []

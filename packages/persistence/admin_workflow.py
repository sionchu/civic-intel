"""Bounded operator review/commands over the single canonical repository/session."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid5

from sqlalchemy import String, cast, func, inspect, or_, select, text
from sqlalchemy.orm import Session

from packages.domain import db
from packages.domain.admin import (
    CORRECTION_PREDICATE,
    PERSON_ROLE_PREDICATE,
    AdminAction,
    AdminCommand,
)
from packages.domain.contracts import (
    Claim,
    ClaimEvidence,
    Organization,
    Person,
    Source,
    SourcePolicy,
)
from packages.domain.enums import (
    CrossLaneIdentityEvidenceType,
    EpistemicStatus,
    IdentityStatus,
    PublicationStatus,
)
from packages.rendering.alio_organization_content import (
    ALIO_EXECUTIVE_FEEDER,
    ALIO_EXECUTIVE_PREDICATE,
    ALIO_EXECUTIVE_SCOPE,
    ALIO_EXECUTIVE_SOURCE_CONTRACT,
    validate_alio_item4_observation,
)
from packages.verification.claims import validate_claim_publication
from packages.verification.cross_lane_identity import (
    CrossLaneIdentityEvidence,
    resolve_cross_lane_identity,
)
from packages.verification.identity import IdentityCandidate
from packages.verification.policy import PolicyAction, require_policy

SAFE_CHANGE_FIELDS = {
    "id",
    "canonical_name",
    "name",
    "identity_status",
    "person_id",
    "organization_id",
    "subject",
    "predicate",
    "object_text",
    "proposition",
    "epistemic_status",
    "publication_status",
    "asserted_as_true",
    "valid_from",
    "valid_to",
    "recorded_at",
    "superseded_at",
    "observation_id",
    "claim_id",
    "source_id",
    "snapshot_id",
    "feeder_observation_id",
    "stance",
    "candidate_person_id",
    "status",
    "reason_code",
    "resolved_at",
    "resolution_note",
    "action",
    "decision_class",
    "linked_at",
    "review_item_id",
    "created_at",
}


class AdminError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def normalized(value: Any) -> Any:
    if isinstance(value, datetime) and value.tzinfo is not None:
        return value.astimezone(UTC).isoformat()
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        return {str(key): normalized(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [normalized(item) for item in value]
    return value


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            normalized(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()


def row_data(row: Any) -> dict[str, Any]:
    return {column.key: getattr(row, column.key) for column in inspect(type(row)).columns}


def receipt(row: db.AdminOperationRow) -> dict[str, Any]:
    return {
        "version": digest({"id": row.id, "command_hash": row.command_hash, "state_hash": row.state_hash}),
        "id": row.id,
        "actor": row.actor,
        "action": row.action,
        "created_at": normalized(row.created_at),
        "reason": row.reason,
        "targets": row.targets,
        "changes": row.changes,
        "result": row.result,
    }


def admin_schema_ready(session: Session) -> bool:
    revision = session.scalar(text("SELECT version_num FROM alembic_version"))
    return revision == "0007"


def history(session: Session, offset: int = 0, limit: int = 25) -> dict[str, Any]:
    if not admin_schema_ready(session):
        return {"available": False, "total": 0, "items": [], "schema_required": "0007"}
    rows = session.scalars(
        select(db.AdminOperationRow)
        .order_by(db.AdminOperationRow.created_at.desc(), db.AdminOperationRow.id)
        .offset(offset)
        .limit(limit)
    ).all()
    return {
        "available": True,
        "total": session.scalar(select(func.count()).select_from(db.AdminOperationRow)),
        "items": [receipt(row) for row in rows],
        "offset": offset,
        "limit": limit,
    }


@dataclass
class Change:
    model: Any
    record_id: str
    before: dict[str, Any] | None
    after: dict[str, Any]

    def visible(self) -> dict[str, Any]:
        keys = {
            key
            for key in self.after
            if self.before is None or self.after[key] != self.before.get(key)
        }
        keys &= SAFE_CHANGE_FIELDS
        return {
            "table": self.model.__tablename__,
            "id": self.record_id,
            "operation": "CREATE" if self.before is None else "UPDATE",
            "before": normalized({key: self.before.get(key) for key in sorted(keys)})
            if self.before
            else None,
            "after": normalized({key: self.after[key] for key in sorted(keys)}),
        }


@dataclass
class Plan:
    session: Session
    command: AdminCommand
    locking: bool = False
    dependencies: dict[str, Any] = field(default_factory=dict)
    changes: dict[str, Change] = field(default_factory=dict)
    outcomes: list[dict[str, Any]] = field(default_factory=list)
    row_cache: dict[str, Any] = field(default_factory=dict)
    review_time: datetime = field(default_factory=lambda: datetime.now(UTC))

    def query(self, model: Any, *conditions: Any, limit: int = 250) -> list[Any]:
        statement = select(model).where(*conditions).order_by(model.id).limit(limit + 1)
        if self.locking:
            statement = statement.with_for_update()
        rows = list(self.session.scalars(statement).all())
        if len(rows) > limit:
            raise AdminError(
                "IMPACT_LIMIT",
                "영향 범위가 한 번에 처리할 수 있는 한도를 넘습니다. 범위를 나눠 검토하세요.",
            )
        self.dependencies[f"query:{len(self.dependencies)}:{model.__tablename__}"] = [
            row.id for row in rows
        ]
        for row in rows:
            self.dependencies[f"{model.__tablename__}:{row.id}"] = digest(row_data(row))
            self.row_cache[f"{model.__tablename__}:{row.id}"] = row
        return rows

    def get(self, model: Any, identifier: UUID | str | None) -> Any:
        if identifier is None:
            raise AdminError("MISSING_ID", "필수 대상 ID가 없습니다.")
        key = f"{model.__tablename__}:{identifier}"
        if key in self.row_cache:
            return self.row_cache[key]
        rows = self.query(model, model.id == str(identifier), limit=1)
        if not rows:
            raise AdminError("MISSING_RECORD", "선택한 레코드 또는 근거가 현재 DB에 없습니다.")
        return rows[0]

    def update(self, row: Any, **values: Any) -> None:
        model = type(row)
        key = f"{model.__tablename__}:{row.id}"
        change = self.changes.get(key)
        if change is None:
            change = Change(model, row.id, row_data(row), row_data(row))
            self.changes[key] = change
        change.after.update(values)

    def create(self, model: Any, **values: Any) -> None:
        identifier = str(values["id"])
        key = f"{model.__tablename__}:{identifier}"
        if key in self.changes or self.query(model, model.id == identifier, limit=1):
            raise AdminError("ID_CONFLICT", "새 레코드 ID가 이미 존재합니다.")
        self.changes[key] = Change(model, identifier, None, values)

    def uid(self, label: str) -> str:
        return str(uuid5(self.command.request_id, label))

    def time_fields(self) -> dict[str, Any]:
        return {
            "valid_from": self.review_time,
            "valid_to": None,
            "recorded_at": self.review_time,
            "superseded_at": None,
        }

    def state_hash(self) -> str:
        return digest(self.dependencies)

    def report(self) -> dict[str, Any]:
        return {
            "action": self.command.action.value,
            "selected_count": len(self.command.record_ids),
            "changes": [change.visible() for change in self.changes.values()],
            "outcomes": self.outcomes,
            "state_hash": self.state_hash(),
            "command_hash": digest(self.command.model_dump(mode="json")),
            "write_performed": False,
        }

    def apply(self) -> None:
        # Flush new rows by declared FK table order, not once for every selected row.
        # This keeps bounded batches practical over a private PostgreSQL connection.
        for table in db.Base.metadata.sorted_tables:
            additions = [
                change
                for change in self.changes.values()
                if change.before is None and change.model.__tablename__ == table.name
            ]
            if additions:
                self.session.add_all(change.model(**change.after) for change in additions)
                self.session.flush()
        for change in self.changes.values():
            if change.before is None:
                continue
            row = self.session.get(change.model, change.record_id)
            if row is None:
                raise AdminError(
                    "STALE_PREVIEW", "레코드가 변경되었습니다. 미리보기를 다시 실행하세요."
                )
            for name, value in change.after.items():
                if value != change.before.get(name):
                    setattr(row, name, value)
        self.session.flush()


def _current_person(plan: Plan, identifier: UUID | str | None) -> Any:
    row = plan.get(db.PersonRow, identifier)
    if row.superseded_at is not None:
        raise AdminError("INACTIVE_PERSON", "이미 비활성화된 인물입니다.")
    return row


def _evidence_context(
    plan: Plan, evidence_rows: list[Any]
) -> tuple[list[ClaimEvidence], dict, dict]:
    evidence, sources, policies = [], {}, {}
    for row in evidence_rows:
        item = ClaimEvidence.model_validate(row, from_attributes=True)
        source_row = plan.get(db.SourceRow, row.source_id)
        policy_row = plan.get(db.SourcePolicyRow, source_row.policy_id)
        source = Source.model_validate(source_row, from_attributes=True)
        policy = SourcePolicy.model_validate(policy_row, from_attributes=True)
        require_policy(policy, PolicyAction.STORE_METADATA)
        if row.snapshot_id:
            snapshot = plan.get(db.SourceSnapshotRow, row.snapshot_id)
            if snapshot.source_id != row.source_id:
                raise AdminError("PROVENANCE_CONFLICT", "Evidence와 수집본의 출처가 다릅니다.")
        if row.feeder_observation_id:
            observation = plan.get(db.FeederObservationRow, row.feeder_observation_id)
            if observation.snapshot_id != row.snapshot_id:
                raise AdminError("PROVENANCE_CONFLICT", "Evidence와 수집 기록의 수집본이 다릅니다.")
        sources[source.id], policies[policy.id] = source, policy
        evidence.append(item)
    return evidence, sources, policies


def _publication_gate(
    plan: Plan, claim: Claim, evidence_rows: list[Any], subject: Person | Organization | None = None
) -> None:
    if subject is None:
        model = db.PersonRow if claim.person_id else db.OrganizationRow
        row = plan.get(model, claim.person_id or claim.organization_id)
        if row.superseded_at is not None:
            raise AdminError("INACTIVE_SUBJECT", "비활성 대상의 Claim은 공개할 수 없습니다.")
        subject = (
            Person.model_validate(row, from_attributes=True)
            if claim.person_id
            else Organization.model_validate(row, from_attributes=True)
        )
    evidence, sources, policies = _evidence_context(plan, evidence_rows)
    if not evidence and claim.epistemic_status != EpistemicStatus.UNKNOWN:
        raise AdminError("EVIDENCE_REQUIRED", "근거가 없는 기록은 공개할 수 없습니다.")
    assert subject is not None
    gate = validate_claim_publication(claim, subject, evidence, sources, policies)
    if not gate.publishable:
        raise AdminError("PUBLICATION_BLOCKED", "공개 검증 실패: " + ", ".join(gate.failures))


def _review_row(plan: Plan, observation_id: str) -> Any | None:
    rows = plan.query(
        db.IdentityReviewItemRow, db.IdentityReviewItemRow.observation_id == observation_id
    )
    return max(rows, key=lambda row: (row.created_at, row.id)) if rows else None


def _save_review(
    plan: Plan, observation_id: str, state: str, disposition: str, person_id: str | None = None
) -> str:
    previous = _review_row(plan, observation_id)
    # Existing rows remain traceable; a decision is updated only with atomic audit history.
    if previous:
        plan.update(
            previous,
            status=state,
            reason_code="OPERATOR_REVIEW",
            resolution_note=plan.command.reason,
            candidate_person_id=person_id,
            details_json={
                "disposition": disposition,
                "operator_request_id": str(plan.command.request_id),
            },
            resolved_at=plan.review_time if state != "OPEN" else None,
        )
        return previous.id
    identifier = plan.uid(f"review:{observation_id}")
    plan.create(
        db.IdentityReviewItemRow,
        id=identifier,
        observation_id=observation_id,
        candidate_person_id=person_id,
        reason_code="OPERATOR_REVIEW",
        details_json={
            "disposition": disposition,
            "operator_request_id": str(plan.command.request_id),
        },
        status=state,
        created_at=plan.review_time,
        resolved_at=plan.review_time if state != "OPEN" else None,
        resolution_note=plan.command.reason,
    )
    return identifier


def _alio_person_record(plan: Plan, identifier: UUID) -> tuple[Any, dict[str, str], Any, Any]:
    from packages.persistence.repository import SqlAlchemyRepository

    row = plan.get(db.FeederObservationRow, identifier)
    snapshot_row = plan.get(db.SourceSnapshotRow, row.snapshot_id)
    source_row = plan.get(db.SourceRow, snapshot_row.source_id)
    policy_row = plan.get(db.SourcePolicyRow, source_row.policy_id)
    fields = validate_alio_item4_observation(
        SqlAlchemyRepository._observation(row),
        snapshot=SqlAlchemyRepository._snapshot(snapshot_row),
        source=SqlAlchemyRepository._source(source_row),
        policy=SqlAlchemyRepository._policy(policy_row),
    )
    if fields["name_status"] != "PUBLIC":
        raise AdminError(
            "NO_PUBLIC_PERSON", "가림·공석·비공개 행은 인물 등록 대상으로 사용할 수 없습니다."
        )
    checkpoints = plan.query(
        db.SourceCheckpointRow,
        db.SourceCheckpointRow.feeder == ALIO_EXECUTIVE_FEEDER,
        db.SourceCheckpointRow.scope_key == ALIO_EXECUTIVE_SCOPE,
        limit=1,
    )
    if not checkpoints or not checkpoints[0].last_run_id:
        raise AdminError("CHECKPOINT_REQUIRED", "성공한 수집 체크포인트가 필요합니다.")
    checkpoint = checkpoints[0]
    run = plan.get(db.SourceRunRow, checkpoint.last_run_id)
    metadata = checkpoint.metadata_json
    if (
        run.status != "SUCCESS"
        or run.feeder != row.feeder
        or run.scope_key != row.scope_key
        or run.checkpoint_after != checkpoint.cursor
        or metadata.get("source_contract") != ALIO_EXECUTIVE_SOURCE_CONTRACT
        or metadata.get("seen_provider_hashes", {}).get(row.provider_record_key) != row.content_hash
        or metadata.get("seen_current_disclosures", {}).get(fields["disclosure_no"])
        != fields["alio_apba_id"]
    ):
        raise AdminError(
            "SOURCE_VERSION_CONFLICT", "현재 성공한 수집 기준과 선택한 기록이 일치하지 않습니다."
        )
    versions = plan.query(
        db.FeederObservationRow,
        db.FeederObservationRow.feeder == row.feeder,
        db.FeederObservationRow.scope_key == row.scope_key,
        db.FeederObservationRow.provider_record_key == row.provider_record_key,
        limit=10,
    )
    if len({item.content_hash for item in versions}) != 1:
        raise AdminError(
            "SOURCE_VERSION_CONFLICT",
            "원본 기록에 복수 버전이 있습니다. 먼저 원본 버전을 검토하세요.",
        )
    evidence_rows = plan.query(
        db.ClaimEvidenceRow, db.ClaimEvidenceRow.feeder_observation_id == row.id
    )
    claims = [plan.get(db.ClaimRow, evidence.claim_id) for evidence in evidence_rows]
    exact = [
        claim
        for claim in claims
        if claim.predicate == ALIO_EXECUTIVE_PREDICATE
        and claim.organization_id
        and claim.publication_status == "PUBLISHED"
        and claim.superseded_at is None
        and claim.qualifiers.get("source_contract") == ALIO_EXECUTIVE_SOURCE_CONTRACT
    ]
    identities = {claim.organization_id for claim in exact}
    if len(identities) != 1:
        raise AdminError(
            "ORGANIZATION_BINDING_REQUIRED",
            "먼저 이 공시의 정확한 기관 연결을 검토·등록해야 합니다.",
        )
    organization = plan.get(db.OrganizationRow, next(iter(identities)))
    if organization.superseded_at or organization.name != fields["institution_name"]:
        raise AdminError("ORGANIZATION_CONFLICT", "공시의 기관명과 현재 canonical 기관이 다릅니다.")
    return row, fields, organization, source_row


def _bridge(plan: Plan, left: IdentityCandidate, target: Any, from_role: str) -> list[Any]:
    rows = [plan.get(db.ClaimEvidenceRow, identifier) for identifier in plan.command.evidence_ids]
    evidence, sources, policies = _evidence_context(plan, rows)
    aliases = plan.query(
        db.PersonAliasRow,
        db.PersonAliasRow.person_id == target.id,
        db.PersonAliasRow.superseded_at.is_(None),
    )
    bridge_items = []
    for item in evidence:
        source = sources[item.source_id]
        policy = policies[source.policy_id]
        # Human attests the actual cross-role continuity; existing resolver records that basis.
        # Merely selecting a same-name candidate, an embedding score, or a row key is insufficient.
        if (
            not policy.can_fetch
            or not policy.source_class.startswith("official_")
            or policy.collection_mode.value == "DISCOVERY_ONLY"
        ):
            raise AdminError(
                "OFFICIAL_BRIDGE_REQUIRED", "연결·병합 근거는 검토된 공식 출처여야 합니다."
            )
        bridge_items.append(
            CrossLaneIdentityEvidence(
                evidence_type=CrossLaneIdentityEvidenceType(plan.command.identity_basis or ""),
                source_ref=str(source.id),
                from_role=from_role,
                to_role=plan.command.reason,
            )
        )
    decision = resolve_cross_lane_identity(
        left,
        IdentityCandidate(
            canonical_name=target.canonical_name,
            birth_date=target.birth_date,
            aliases=tuple(alias.name for alias in aliases),
        ),
        tuple(bridge_items),
    )
    if decision.status != IdentityStatus.RESOLVED:
        raise AdminError(
            "IDENTITY_CONFLICT", "기존 identity 검증 실패: " + ", ".join(decision.reasons)
        )
    return rows


def _register_or_link(plan: Plan, identifier: UUID, created_names: set[str]) -> None:
    observation, fields, organization, source = _alio_person_record(plan, identifier)
    linked = plan.query(
        db.PersonObservationLinkRow,
        db.PersonObservationLinkRow.observation_id == observation.id,
        db.PersonObservationLinkRow.superseded_at.is_(None),
    )
    if linked:
        raise AdminError(
            "ALREADY_LINKED", "이 수집 기록은 이미 인물에 연결되었습니다. 중복 등록하지 않습니다."
        )
    name = fields["canonical_name"]
    if plan.command.action == AdminAction.REGISTER_PERSON:
        alias_rows = plan.query(
            db.PersonAliasRow,
            db.PersonAliasRow.name == name,
            db.PersonAliasRow.superseded_at.is_(None),
        )
        candidates = plan.query(
            db.PersonRow,
            or_(
                db.PersonRow.canonical_name == name,
                db.PersonRow.id.in_([alias.person_id for alias in alias_rows]),
            ),
            db.PersonRow.superseded_at.is_(None),
        )
        if candidates or name in created_names:
            raise AdminError(
                "IDENTITY_REVIEW_REQUIRED",
                f"동일 이름 후보가 존재합니다: {name}. 기존 연결 또는 별도 동일인 근거 검토가 필요합니다.",
            )
        created_names.add(name)
        person_id = plan.uid(f"person:{observation.id}")
        person = Person(
            id=UUID(person_id),
            canonical_name=name,
            identity_status=IdentityStatus.RESOLVED,
            **plan.time_fields(),
        )
        plan.create(db.PersonRow, **person.model_dump(mode="python", exclude={"id"}), id=person_id)
        action, decision = "REVIEWED_CREATE", "REVIEWED_SOURCE_CONTEXT"
        bridge_rows: list[Any] = []
    else:
        target = _current_person(plan, plan.command.target_person_id)
        if target.identity_status != "RESOLVED":
            raise AdminError("TARGET_NOT_RESOLVED", "연결 대상 인물이 아직 확인되지 않았습니다.")
        bridge_rows = _bridge(
            plan,
            IdentityCandidate(canonical_name=name),
            target,
            fields["institution_name"] + " / " + fields["position_text"],
        )
        person_id = target.id
        person = Person.model_validate(target, from_attributes=True)
        action, decision = "REVIEWED_LINK", "REVIEWED_BRIDGE"
    review_id = _save_review(plan, observation.id, "RESOLVED", "REGISTERED", person_id)
    plan.create(
        db.PersonObservationLinkRow,
        id=plan.uid(f"link:{observation.id}"),
        person_id=person_id,
        observation_id=observation.id,
        action=action,
        decision_class=decision,
        linked_at=plan.review_time,
        superseded_at=None,
        review_item_id=review_id,
    )
    claim_id = plan.uid(f"person-role:{observation.id}")
    claim = Claim(
        id=UUID(claim_id),
        person_id=UUID(person_id),
        subject=name,
        predicate=PERSON_ROLE_PREDICATE,
        proposition=f"{organization.name}의 ALIO 공시는 {name}을 {fields['position_text']}으로 기재한다.",
        object_text=f"{organization.name} · {fields['position_text']}",
        qualifiers={
            "organization_id": organization.id,
            "canonical_name": name,
            "position_text": fields["position_text"],
            "as_of": fields["as_of"],
            "source_contract": "alio_reviewed_person_role",
            "source_observation_id": observation.id,
            "immutable_observation_hash": observation.content_hash,
            "identity_review_id": review_id,
            "identity_scope": "OPERATOR_REVIEWED_SOURCE_CONTEXT",
        },
        epistemic_status=EpistemicStatus.CLAIM,
        publication_status=PublicationStatus.DRAFT,
        asserted_as_true=False,
        valid_from=observation.provider_observed_at or observation.recorded_at,
        recorded_at=plan.review_time,
    )
    claim_values = claim.model_dump(mode="python")
    claim_values.update(id=claim_id, person_id=person_id, organization_id=None)
    plan.create(db.ClaimRow, **claim_values)
    plan.create(
        db.ClaimEvidenceRow,
        id=plan.uid(f"role-evidence:{observation.id}"),
        claim_id=claim_id,
        source_id=source.id,
        snapshot_id=observation.snapshot_id,
        feeder_observation_id=observation.id,
        stance="SUPPORT",
        excerpt=None,
    )
    for item in bridge_rows:
        plan.create(
            db.ClaimEvidenceRow,
            id=plan.uid(f"bridge:{observation.id}:{item.id}"),
            claim_id=claim_id,
            source_id=item.source_id,
            snapshot_id=item.snapshot_id,
            feeder_observation_id=item.feeder_observation_id,
            stance="NEUTRAL",
            excerpt=None,
        )
    plan.outcomes.append(
        {
            "observation_id": observation.id,
            "person_id": person_id,
            "name": name,
            "disposition": "REGISTERED",
            "claim_id": claim_id,
            "publication_status": "DRAFT",
            "identity_action": action,
        }
    )


def _claim_action(plan: Plan, identifier: UUID) -> None:
    row = plan.get(db.ClaimRow, identifier)
    if row.superseded_at is not None:
        raise AdminError("SUPERSEDED_CLAIM", "이미 대체된 Claim은 수정·공개하지 않습니다.")
    evidence_rows = plan.query(db.ClaimEvidenceRow, db.ClaimEvidenceRow.claim_id == row.id)
    action = plan.command.action
    if action == AdminAction.CORRECT_CLAIM:
        # Draft correction does not remove a currently public record. Replacement occurs on publish.
        extra_rows = [plan.get(db.ClaimEvidenceRow, item) for item in plan.command.evidence_ids]
        _evidence_context(plan, extra_rows)
        correction_id = plan.uid(f"correction:{row.id}")
        correction = Claim(
            id=UUID(correction_id),
            person_id=UUID(row.person_id) if row.person_id else None,
            organization_id=UUID(row.organization_id) if row.organization_id else None,
            subject=row.subject,
            predicate=CORRECTION_PREDICATE,
            proposition=(plan.command.value or "").strip(),
            object_text=(plan.command.value or "").strip(),
            qualifiers={
                "replaces_claim_id": row.id,
                "original_predicate": row.predicate,
                "source_contract": "operator_reviewed_correction",
            },
            epistemic_status=EpistemicStatus.CLAIM,
            publication_status=PublicationStatus.DRAFT,
            asserted_as_true=False,
            valid_from=row.valid_from,
            valid_to=row.valid_to,
            recorded_at=plan.review_time,
        )
        values = correction.model_dump(mode="python")
        values.update(
            id=correction_id, person_id=row.person_id, organization_id=row.organization_id
        )
        plan.create(db.ClaimRow, **values)
        for item in extra_rows:
            plan.create(
                db.ClaimEvidenceRow,
                id=plan.uid(f"correction-evidence:{item.id}"),
                claim_id=correction_id,
                source_id=item.source_id,
                snapshot_id=item.snapshot_id,
                feeder_observation_id=item.feeder_observation_id,
                stance=item.stance,
                excerpt=None,
            )
        plan.outcomes.append(
            {
                "record_id": row.id,
                "correction_claim_id": correction_id,
                "publication_status": "DRAFT",
                "original_preserved": True,
            }
        )
        return
    new_status = {
        AdminAction.SUBMIT_REVIEW: "REVIEW",
        AdminAction.PUBLISH: "PUBLISHED",
        AdminAction.WITHDRAW: "WITHHELD",
    }[action]
    if row.publication_status == new_status:
        raise AdminError("NO_CHANGE", "이미 요청한 상태입니다.")
    if action == AdminAction.SUBMIT_REVIEW and row.publication_status not in {"DRAFT", "WITHHELD"}:
        raise AdminError("INVALID_TRANSITION", "초안 또는 비공개 상태만 검토 요청할 수 있습니다.")
    if action == AdminAction.PUBLISH:
        if row.publication_status not in {"REVIEW", "DRAFT", "WITHHELD"}:
            raise AdminError("INVALID_TRANSITION", "공개할 수 없는 상태입니다.")
        if row.predicate == PERSON_ROLE_PREDICATE:
            observation_id = row.qualifiers.get("source_observation_id", "")
            observation, fields, organization, _ = _alio_person_record(plan, UUID(observation_id))
            active = plan.query(
                db.PersonObservationLinkRow,
                db.PersonObservationLinkRow.observation_id == observation.id,
                db.PersonObservationLinkRow.person_id == row.person_id,
                db.PersonObservationLinkRow.superseded_at.is_(None),
            )
            if (
                len(active) != 1
                or row.qualifiers.get("organization_id") != organization.id
                or row.qualifiers.get("immutable_observation_hash") != observation.content_hash
                or row.object_text != f"{organization.name} · {fields['position_text']}"
            ):
                raise AdminError(
                    "ROLE_BINDING_CONFLICT", "인물·기관·수집 기록의 검토 연결이 일치하지 않습니다."
                )
        values = row_data(row)
        values["publication_status"] = "PUBLISHED"
        _publication_gate(plan, Claim.model_validate(values), evidence_rows)
        original_id = (
            row.qualifiers.get("replaces_claim_id")
            if row.predicate == CORRECTION_PREDICATE
            else None
        )
        if original_id:
            original = plan.get(db.ClaimRow, original_id)
            if original.superseded_at is not None or (
                original.person_id,
                original.organization_id,
            ) != (row.person_id, row.organization_id):
                raise AdminError("CORRECTION_CONFLICT", "정정 원본이 변경되었거나 대상이 다릅니다.")
            plan.update(original, publication_status="WITHHELD", superseded_at=plan.review_time)
    plan.update(row, publication_status=new_status)
    plan.outcomes.append(
        {
            "record_id": row.id,
            "before": row.publication_status,
            "after": new_status,
            "epistemic_status_unchanged": row.epistemic_status,
        }
    )


def _protect_indirect_dependencies(plan: Plan, person_id: str, claims: list[Any]) -> None:
    identifiers = [person_id, *(row.id for row in claims)]
    # Exact ID occurrence check is a conservative impact blocker, never an identity join.
    for model in (
        db.AssetDisclosureRow,
        db.EventRow,
        db.DecisionEpisodeRow,
        db.RelationshipRow,
        db.HypothesisRow,
        db.ProfileSnapshotRow,
    ):
        rows = plan.query(
            model,
            model.superseded_at.is_(None),
            or_(*(cast(model.payload, String).contains(item) for item in identifiers)),
            limit=1,
        )
        if rows:
            raise AdminError(
                "DEPENDENT_DOMAIN_REVIEW",
                "추가 도메인 기록이 연결되어 있습니다. 영향 검토 없이 병합·비활성화하지 않습니다.",
            )
    claim_ids = [row.id for row in claims]
    assets = plan.query(db.AssetItemRow, db.AssetItemRow.claim_id.in_(claim_ids), limit=1)
    evidence_ids = [
        row.id
        for claim in claims
        for row in plan.query(db.ClaimEvidenceRow, db.ClaimEvidenceRow.claim_id == claim.id)
    ]
    hypotheses = plan.query(
        db.HypothesisEvidenceRow,
        db.HypothesisEvidenceRow.claim_evidence_id.in_(evidence_ids),
        limit=1,
    )
    if assets or hypotheses:
        raise AdminError(
            "DEPENDENT_DOMAIN_REVIEW",
            "자산·가설 근거가 이 기록을 참조합니다. 해당 영향 검토가 먼저 필요합니다.",
        )


def _person_action(plan: Plan, identifier: UUID) -> None:
    person = _current_person(plan, identifier)
    action = plan.command.action
    if action == AdminAction.RENAME_PERSON:
        _evidence_context(
            plan, [plan.get(db.ClaimEvidenceRow, item) for item in plan.command.evidence_ids]
        )
        name = (plan.command.value or "").strip()
        if name == person.canonical_name:
            raise AdminError("NO_CHANGE", "현재 이름과 같습니다.")
        if plan.query(
            db.PersonRow,
            db.PersonRow.canonical_name == name,
            db.PersonRow.superseded_at.is_(None),
            db.PersonRow.id != person.id,
        ):
            raise AdminError(
                "NAME_CONFLICT",
                "동일 이름의 다른 인물이 있습니다. 이름 변경을 병합처럼 사용하지 마세요.",
            )
        plan.create(
            db.PersonAliasRow,
            id=plan.uid("previous-name"),
            person_id=person.id,
            name=person.canonical_name,
            **plan.time_fields(),
        )
        plan.update(person, canonical_name=name)
        plan.outcomes.append(
            {
                "person_id": person.id,
                "before_name": person.canonical_name,
                "after_name": name,
                "source_records_unchanged": True,
            }
        )
        return
    claims = plan.query(
        db.ClaimRow,
        db.ClaimRow.person_id == person.id,
        db.ClaimRow.superseded_at.is_(None),
        limit=200,
    )
    _protect_indirect_dependencies(plan, person.id, claims)
    links = plan.query(
        db.PersonObservationLinkRow,
        db.PersonObservationLinkRow.person_id == person.id,
        db.PersonObservationLinkRow.superseded_at.is_(None),
        limit=200,
    )
    appointments = plan.query(
        db.AppointmentRow,
        db.AppointmentRow.person_id == person.id,
        db.AppointmentRow.superseded_at.is_(None),
        limit=200,
    )
    if action == AdminAction.DEACTIVATE_PERSON:
        for row in claims:
            plan.update(row, publication_status="WITHHELD")
        for row in appointments:
            plan.update(row, superseded_at=plan.review_time)
        for row in links:
            plan.update(row, superseded_at=plan.review_time)
            _save_review(plan, row.observation_id, "REJECTED", "EXCLUDED", person.id)
        plan.update(person, superseded_at=plan.review_time)
        plan.outcomes.append(
            {
                "person_id": person.id,
                "deactivated": True,
                "claims_withheld": len(claims),
                "hard_delete": False,
            }
        )
        return
    target = _current_person(plan, plan.command.target_person_id)
    if target.id == person.id or target.identity_status != "RESOLVED":
        raise AdminError("MERGE_TARGET", "다른 현재 확인 인물을 병합 대상으로 선택하세요.")
    _bridge(
        plan,
        IdentityCandidate(canonical_name=person.canonical_name, birth_date=person.birth_date),
        target,
        person.canonical_name,
    )
    # Copy current evidence-bearing Claims to the survivor and preserve originals as superseded.
    for row in claims:
        new_id = plan.uid(f"merged-claim:{row.id}")
        values = row_data(row)
        values.update(
            id=new_id, person_id=target.id, recorded_at=plan.review_time, superseded_at=None
        )
        evidence_rows = plan.query(db.ClaimEvidenceRow, db.ClaimEvidenceRow.claim_id == row.id)
        copied_evidence = []
        for item in evidence_rows:
            copied = row_data(item)
            copied.update(id=plan.uid(f"merged-evidence:{item.id}"), claim_id=new_id)
            copied_evidence.append(copied)
        if row.publication_status == "PUBLISHED":
            # Gate the remapped packet with the same canonical policy/evidence semantics.
            gate_values = dict(values, publication_status="PUBLISHED")
            old_subject_values = dict(gate_values, id=row.id)
            _publication_gate(
                plan,
                Claim.model_validate(old_subject_values),
                evidence_rows,
                Person.model_validate(target, from_attributes=True),
            )
        plan.create(db.ClaimRow, **values)
        for item in copied_evidence:
            plan.create(db.ClaimEvidenceRow, **item)
        plan.update(row, superseded_at=plan.review_time)
    for row in links:
        existing = plan.query(
            db.PersonObservationLinkRow,
            db.PersonObservationLinkRow.person_id == target.id,
            db.PersonObservationLinkRow.observation_id == row.observation_id,
            db.PersonObservationLinkRow.superseded_at.is_(None),
        )
        if not existing:
            plan.create(
                db.PersonObservationLinkRow,
                id=plan.uid(f"merged-link:{row.id}"),
                person_id=target.id,
                observation_id=row.observation_id,
                action="REVIEWED_LINK",
                decision_class="REVIEWED_MERGE",
                linked_at=plan.review_time,
                superseded_at=None,
                review_item_id=row.review_item_id,
            )
        plan.update(row, superseded_at=plan.review_time)
    aliases = plan.query(
        db.PersonAliasRow,
        db.PersonAliasRow.person_id == person.id,
        db.PersonAliasRow.superseded_at.is_(None),
    )
    for row in aliases:
        values = row_data(row)
        values.update(
            id=plan.uid(f"merged-alias:{row.id}"),
            person_id=target.id,
            recorded_at=plan.review_time,
            superseded_at=None,
        )
        plan.create(db.PersonAliasRow, **values)
        plan.update(row, superseded_at=plan.review_time)
    for row in appointments:
        values = row_data(row)
        values.update(
            id=plan.uid(f"merged-appointment:{row.id}"),
            person_id=target.id,
            recorded_at=plan.review_time,
            superseded_at=None,
        )
        plan.create(db.AppointmentRow, **values)
        plan.update(row, superseded_at=plan.review_time)
    plan.update(person, superseded_at=plan.review_time)
    plan.outcomes.append(
        {
            "source_person_id": person.id,
            "surviving_person_id": target.id,
            "copied_claims": len(claims),
            "source_retained": True,
            "hard_delete": False,
        }
    )


def build_plan(session: Session, command: AdminCommand, *, locking: bool = False) -> Plan:
    plan = Plan(session, command, locking)
    created_names: set[str] = set()
    for identifier in sorted(command.record_ids, key=str):
        if command.action in {AdminAction.HOLD, AdminAction.EXCLUDE, AdminAction.REOPEN}:
            row = plan.get(db.FeederObservationRow, identifier)
            if (
                row.feeder != ALIO_EXECUTIVE_FEEDER
                or row.normalized_json.get("name_status") != "PUBLIC"
            ):
                raise AdminError(
                    "UNSUPPORTED_REVIEW", "현재 인물 검토 큐는 공개된 ALIO 인물 기록을 지원합니다."
                )
            if plan.query(
                db.PersonObservationLinkRow,
                db.PersonObservationLinkRow.observation_id == row.id,
                db.PersonObservationLinkRow.superseded_at.is_(None),
            ):
                raise AdminError(
                    "ALREADY_REGISTERED", "이미 등록된 기록은 인물 관리에서 처리하세요."
                )
            state = "REJECTED" if command.action == AdminAction.EXCLUDE else "OPEN"
            disposition = {
                AdminAction.HOLD: "HELD",
                AdminAction.EXCLUDE: "EXCLUDED",
                AdminAction.REOPEN: "UNREVIEWED",
            }[command.action]
            _save_review(plan, row.id, state, disposition)
            plan.outcomes.append({"observation_id": row.id, "disposition": disposition})
        elif command.action in {AdminAction.REGISTER_PERSON, AdminAction.LINK_PERSON}:
            _register_or_link(plan, identifier, created_names)
        elif command.action in {
            AdminAction.SUBMIT_REVIEW,
            AdminAction.PUBLISH,
            AdminAction.WITHDRAW,
            AdminAction.CORRECT_CLAIM,
        }:
            _claim_action(plan, identifier)
        else:
            _person_action(plan, identifier)
    if not plan.changes:
        raise AdminError("NO_CHANGE", "변경할 항목이 없습니다.")
    return plan


def commit_command(
    session: Session, command: AdminCommand, actor: str, expected_state: str
) -> dict[str, Any]:
    if not admin_schema_ready(session):
        raise AdminError(
            "ADMIN_MIGRATION_REQUIRED", "어드민 변경 이력 migration 0007 적용이 필요합니다."
        )
    if session.get_bind().dialect.name == "postgresql":
        session.execute(text("SELECT pg_advisory_xact_lock(187465321)"))
        if command.action in {
            AdminAction.REGISTER_PERSON,
            AdminAction.LINK_PERSON,
            AdminAction.MERGE_PERSON,
            AdminAction.RENAME_PERSON,
            AdminAction.DEACTIVATE_PERSON,
        }:
            session.execute(text("LOCK TABLE people IN SHARE ROW EXCLUSIVE MODE"))
    existing = session.get(db.AdminOperationRow, str(command.request_id))
    command_hash = digest(command.model_dump(mode="json"))
    if existing:
        if existing.actor != actor or existing.command_hash != command_hash:
            raise AdminError(
                "IDEMPOTENCY_CONFLICT", "같은 요청 ID에 다른 작업이 이미 기록되었습니다."
            )
        return {**receipt(existing), "replayed": True, "write_performed": False}
    plan = build_plan(session, command, locking=True)
    if plan.state_hash() != expected_state:
        raise AdminError("STALE_PREVIEW", "미리보기 이후 데이터가 바뀌었습니다. 다시 검토하세요.")
    plan.apply()
    result = {
        "outcomes": plan.outcomes,
        "changed_rows": len(plan.changes),
        "write_performed": True,
        "review_evidence_ids": [str(item) for item in command.evidence_ids],
        "identity_basis": command.identity_basis,
        "human_verified": command.human_verified,
    }
    entry = db.AdminOperationRow(
        id=str(command.request_id),
        actor=actor,
        action=command.action.value,
        created_at=plan.review_time,
        command_hash=command_hash,
        state_hash=expected_state,
        reason=command.reason,
        targets=[str(item) for item in command.record_ids],
        changes=[change.visible() for change in plan.changes.values()],
        result=result,
    )
    session.add(entry)
    session.flush()
    return {**receipt(entry), "replayed": False, "write_performed": True}

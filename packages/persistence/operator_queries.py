from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import func, or_, select, union
from sqlalchemy.orm import Session

from packages.domain import db

# A fixed read model over existing canonical rows, not a second repository.
MODELS: dict[str, Any] = {
    "organizations": db.OrganizationRow,
    "people": db.PersonRow,
    "claims": db.ClaimRow,
    "observations": db.FeederObservationRow,
    "sources": db.SourceRow,
    "runs": db.SourceRunRow,
    "evidence": db.ClaimEvidenceRow,
    "snapshots": db.SourceSnapshotRow,
    "reviews": db.IdentityReviewItemRow,
    "policies": db.SourcePolicyRow,
    "links": db.PersonObservationLinkRow,
    "checkpoints": db.SourceCheckpointRow,
}
TEMPORAL = ("valid_from", "valid_to", "recorded_at", "superseded_at")
FIELDS: dict[str, tuple[str, ...]] = {
    "organizations": ("name", *TEMPORAL),
    "people": ("canonical_name", "identity_status", *TEMPORAL),
    "claims": (
        "subject",
        "predicate",
        "object_text",
        "proposition",
        "person_id",
        "organization_id",
        "epistemic_status",
        "publication_status",
        "asserted_as_true",
        *TEMPORAL,
    ),
    "observations": (
        "feeder",
        "scope_key",
        "provider_record_key",
        "snapshot_id",
        "run_id",
        "recorded_at",
        "provider_observed_at",
        "semantic_scope",
        "content_hash",
    ),
    "sources": ("title", "publisher", "url", "policy_id", "published_at"),
    "runs": (
        "feeder",
        "scope_key",
        "status",
        "started_at",
        "finished_at",
        "records_seen",
        "observations_created",
        "observations_unchanged",
    ),
    "evidence": ("claim_id", "source_id", "snapshot_id", "feeder_observation_id", "stance"),
    "snapshots": ("source_id", "fetched_at", "content_hash"),
    "reviews": (
        "observation_id",
        "candidate_person_id",
        "reason_code",
        "status",
        "created_at",
        "resolved_at",
    ),
    "policies": (
        "domain",
        "source_class",
        "collection_mode",
        "can_fetch",
        "can_store_metadata",
        "can_store_fulltext",
        "can_send_to_ai",
        "can_show_excerpt",
        "can_commercialize",
        "license",
        "robots_checked_at",
        "terms_checked_at",
    ),
    "links": (
        "person_id",
        "observation_id",
        "action",
        "decision_class",
        "linked_at",
        "superseded_at",
        "review_item_id",
    ),
    "checkpoints": ("feeder", "scope_key", "updated_at", "last_run_id"),
}
OBSERVATION_FIELDS = (
    "canonical_name",
    "organization_name",
    "institution_name",
    "name",
    "title",
    "notice_title",
    "bill_name",
    "position_text",
    "role_title",
    "committee_name",
    "audit_date",
    "audited_targets",
    "institution_code",
    "term_start",
    "term_end",
    "fiscal_year",
    "business_year",
    "record_type",
    "classification_text",
    "amount_krw",
)
SEARCH_FIELDS: dict[str, tuple[str, ...]] = {
    "organizations": ("name",),
    "people": ("canonical_name",),
    "claims": ("subject", "predicate", "object_text"),
    "observations": ("provider_record_key", "feeder", "semantic_scope"),
    "sources": ("title", "publisher"),
    "runs": ("feeder", "scope_key"),
    "reviews": ("reason_code",),
    "policies": ("domain", "source_class"),
    "links": ("action", "decision_class"),
    "checkpoints": ("feeder", "scope_key"),
}
# field -> (referenced kind, explicit edge description). Never join on a label.
REFS: dict[str, dict[str, tuple[str, str]]] = {
    "claims": {
        "person_id": ("people", "기록 대상"),
        "organization_id": ("organizations", "기록 대상"),
    },
    "evidence": {
        "claim_id": ("claims", "근거 대상 / stance 별도"),
        "source_id": ("sources", "근거 출처"),
        "snapshot_id": ("snapshots", "근거 수집본"),
        "feeder_observation_id": ("observations", "정규화 근거"),
    },
    "snapshots": {"source_id": ("sources", "수집 출처")},
    "sources": {"policy_id": ("policies", "출처 권한")},
    "observations": {"snapshot_id": ("snapshots", "수집본"), "run_id": ("runs", "수집 실행")},
    "reviews": {
        "observation_id": ("observations", "검토 대상"),
        "candidate_person_id": ("people", "후보 / 동일인 미확정"),
    },
    "links": {
        "person_id": ("people", "저장된 인물 연결"),
        "observation_id": ("observations", "연결된 기록"),
        "review_item_id": ("reviews", "검토 이력"),
    },
    "checkpoints": {"last_run_id": ("runs", "체크포인트 실행")},
}
URL_KEYS = frozenset(
    (
        "pageindex",
        "orgcode",
        "chartid",
        "codenum",
        "disclosureno",
        "apbaid",
        "nttid",
        "filesn",
        "atchfileid",
        "menuno",
        "bill_id",
        "age",
        "rcept_no",
        "rcpno",
        "seq",
        "id",
    )
)


def safe_url(value: str) -> str | None:
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in {"https", "http"} or not parsed.hostname or parsed.username:
            return None
        query = [(k, v) for k, v in parse_qsl(parsed.query) if k.lower() in URL_KEYS]
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), ""))
    except ValueError:
        return None


def _value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, str):
        return value[:4000]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, list):
        return [item[:300] for item in value[:50] if isinstance(item, str)]
    return None  # Nested provider objects are not an operator DTO.


def _columns(kind: str) -> list[Any]:
    model = MODELS[kind]
    columns = [model.id, *(getattr(model, name) for name in FIELDS[kind])]
    if kind == "observations":
        columns += [
            model.normalized_json[key].label(f"normalized_{key}") for key in OBSERVATION_FIELDS
        ]
    return columns


def _record(kind: str, row: Any) -> dict[str, Any]:
    fields = {name: _value(row[name]) for name in FIELDS[kind]}
    if kind == "sources":
        fields["url"] = safe_url(str(row["url"]))
    if kind == "observations":
        fields.update(
            {
                key: _value(row[f"normalized_{key}"])
                for key in OBSERVATION_FIELDS
                if row[f"normalized_{key}"] is not None
            }
        )
    names = (
        "name",
        "canonical_name",
        "institution_name",
        "organization_name",
        "title",
        "notice_title",
        "bill_name",
        "subject",
        "domain",
        "reason_code",
        "feeder",
    )
    label = next(
        (fields[key] for key in names if isinstance(fields.get(key), str) and fields[key].strip()),
        str(row["id"]),
    )
    state = (
        fields.get("publication_status") or fields.get("identity_status") or fields.get("status")
    )
    if state is None:
        state = (
            ("SUPERSEDED" if fields.get("superseded_at") else "CURRENT")
            if "superseded_at" in fields
            else "STORED"
        )
    # A version of the allowlisted read view, not a hash asserting the whole DB is frozen.
    version = hashlib.sha256(json.dumps(
        {"kind": kind, "id": str(row["id"]), "fields": fields},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()
    return {
        "version": version,
        "kind": kind,
        "id": str(row["id"]),
        "label": str(label)[:250],
        "status": state,
        "fields": fields,
    }


def records(
    session: Session,
    kind: str,
    *,
    q: str = "",
    feeder: str = "",
    scope: str = "",
    status: str = "",
    offset: int = 0,
    limit: int = 25,
) -> dict[str, Any]:
    if kind not in MODELS or not 1 <= limit <= 100 or not 0 <= offset <= 100000:
        raise ValueError("Unsupported record kind or page bounds")
    if len(q) > 200 or len(feeder) > 100 or len(scope) > 300 or len(status) > 32:
        raise ValueError("Filter is too long")
    model = MODELS[kind]
    predicates: list[Any] = []
    if q.strip():
        pattern = (
            "%" + q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        )
        searchable = [model.id, *(getattr(model, name) for name in SEARCH_FIELDS.get(kind, ()))]
        if kind == "observations":
            searchable += [model.normalized_json[key].as_string() for key in OBSERVATION_FIELDS[:9]]
        predicates.append(or_(*(column.ilike(pattern, escape="\\") for column in searchable)))
    for name, value in (("feeder", feeder), ("scope_key", scope)):
        if value:
            if name not in FIELDS[kind]:
                raise ValueError("This filter is not supported for the selected kind")
            predicates.append(getattr(model, name) == value)
    if status:
        state_field = next(
            (
                name
                for name in ("publication_status", "identity_status", "status")
                if name in FIELDS[kind]
            ),
            None,
        )
        if status in {"CURRENT", "SUPERSEDED"} and "superseded_at" in FIELDS[kind]:
            predicates.append(
                model.superseded_at.is_(None)
                if status == "CURRENT"
                else model.superseded_at.is_not(None)
            )
        elif state_field:
            predicates.append(getattr(model, state_field) == status)
        else:
            raise ValueError("Status filter is not supported for the selected kind")
    total = session.scalar(select(func.count()).select_from(model).where(*predicates)) or 0
    order = next(
        (
            getattr(model, field)
            for field in ("name", "canonical_name", "started_at", "recorded_at")
            if field in FIELDS[kind]
        ),
        model.id,
    )
    rows = session.execute(
        select(*_columns(kind))
        .where(*predicates)
        .order_by(order, model.id)
        .offset(offset)
        .limit(limit)
    ).mappings()
    return {
        "kind": kind,
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": [_record(kind, row) for row in rows],
        "write_performed": False,
    }


def summary(session: Session) -> dict[str, Any]:
    def count(model: Any, *conditions: Any) -> Any:
        return select(func.count()).select_from(model).where(*conditions).scalar_subquery()

    keys = (
        select(
            db.FeederObservationRow.feeder,
            db.FeederObservationRow.scope_key,
            db.FeederObservationRow.provider_record_key,
        )
        .distinct()
        .subquery()
    )
    counts = dict(
        session.execute(
            select(
                *(count(model).label(kind) for kind, model in MODELS.items()),
                count(db.PersonRow, db.PersonRow.superseded_at.is_(None)).label("current_people"),
                count(db.OrganizationRow, db.OrganizationRow.superseded_at.is_(None)).label(
                    "current_organizations"
                ),
                count(db.ClaimRow, db.ClaimRow.superseded_at.is_(None)).label("current_claims"),
                count(
                    db.ClaimRow,
                    db.ClaimRow.superseded_at.is_(None),
                    db.ClaimRow.publication_status == "PUBLISHED",
                ).label("published_claims"),
                count(keys).label("observation_keys"),
                count(db.IdentityReviewItemRow, db.IdentityReviewItemRow.status == "OPEN").label(
                    "open_reviews"
                ),
            )
        )
        .mappings()
        .one()
    )
    obs = db.FeederObservationRow
    run = db.SourceRunRow
    checkpoint = db.SourceCheckpointRow
    lane_keys = union(
        select(obs.feeder, obs.scope_key),
        select(run.feeder, run.scope_key),
        select(checkpoint.feeder, checkpoint.scope_key),
    ).subquery()
    observations = (
        select(
            obs.feeder,
            obs.scope_key,
            func.count().label("versions"),
            func.count(func.distinct(obs.provider_record_key)).label("provider_keys"),
        )
        .group_by(obs.feeder, obs.scope_key)
        .subquery()
    )

    def run_window(success_only: bool = False) -> Any:
        query = select(
            run.id,
            run.feeder,
            run.scope_key,
            run.status,
            run.started_at,
            run.finished_at,
            run.records_seen,
            run.observations_created,
            run.observations_unchanged,
            func.row_number()
            .over(
                partition_by=(run.feeder, run.scope_key),
                order_by=(run.started_at.desc(), run.id.desc()),
            )
            .label("rank"),
        )
        if success_only:
            query = query.where(run.status == "SUCCESS")
        return query.subquery()

    latest = run_window()
    successful = run_window(True)

    def matches(table: Any) -> Any:
        return (table.c.feeder == lane_keys.c.feeder) & (table.c.scope_key == lane_keys.c.scope_key)

    query = (
        select(
            lane_keys.c.feeder,
            lane_keys.c.scope_key,
            func.coalesce(observations.c.versions, 0).label("observation_versions"),
            func.coalesce(observations.c.provider_keys, 0).label("provider_keys"),
            latest.c.id.label("latest_run_id"),
            latest.c.status.label("latest_run_status"),
            latest.c.started_at.label("latest_run_started_at"),
            latest.c.finished_at.label("latest_run_finished_at"),
            latest.c.records_seen,
            latest.c.observations_created,
            latest.c.observations_unchanged,
            successful.c.finished_at.label("last_success_at"),
            checkpoint.updated_at.label("checkpoint_updated_at"),
        )
        .select_from(lane_keys)
        .outerjoin(observations, matches(observations))
        .outerjoin(latest, matches(latest) & (latest.c.rank == 1))
        .outerjoin(successful, matches(successful) & (successful.c.rank == 1))
        .outerjoin(
            checkpoint,
            (checkpoint.feeder == lane_keys.c.feeder)
            & (checkpoint.scope_key == lane_keys.c.scope_key),
        )
        .order_by(lane_keys.c.feeder, lane_keys.c.scope_key)
        .limit(501)
    )
    lanes = [
        {key: _value(value) for key, value in row.items()}
        for row in session.execute(query).mappings()
    ]
    return {
        "counts": counts,
        "lanes": lanes[:500],
        "lanes_truncated": len(lanes) > 500,
        "write_performed": False,
        "semantics": "STORED_DB_COUNTS_NOT_COVERAGE_OR_FACT_VERDICTS",
    }


def detail(session: Session, kind: str, record_id: str) -> dict[str, Any] | None:
    if kind not in MODELS:
        raise ValueError("Unsupported record kind")
    model = MODELS[kind]
    row = (
        session.execute(select(*_columns(kind)).where(model.id == record_id))
        .mappings()
        .one_or_none()
    )
    if row is None:
        return None
    selected = _record(kind, row)
    node_map = {f"{kind}:{record_id}": selected}
    frontier = [selected]
    truncated = False
    max_nodes, per_query = 80, 12
    for depth in range(3):
        grouped: dict[str, set[str]] = {}
        for node in frontier:
            grouped.setdefault(node["kind"], set()).add(node["id"])
        outgoing: dict[str, set[str]] = {}
        for node in frontier:
            for field, (target, _) in REFS.get(node["kind"], {}).items():
                value = node["fields"].get(field)
                if value:
                    outgoing.setdefault(target, set()).add(value)
        additions: list[dict[str, Any]] = []
        for target_kind, target_model in MODELS.items():
            conditions = []
            if outgoing.get(target_kind):
                conditions.append(target_model.id.in_(outgoing[target_kind]))
            for field, (parent, _) in REFS.get(target_kind, {}).items():
                # Expand inbound references at the selected root and Claim evidence only.
                # Shared Source/Run hubs are context, not permission to pull unrelated siblings.
                if grouped.get(parent) and (depth == 0 or parent == "claims"):
                    conditions.append(getattr(target_model, field).in_(grouped[parent]))
            if not conditions:
                continue
            known = [node["id"] for node in node_map.values() if node["kind"] == target_kind]
            query = (
                select(*_columns(target_kind))
                .where(or_(*conditions), target_model.id.not_in(known))
                .order_by(target_model.id)
                .limit(per_query + 1)
            )
            found = list(session.execute(query).mappings())
            truncated |= len(found) > per_query
            for candidate in found[:per_query]:
                key = f"{target_kind}:{candidate['id']}"
                if key in node_map:
                    continue
                if len(node_map) >= max_nodes:
                    truncated = True
                    break
                item = _record(target_kind, candidate)
                node_map[key] = item
                additions.append(item)
        frontier = additions
        if not frontier:
            break
    edges = []
    for key, node in node_map.items():
        for field, (target, label) in REFS.get(node["kind"], {}).items():
            target_id = f"{target}:{node['fields'].get(field)}"
            if target_id in node_map:
                if node["kind"] == "evidence" and field == "claim_id":
                    label = str(node["fields"]["stance"])
                edges.append(
                    {
                        "id": f"{key}:{field}",
                        "source": key,
                        "target": target_id,
                        "label": label,
                        "review_only": node["kind"] == "reviews",
                    }
                )
    return {
        "record": selected,
        "graph": {
            "center": f"{kind}:{record_id}",
            "nodes": [
                {**node, "record_id": node["id"], "id": key} for key, node in node_map.items()
            ],
            "edges": edges,
            "truncated": truncated,
            "max_nodes": max_nodes,
            "max_depth": 3,
            "semantics": "EXACT_STORED_REFERENCE_LINEAGE_NOT_INFERRED_SOCIAL_RELATIONSHIPS",
        },
    }

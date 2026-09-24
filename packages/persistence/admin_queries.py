"""Observation-backed workload, separate from canonical Person and stored OPEN counts."""

from __future__ import annotations

from typing import Any

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from packages.domain import db
from packages.persistence.operator_queries import _columns, _record
from packages.rendering.alio_organization_content import (
    ALIO_EXECUTIVE_FEEDER,
    ALIO_EXECUTIVE_SCOPE,
    ALIO_EXECUTIVE_SEMANTIC_SCOPE,
)


def _queue_base():
    observation = db.FeederObservationRow
    review = db.IdentityReviewItemRow
    link = db.PersonObservationLinkRow
    person = db.PersonRow
    reviews = select(
        review.observation_id,
        review.status,
        review.details_json["disposition"].as_string().label("disposition"),
        func.row_number()
        .over(
            partition_by=review.observation_id,
            order_by=(review.created_at.desc(), review.id.desc()),
        )
        .label("rn"),
    ).subquery()
    links = (
        select(
            link.observation_id,
            func.min(link.person_id).label("person_id"),
            func.min(link.action).label("link_action"),
            func.min(link.decision_class).label("link_decision_class"),
            func.count().label("link_count"),
        )
        .where(link.superseded_at.is_(None))
        .group_by(link.observation_id)
        .subquery()
    )
    state = case(
        (links.c.link_count > 1, "CONFLICT"),
        (
            and_(
                links.c.person_id.is_not(None),
                links.c.link_decision_class == "DETERMINISTIC_SOURCE_CONTEXT",
                person.identity_status != "RESOLVED",
            ),
            "SOURCE_CONTEXT_REVIEW",
        ),
        (links.c.person_id.is_not(None), "REGISTERED"),
        (reviews.c.disposition == "HELD", "HELD"),
        (reviews.c.status == "REJECTED", "EXCLUDED"),
        else_="UNREVIEWED",
    ).label("disposition")
    name = observation.normalized_json["canonical_name"].as_string()
    candidates = (
        select(func.count())
        .select_from(db.PersonRow)
        .where(
            db.PersonRow.superseded_at.is_(None),
            or_(
                db.PersonRow.canonical_name == name,
                select(db.PersonAliasRow.id)
                .where(
                    db.PersonAliasRow.person_id == db.PersonRow.id,
                    db.PersonAliasRow.name == name,
                    db.PersonAliasRow.superseded_at.is_(None),
                )
                .correlate(db.PersonRow, observation)
                .exists(),
            ),
        )
        .correlate(observation)
        .scalar_subquery()
        .label("candidate_count")
    )
    query = (
        select(observation.id, name.label("name"),
            observation.normalized_json["institution_name"].as_string().label("institution"),
            observation.normalized_json["position_text"].as_string().label("position"),
            state,
            links.c.person_id,
            links.c.link_action,
            links.c.link_decision_class,
            candidates,
        )
        .outerjoin(reviews, (reviews.c.observation_id == observation.id) & (reviews.c.rn == 1))
        .outerjoin(links, links.c.observation_id == observation.id)
        .outerjoin(person, person.id == links.c.person_id)
        .where(
            observation.feeder == ALIO_EXECUTIVE_FEEDER,
            observation.scope_key == ALIO_EXECUTIVE_SCOPE,
            observation.semantic_scope == ALIO_EXECUTIVE_SEMANTIC_SCOPE,
            observation.normalized_json["name_status"].as_string() == "PUBLIC",
        )
    )
    return query.subquery()


def person_review_queue(
    session: Session, *, q: str = "", state: str = "UNREVIEWED", offset: int = 0, limit: int = 25
) -> dict[str, Any]:
    if state not in {
        "ALL",
        "UNREVIEWED",
        "HELD",
        "EXCLUDED",
        "REGISTERED",
        "SOURCE_CONTEXT_REVIEW",
        "CONFLICT",
        "HAS_CANDIDATE",
    }:
        raise ValueError("Unsupported work-queue state")
    base = _queue_base()
    total_counts: dict[str, int] = {
        str(row[0]): int(row[1])
        for row in session.execute(
            select(base.c.disposition, func.count()).group_by(base.c.disposition)
        ).all()
    }
    filters = []
    if state == "HAS_CANDIDATE":
        filters += [base.c.candidate_count > 0, base.c.disposition == "UNREVIEWED"]
    elif state != "ALL":
        filters.append(base.c.disposition == state)
    if q.strip():
        pattern = (
            "%" + q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        )
        filters.append(or_(*(column.ilike(pattern, escape="\\") for column in
                             (base.c.name, base.c.institution, base.c.position))))
    count = session.scalar(select(func.count()).select_from(base).where(*filters)) or 0
    page = list(
        session.execute(
            select(base)
            .where(*filters)
            .order_by(base.c.name, base.c.id)
            .offset(offset)
            .limit(limit)
        ).mappings()
    )
    ids = [row["id"] for row in page]
    observed = {
        row["id"]: _record("observations", row)
        for row in session.execute(
            select(*_columns("observations")).where(db.FeederObservationRow.id.in_(ids))
        ).mappings()
    }
    names = {row["name"] for row in page}
    alias_pairs = list(
        session.execute(
            select(db.PersonAliasRow.name, db.PersonAliasRow.person_id).where(
                db.PersonAliasRow.name.in_(names), db.PersonAliasRow.superseded_at.is_(None)
            )
        ).all()
    )
    alias_ids = [pair[1] for pair in alias_pairs]
    people = session.execute(
        select(db.PersonRow.id, db.PersonRow.canonical_name, db.PersonRow.identity_status)
        .where(
            db.PersonRow.superseded_at.is_(None),
            or_(db.PersonRow.canonical_name.in_(names), db.PersonRow.id.in_(alias_ids)),
        )
        .order_by(db.PersonRow.canonical_name, db.PersonRow.id)
    ).mappings()
    by_name: dict[str, list[dict]] = {}
    for person in people:
        by_name.setdefault(person["canonical_name"], []).append(dict(person))
        for alias_name, person_id in alias_pairs:
            if person_id == person["id"] and alias_name != person["canonical_name"]:
                by_name.setdefault(alias_name, []).append(dict(person))
    items = []
    for row in page:
        item = observed[row["id"]]
        items.append(
            {
                **item,
                "disposition": row["disposition"],
                "linked_person_id": row["person_id"],
                "link_action": row["link_action"],
                "link_decision_class": row["link_decision_class"],
                "candidate_count": row["candidate_count"],
                "candidates": by_name.get(row["name"], [])[:10],
            }
        )
    return {
        "total": count,
        "offset": offset,
        "limit": limit,
        "items": items,
        "counts": {
            state: total_counts.get(state, 0)
            for state in (
                "UNREVIEWED",
                "HELD",
                "EXCLUDED",
                "SOURCE_CONTEXT_REVIEW",
                "REGISTERED",
                "CONFLICT",
            )
        },
        "named_record_total": sum(total_counts.values()),
        "distinct_names": session.scalar(select(func.count(func.distinct(base.c.name)))) or 0,
        "semantics": "NAMED_SOURCE_RECORDS_NOT_DEDUPLICATED_PEOPLE",
        "candidate_rule": "EXACT_NAME_OR_STORED_ALIAS_DISCOVERY_ONLY_NOT_IDENTITY_AUTHORITY",
    }


def evidence_options(session: Session, q: str = "", limit: int = 10) -> list[dict[str, Any]]:
    from sqlalchemy import or_

    from packages.persistence.operator_queries import safe_url

    evidence, claim, source = db.ClaimEvidenceRow, db.ClaimRow, db.SourceRow
    query = (
        select(
            evidence.id, evidence.stance, claim.subject, claim.proposition, source.title, source.url
        )
        .select_from(evidence)
        .join(claim, evidence.claim_id == claim.id)
        .join(source, evidence.source_id == source.id)
        .where(claim.superseded_at.is_(None))
    )
    if q.strip():
        pattern = (
            "%" + q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        )
        query = query.where(
            or_(
                *(
                    field.ilike(pattern, escape="\\")
                    for field in (evidence.id, claim.subject, claim.object_text, source.title)
                )
            )
        )
    return [
        {
            "id": row.id,
            "label": row.subject,
            "proposition": row.proposition[:500],
            "source_title": row.title,
            "url": safe_url(row.url),
            "stance": row.stance,
        }
        for row in session.execute(query.order_by(evidence.id).limit(limit)).all()
    ]

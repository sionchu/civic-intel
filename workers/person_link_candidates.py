"""Read-only review packet: which no-Person-ID source rows could be linked to which Person.

Gukgam witness rows and OpenDART executive-status rows have no provider Person ID. This report
never links, creates, merges, scores or publishes. Exact name overlap only nominates a pair; a
pair becomes a review candidate only with a second deterministic anchor (witness: the row states
an institution of the Person's own role record; OpenDART: disclosed birth year/month agrees with
a known birth date, or the company appears in the Person's source-reported career). Every
candidate still needs the admin LINK_PERSON transaction with explicit human review.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Iterable
from typing import Any

from sqlalchemy import select

from packages.domain import db
from packages.domain.admin import PERSON_ROLE_PREDICATE
from packages.persistence import DatabaseNotReady, SqlAlchemyRepository
from packages.rendering.alio_organization_content import ALIO_EXECUTIVE_FEEDER
from packages.rendering.gukgam_witness_claim import GUKGAM_WITNESS_PREDICATE
from packages.verification.gukgam_witness_import import GUKGAM_WITNESS_FEEDER
from packages.verification.person_record_links import (
    NO_PROVIDER_PERSON_ID,
    OPENDART_EXECUTIVE_FEEDER,
    birth_year_month,
    birth_year_month_conflict,
    listed_name,
    witness_institution_anchors,
)

REPORT_SEMANTICS = "REVIEW_CANDIDATES_NOT_IDENTITY_DECISIONS"


def _person_index(session: Any) -> tuple[dict[str, Any], dict[str, set[str]]]:
    people = {
        row.id: row
        for row in session.scalars(select(db.PersonRow).where(db.PersonRow.superseded_at.is_(None)))
    }
    by_name: dict[str, set[str]] = defaultdict(set)
    for row in people.values():
        by_name[row.canonical_name].add(row.id)
    aliases = session.scalars(
        select(db.PersonAliasRow).where(db.PersonAliasRow.superseded_at.is_(None))
    )
    for alias in aliases:
        if alias.person_id in people:
            by_name[alias.name].add(alias.person_id)
    return people, by_name


def _role_records(session: Any) -> dict[str, list[dict[str, Any]]]:
    """Current ALIO-backed Person role records that a witness row may be compared with."""

    organizations = {row.id: row.name for row in session.scalars(select(db.OrganizationRow))}
    claims = list(
        session.scalars(
            select(db.ClaimRow).where(
                db.ClaimRow.predicate == PERSON_ROLE_PREDICATE,
                db.ClaimRow.person_id.is_not(None),
                db.ClaimRow.superseded_at.is_(None),
            )
        )
    )
    evidence: dict[str, list[str]] = defaultdict(list)
    for row in session.scalars(
        select(db.ClaimEvidenceRow).where(
            db.ClaimEvidenceRow.claim_id.in_([claim.id for claim in claims])
        )
    ):
        evidence[row.claim_id].append(row.id)
    records: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for claim in claims:
        records[claim.person_id].append(
            {
                "claim_id": claim.id,
                "predicate": claim.predicate,
                "organization": organizations.get(claim.qualifiers.get("organization_id", "")),
                "position_text": claim.qualifiers.get("position_text"),
                "as_of": claim.qualifiers.get("as_of"),
                "publication_status": claim.publication_status,
                "bridge_evidence_ids": sorted(evidence[claim.id]),
            }
        )
    return records


def _reported_careers(session: Any) -> dict[str, str]:
    """ALIO source-reported career text per linked Person (discovery context only)."""

    rows = session.execute(
        select(db.PersonObservationLinkRow.person_id, db.FeederObservationRow.normalized_json)
        .join(
            db.FeederObservationRow,
            db.FeederObservationRow.id == db.PersonObservationLinkRow.observation_id,
        )
        .where(
            db.PersonObservationLinkRow.superseded_at.is_(None),
            db.FeederObservationRow.feeder == ALIO_EXECUTIVE_FEEDER,
        )
    )
    careers: dict[str, list[str]] = defaultdict(list)
    for person_id, normalized in rows:
        careers[person_id].extend(str(item) for item in normalized.get("reported_careers") or [])
    return {person_id: " / ".join(items) for person_id, items in careers.items()}


def _linked_observation_ids(session: Any) -> set[str]:
    return set(
        session.scalars(
            select(db.PersonObservationLinkRow.observation_id).where(
                db.PersonObservationLinkRow.superseded_at.is_(None)
            )
        )
    )


def _person_view(row: Any) -> dict[str, Any]:
    return {
        "id": row.id,
        "name": row.canonical_name,
        "identity_status": row.identity_status,
        "birth_date_known": row.birth_date is not None,
    }


def _people_with_claims(session: Any) -> set[str]:
    """People holding at least one current evidence-backed Claim a reviewer can cite as bridge."""

    return set(
        session.scalars(
            select(db.ClaimRow.person_id)
            .join(db.ClaimEvidenceRow, db.ClaimEvidenceRow.claim_id == db.ClaimRow.id)
            .where(db.ClaimRow.person_id.is_not(None), db.ClaimRow.superseded_at.is_(None))
            .distinct()
        )
    )


def _blocked(person: Any, context: dict[str, Any], collisions: int) -> list[str]:
    reasons = []
    if person.identity_status != "RESOLVED":
        reasons.append("PERSON_NOT_RESOLVED_RESOLVE_PERSON_FIRST")
    if person.id not in context["bridgeable"]:
        reasons.append("NO_OFFICIAL_BRIDGE_RECORD_ON_PERSON")
    if collisions > 1:
        reasons.append("SAME_NAME_MULTIPLE_ANCHORED_PEOPLE")
    return reasons


def _witness_candidates(session: Any, context: dict[str, Any]) -> tuple[list[dict], Counter]:
    people, by_name, records, linked = (
        context["people"],
        context["by_name"],
        context["records"],
        context["linked"],
    )
    witness_claims: dict[str, Any] = {}
    claim_rows = session.execute(
        select(db.ClaimEvidenceRow.feeder_observation_id, db.ClaimRow)
        .join(db.ClaimRow, db.ClaimRow.id == db.ClaimEvidenceRow.claim_id)
        .where(
            db.ClaimRow.predicate == GUKGAM_WITNESS_PREDICATE,
            db.ClaimRow.superseded_at.is_(None),
            db.ClaimRow.publication_status == "PUBLISHED",
        )
    )
    for observation_id, claim in claim_rows:
        witness_claims[observation_id] = claim
    tally: Counter = Counter()
    candidates = []
    rows = session.scalars(
        select(db.FeederObservationRow).where(db.FeederObservationRow.feeder == GUKGAM_WITNESS_FEEDER)
    )
    for row in rows:
        tally["rows"] += 1
        normalized = row.normalized_json
        claim = witness_claims.get(row.id)
        if row.id in linked:
            tally["already_linked"] += 1
            continue
        if claim is None or claim.qualifiers.get("immutable_observation_hash") != row.content_hash:
            tally["no_current_published_list_claim"] += 1
            continue
        name = listed_name(str(normalized.get("name") or ""))
        matches = sorted(by_name.get(name, ()))
        if not matches:
            tally["no_exact_name_person"] += 1
            continue
        anchored = []
        for person_id in matches:
            person_records = records.get(person_id, [])
            anchors = witness_institution_anchors(
                normalized, [item["organization"] for item in person_records if item["organization"]]
            )
            if anchors:
                anchored.append((person_id, anchors, person_records))
        if not anchored:
            tally["exact_name_only_not_a_candidate"] += 1
            continue
        for person_id, anchors, person_records in anchored:
            person = people[person_id]
            blocked = _blocked(person, context, len(anchored))
            tally["candidates"] += 1
            tally["link_ready" if not blocked else "blocked"] += 1
            for reason in blocked:
                tally[f"blocked:{reason}"] += 1
            candidates.append(
                {
                    "lane": "GUKGAM_WITNESS",
                    "source_record": {
                        "observation_id": row.id,
                        "witness_claim_id": claim.id,
                        "listed_name": normalized.get("name"),
                        "affiliation_title": normalized.get("affiliation_title"),
                        "target_institution": normalized.get("target_institution"),
                        "committee_name": normalized.get("committee_name"),
                        "category": normalized.get("category"),
                        "list_section": normalized.get("list_section"),
                        "list_version": normalized.get("list_version"),
                        "attendance_date_text": normalized.get("attendance_date_text"),
                        "source_tag": claim.qualifiers.get("source_tag"),
                        "acquisition_channel": normalized.get("acquisition_channel"),
                        "locator": normalized.get("locator"),
                    },
                    "candidate_person": _person_view(person),
                    "person_records": person_records,
                    "anchors": ["EXACT_LISTED_NAME", *(f"INSTITUTION:{a}" for a in anchors)],
                    "conflicts": [],
                    "blocked_reasons": blocked,
                    "automatic_resolution": NO_PROVIDER_PERSON_ID,
                }
            )
    return candidates, tally


def _opendart_candidates(session: Any, context: dict[str, Any]) -> tuple[list[dict], Counter]:
    people, by_name, records, linked, careers = (
        context["people"],
        context["by_name"],
        context["records"],
        context["linked"],
        context["careers"],
    )
    tally: Counter = Counter()
    candidates = []
    rows = session.execute(
        select(
            db.FeederObservationRow.id,
            db.FeederObservationRow.normalized_json,
        ).where(db.FeederObservationRow.feeder == OPENDART_EXECUTIVE_FEEDER)
    )
    for observation_id, normalized in rows:
        tally["rows"] += 1
        if observation_id in linked:
            tally["already_linked"] += 1
            continue
        name = str(normalized.get("canonical_name") or "").strip()
        matches = sorted(by_name.get(name, ()))
        if not matches:
            tally["no_exact_name_person"] += 1
            continue
        disclosed = normalized.get("birth_year_month")
        corp_name = str(normalized.get("corp_name") or "")
        anchored = []
        for person_id in matches:
            person = people[person_id]
            if birth_year_month_conflict(person.birth_date, disclosed):
                tally["birth_year_month_conflict_refused"] += 1
                continue
            anchors = []
            if person.birth_date is not None and birth_year_month(disclosed) is not None:
                anchors.append("BIRTH_YEAR_MONTH_AGREES")
            if len(corp_name) >= 2 and corp_name in careers.get(person_id, ""):
                anchors.append("COMPANY_IN_SOURCE_REPORTED_CAREER")
            if anchors:
                anchored.append((person_id, anchors))
            else:
                tally["exact_name_only_not_a_candidate"] += 1
        for person_id, anchors in anchored:
            person = people[person_id]
            person_records = records.get(person_id, [])
            blocked = _blocked(person, context, len(anchored))
            tally["candidates"] += 1
            tally["link_ready" if not blocked else "blocked"] += 1
            for reason in blocked:
                tally[f"blocked:{reason}"] += 1
            candidates.append(
                {
                    "lane": "OPENDART_EXECUTIVE",
                    "source_record": {
                        "observation_id": observation_id,
                        "listed_name": name,
                        "birth_year_month": disclosed,
                        **{
                            key: normalized.get(key)
                            for key in (
                                "corp_name",
                                "corp_code",
                                "receipt_no",
                                "business_year",
                                "report_code",
                                "position",
                                "registered_status",
                                "full_time_status",
                                "responsibility",
                                "tenure_text",
                                "settlement_date",
                            )
                        },
                    },
                    "candidate_person": _person_view(person),
                    "person_records": person_records,
                    "anchors": ["EXACT_NAME", *anchors],
                    "conflicts": [],
                    "blocked_reasons": blocked,
                    "automatic_resolution": NO_PROVIDER_PERSON_ID,
                }
            )
    return candidates, tally


def build_person_link_candidate_report(
    repository: SqlAlchemyRepository, *, lanes: Iterable[str] = ("witness", "opendart")
) -> dict[str, Any]:
    repository.assert_ready()
    with repository.sessions() as session:
        people, by_name = _person_index(session)
        context = {
            "people": people,
            "by_name": by_name,
            "records": _role_records(session),
            "linked": _linked_observation_ids(session),
            "careers": _reported_careers(session),
            "bridgeable": _people_with_claims(session),
        }
        candidates: list[dict[str, Any]] = []
        summary: dict[str, dict[str, int]] = {}
        selected = set(lanes)
        if "witness" in selected:
            found, tally = _witness_candidates(session, context)
            candidates.extend(found)
            summary["gukgam_witness"] = dict(sorted(tally.items()))
        if "opendart" in selected:
            found, tally = _opendart_candidates(session, context)
            candidates.extend(found)
            summary["opendart_executive"] = dict(sorted(tally.items()))
    candidates.sort(
        key=lambda item: (
            item["lane"],
            item["candidate_person"]["name"],
            item["source_record"]["observation_id"],
            item["candidate_person"]["id"],
        )
    )
    body = {
        "semantics": REPORT_SEMANTICS,
        "write_performed": False,
        "automatic_resolution": NO_PROVIDER_PERSON_ID,
        "people_considered": len(people),
        "summary": summary,
        "candidates": candidates,
    }
    encoded = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return body | {"report_sha256": hashlib.sha256(encoded.encode()).hexdigest()}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read-only review candidates for witness/OpenDART rows and existing People."
    )
    parser.add_argument("--database-url")
    parser.add_argument("--lane", action="append", choices=("witness", "opendart"))
    parser.add_argument(
        "--summary-only", action="store_true", help="Print counts without candidate rows."
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    repository = SqlAlchemyRepository(args.database_url)
    try:
        report = build_person_link_candidate_report(
            repository, lanes=args.lane or ("witness", "opendart")
        )
    except (DatabaseNotReady, ValueError) as exc:
        parser.error(str(exc))
    if args.summary_only:
        report = {key: value for key, value in report.items() if key != "candidates"}
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

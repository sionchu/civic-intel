"""Offline source-to-source discovery; no identity, schedule selection or publication."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from collections.abc import Sequence
from urllib.parse import parse_qs, urlparse

from packages.connectors.gukgam_reviewed_packet import (
    ReviewedGukgamPlanPacket,
    parse_reviewed_gukgam_plan_packet,
)
from packages.connectors.gukgam_witness_packet import (
    GukgamWitnessPacket,
    canonical_hash,
    parse_gukgam_witness_packet,
)
from packages.rendering.gukgam_organization_binding_review import gukgam_review_key
from packages.verification.gukgam_reviewed_plan_import import reviewed_gukgam_plan_policy

NO_CONTEXT = "NO_PRINTED_CONTEXT_LABEL"
NO_EXACT = "NO_EXACT_PLAN_LABEL_OVERLAP"
ONE_EXACT = "EXACT_PLAN_LABEL_OVERLAP_DISCOVERY_ONLY"
MULTIPLE_EXACT = "MULTIPLE_PLAN_OCCURRENCES_REVIEW_REQUIRED"


class GukgamWitnessPlanReviewError(ValueError):
    pass


def _validate_plan_source(packet: ReviewedGukgamPlanPacket) -> str:
    source = packet.source
    url = urlparse(source.detail_url)
    query = parse_qs(url.query, keep_blank_values=True)
    if (
        url.scheme != "https" or not (url.hostname or "").endswith(".na.go.kr")
        or url.netloc != url.hostname or url.username is not None or url.password is not None
        or url.fragment or url.path != "/cmmit/bbs/BCMT2002/view.do"
        or set(query) - {"nttId", "menuNo", "pageIndex", "hrCmtId", "pageUnit", "pdCndCd"}
        or any(len(values) != 1 for values in query.values())
        or query.get("nttId") != [source.ntt_id]
        or not re.fullmatch(r"[0-9]+", source.ntt_id)
        or not re.fullmatch(r"[A-Za-z0-9_-]+", source.atch_file_id)
        or source.rights_mark != "KOGL_TYPE_1" or not packet.schedule
    ):
        raise GukgamWitnessPlanReviewError("plan review requires exact permitted source metadata")
    policy = reviewed_gukgam_plan_policy(url.hostname or "")
    if not policy.can_store_metadata:
        raise GukgamWitnessPlanReviewError("plan metadata processing is not permitted")
    return f"{source.ntt_id}:{source.atch_file_id}:{source.file_sn}"


def build_gukgam_witness_plan_review(
    witnesses: Sequence[GukgamWitnessPacket], plans: Sequence[ReviewedGukgamPlanPacket],
) -> dict:
    # Revalidate at this boundary, including callers constructing dataclasses directly.
    checked_witnesses = [parse_gukgam_witness_packet(item.normalized()) for item in witnesses]
    checked_plans = [parse_reviewed_gukgam_plan_packet(item.normalized()) for item in plans]
    if not checked_witnesses or not checked_plans:
        raise GukgamWitnessPlanReviewError("witness and plan packets are required")
    if len({item.source_key for item in checked_witnesses}) != len(checked_witnesses):
        raise GukgamWitnessPlanReviewError("duplicate witness attachment series requires review")
    for witness in checked_witnesses:
        policy = reviewed_gukgam_plan_policy(urlparse(witness.source.detail_url).hostname or "")
        if witness.source.rights_mark not in (
            "KOGL_TYPE_1", "KOGL_TYPE_1_VISIBLE_ON_EXACT_PARENT_POST",
        ) or not policy.can_store_metadata:
            raise GukgamWitnessPlanReviewError("witness metadata processing is not permitted")
    plan_keys = [_validate_plan_source(item) for item in checked_plans]
    if len(set(plan_keys)) != len(plan_keys):
        raise GukgamWitnessPlanReviewError("duplicate plan attachment series requires review")
    checked_witnesses.sort(key=lambda item: item.source_key)
    checked_plans.sort(key=lambda item: (
        item.source.ntt_id, item.source.atch_file_id, item.source.file_sn,
    ))
    candidates: dict[tuple[str, int, str], list[dict]] = defaultdict(list)
    plan_sources: list[dict] = []
    for plan in checked_plans:
        source = plan.source
        source_key = f"{source.ntt_id}:{source.atch_file_id}:{source.file_sn}"
        plan_sources.append({
            "source_key": source_key, "packet_hash": plan.content_hash,
            "source": source.normalized(), "artifact_bytes_verified": False,
            "attachment_sha256": None, "version_state": "NOT_CURRENT_VERIFIED",
        })
        for plan_row in plan.schedule:
            # Publication scope and printed audit year must both agree with the witness scope.
            if plan_row.audit_date.year != source.published_date.year:
                continue
            record_key = plan.schedule_record_key(plan_row)
            for index, plan_label in enumerate(plan_row.audited_targets, 1):
                candidates[(source.committee_name, source.published_date.year, plan_label.strip())].append({
                    "plan_source_key": source_key, "plan_packet_hash": plan.content_hash,
                    "plan_record_key": record_key, "review_key": gukgam_review_key(record_key, index),
                    "target_index": index, "printed_audited_target": plan_label,
                    "printed_audit_date": plan_row.audit_date.isoformat(),
                    "printed_time_text": plan_row.time_text, "printed_venue": plan_row.venue,
                    "printed_section": plan_row.section, "page_number": plan_row.page_number,
                })
    items: list[dict] = []
    witness_sources: list[dict] = []
    for packet in checked_witnesses:
        source = packet.source
        witness_sources.append({
            "source_key": packet.source_key, "packet_hash": packet.content_hash,
            "source": source.normalized(), "attachment_sha256": packet.attachment_sha256,
            "review_status": packet.review_status, "selection": packet.selection,
        })
        for row in sorted(packet.rows, key=lambda item: item.record_key):
            heading = row.category == "INSTITUTION_WITNESS"
            label = row.printed_institution_group if heading else row.printed_audited_target
            matches = candidates.get(
                (source.committee_name, source.published_date.year, (label or "").strip()), [],
            ) if label is not None else []
            match_class = NO_CONTEXT if label is None else (
                NO_EXACT if not matches else ONE_EXACT if len(matches) == 1 else MULTIPLE_EXACT
            )
            references = [candidate | {"occurrence_ref_hash": canonical_hash({
                "witness_packet_hash": packet.content_hash,
                "witness_attachment_sha256": packet.attachment_sha256,
                "witness_record_key": row.record_key,
                "plan_packet_hash": candidate["plan_packet_hash"],
                "plan_review_key": candidate["review_key"],
            })} for candidate in matches]
            items.append({
                "witness_source_key": packet.source_key, "witness_packet_hash": packet.content_hash,
                "witness_row_hash": canonical_hash(row.model_dump()),
                "witness_row": row.model_dump(), "context_label": label,
                "context_kind": "INSTITUTION_LIST_HEADING" if heading else "PRINTED_AUDITED_TARGET",
                "match_class": match_class, "plan_candidates": references,
                "identity_state": "SOURCE_SCOPED_IDENTITY_REVIEW_REQUIRED",
                "attendance_state": "NOT_VERIFIED",
            })
    return {
        "semantics": "REVIEW_ONLY_WITNESS_PLAN_LABEL_OVERLAP",
        "match_rule": "EXACT_TRIMMED_LABEL_SAME_EXPLICIT_COMMITTEE_AND_YEAR",
        "row_count": len(items),
        "category_counts": dict(sorted(Counter(item["witness_row"]["category"] for item in items).items())),
        "match_class_counts": dict(sorted(Counter(item["match_class"] for item in items).items())),
        "witness_sources": witness_sources, "plan_sources": plan_sources, "items": items,
        "canonical_identity_binding": False, "claim_publication": False,
        "selected_plan_occurrences": 0, "unique_person_count": None,
        "latest_amendment_completeness": "NOT_ESTABLISHED",
        "limitations": [
            "All exact label occurrences are candidates; no occurrence or date is selected.",
            "Institution headings are list context, not employment or canonical audited targets.",
            "Employer/role text is never parsed into an audited target or identity candidate.",
            "Witness fields and requested dates stay literal; plan dates do not fill missing fields.",
            "Input review markers do not attest to a new human review, identity or publication.",
            "Plan packet hashes are verified representations; raw plan bytes are not checked here.",
            "Different attachment posts coexist; supersession and current editions require review.",
        ],
    }

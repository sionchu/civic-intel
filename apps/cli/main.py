"""Explicit-effect operator command boundary (no legacy worker-main dispatch)."""

from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import asdict, is_dataclass
from datetime import date
from enum import StrEnum
from pathlib import Path
from uuid import UUID


class CommandEffect(StrEnum):
    READ_ONLY = "READ_ONLY"
    SOURCE_INGESTION = "SOURCE_INGESTION"
    IDENTITY_MATERIALIZATION = "IDENTITY_MATERIALIZATION"
    CLAIM_PUBLICATION = "CLAIM_PUBLICATION"
    SCHEMA_OR_DEPLOY = "SCHEMA_OR_DEPLOY"


ROUTES = {
    "observe": (
        CommandEffect.SOURCE_INGESTION,
        (
            "assembly",
            "legislative",
            "nec-candidates",
            "nec-winners",
            "gwanbo",
            "policy-research",
            "dart",
            "dart-executives",
            "mois-organizations",
            "mois-organization-lookup",
            "alio-item4",
            "alio-item12",
            "gukgam-plan",
            "gukgam-witness",
            "gukgam-schedule-probe",
            "assembly-page",
            "legislative-person",
            "nec-page",
        ),
    ),
    "materialize": (
        CommandEffect.IDENTITY_MATERIALIZATION,
        (
            "assembly",
            "alio-safe-people",
            "nec-safe-people",
            "orggo-organizations",
        ),
    ),
    "publish": (
        CommandEffect.CLAIM_PUBLICATION,
        (
            "assembly-profile",
            "claim",
            "alio-item4",
            "legislative",
            "alio-item12",
            "gukgam-claim",
            "gukgam-batch",
        ),
    ),
    "review": (CommandEffect.CLAIM_PUBLICATION, ("assembly-distinct-person",)),
    "inspect": (
        CommandEffect.READ_ONLY,
        (
            "commands",
            "collection-status",
            "gukgam-witness-claim",
            "alio-item4",
            "gukgam-plan",
            "gukgam-witness",
            "alio-safe-people",
            "nec-safe-people",
            "orggo-organizations",
            "alio-item12",
            "gukgam-claim",
            "gukgam-batch",
        ),
    ),
}


def sha256(value: str) -> str:
    normalized = value.strip().casefold()
    if not re.fullmatch(r"[0-9a-f]{64}", normalized):
        raise argparse.ArgumentTypeError("expected SHA-256 must contain 64 hex characters")
    return normalized


def election_types(value: str) -> tuple[int, ...]:
    try:
        result = tuple(int(item) for item in value.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("election types must be comma-separated integers") from exc
    if (
        not result
        or len(set(result)) != len(result)
        or any(x not in (3, 4, 5, 6, 11) for x in result)
    ):
        raise argparse.ArgumentTypeError("select unique NEC types from 3,4,5,6,11")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="civic", description="Explicit-effect Civic Intel operations"
    )
    verbs = parser.add_subparsers(dest="verb", required=True)
    for verb, (effect, lanes) in ROUTES.items():
        group = verbs.add_parser(verb).add_subparsers(dest="lane", required=True)
        for lane in lanes:
            p = group.add_parser(lane, help=effect.value)
            p.set_defaults(effect=effect)
            p.add_argument("--allow-effect", choices=[x.value for x in CommandEffect])
            if lane == "commands":
                continue
            if lane == "collection-status":
                p.add_argument("--database-url", required=True)
                p.add_argument("--running-age-minutes", type=int, default=60)
                continue
            if lane not in (
                "policy-research",
                "assembly-page",
                "legislative-person",
                "nec-page",
                "dart",
                "gukgam-schedule-probe",
            ):
                p.add_argument("--database-url", required=lane == "gukgam-witness-claim")
            if lane == "gukgam-witness-claim":
                p.add_argument("--person-id", type=UUID, required=True)
                p.add_argument("--observation-id", type=UUID, required=True)
                p.add_argument("--expected-observation-hash", type=sha256, required=True)
                p.add_argument("--expected-packet-hash", type=sha256, required=True)
            if lane == "claim":
                p.add_argument("--claim-id", type=UUID, required=True)
            if lane == "gukgam-plan":
                p.add_argument("--packet", type=Path, required=True)
                p.add_argument("--artifact", type=Path, required=True)
                p.add_argument("--attachment-url", required=True)
                p.add_argument(
                    "--confirm-exact-attachment-rights", action="store_true", required=True
                )
            if lane == "gukgam-witness":
                if verb == "inspect":
                    inputs = p.add_mutually_exclusive_group(required=True)
                    inputs.add_argument("--research", type=Path)
                    inputs.add_argument("--packet", type=Path)
                    p.add_argument("--artifact", type=Path)
                    p.add_argument("--plan-packet", type=Path, action="append", default=[])
                    draft = p.add_mutually_exclusive_group()
                    draft.add_argument("--write-draft-edits", type=Path)
                    draft.add_argument("--draft-edits", type=Path)
                    p.add_argument("--draft-packet", type=Path)
                else:
                    p.add_argument("--packet", type=Path, required=True)
                    p.add_argument("--artifact", type=Path, required=True)
                    p.add_argument(
                        "--confirm-exact-attachment-rights", action="store_true", required=True
                    )
            if verb == "observe":
                if lane == "assembly":
                    p.add_argument("--max-requests", type=int)
                    p.add_argument("--min-request-interval", type=float)
                    p.add_argument("--fetch-deadline-seconds", type=float)
                if lane not in (
                    "gukgam-witness",
                    "mois-organization-lookup",
                    "policy-research",
                    "assembly-page",
                    "legislative-person",
                    "nec-page",
                    "dart",
                    "gukgam-schedule-probe",
                ):
                    p.add_argument("--resume", action="store_true")
                if lane == "mois-organization-lookup":
                    filters = p.add_mutually_exclusive_group(required=True)
                    filters.add_argument("--full-name")
                    filters.add_argument("--org-code")
                    p.add_argument("--expected-full-name", required=True)
                    p.add_argument("--page-size", type=int, default=100)
                if lane in (
                    "assembly",
                    "assembly-page",
                    "legislative",
                    "legislative-person",
                    "nec-candidates",
                    "nec-winners",
                    "nec-page",
                    "gwanbo",
                    "mois-organizations",
                    "gukgam-schedule-probe",
                ):
                    p.add_argument(
                        "--page-size",
                        type=int,
                        default=10
                        if lane in ("gwanbo", "gukgam-schedule-probe")
                        else 1000
                        if lane in ("legislative", "legislative-person", "mois-organizations")
                        else 100,
                    )
                if lane in ("legislative", "legislative-person", "mois-organizations"):
                    p.add_argument(
                        "--max-pages",
                        type=int,
                        default=500 if lane == "mois-organizations" else 100,
                    )
                if lane == "assembly-page":
                    p.add_argument("--page-index", type=int, default=1)
                    for flag in ("name", "party", "district"):
                        p.add_argument("--" + flag)
                if lane == "gukgam-schedule-probe":
                    p.add_argument("--date", type=date.fromisoformat, required=True)
                    p.add_argument("--committee", required=True)
                if lane in ("legislative", "legislative-person"):
                    p.add_argument("--age", type=int, required=True)
                    if lane == "legislative-person":
                        p.add_argument("--name", required=True)
                        p.add_argument("--member-code", required=True)
                if lane.startswith("nec-"):
                    p.add_argument("--election-id", required=True)
                    p.add_argument("--type", type=int, choices=(3, 4, 5, 6, 11), required=True)
                    p.add_argument("--page-no", type=int, default=1)
                    if lane == "nec-page":
                        for flag in ("province", "district", "party"):
                            p.add_argument("--" + flag)
                if lane == "gwanbo":
                    p.add_argument("--from-date", type=date.fromisoformat, required=True)
                    p.add_argument("--to-date", type=date.fromisoformat, required=True)
                if lane == "policy-research":
                    for flag in ("title", "publisher", "publisher-code"):
                        p.add_argument("--" + flag)
                    for flag in ("year-begin", "year-end"):
                        p.add_argument("--" + flag, type=int)
                    p.add_argument("--page-no", type=int, default=1)
                    p.add_argument("--row-count", type=int, default=30)
                if lane.startswith("dart"):
                    p.add_argument("--business-year", type=int, required=lane == "dart-executives")
                    p.add_argument("--report-code", required=lane == "dart-executives")
                    if lane == "dart-executives":
                        p.add_argument("--listed-only", action="store_true")
                    else:
                        p.add_argument(
                            "--dataset",
                            required=True,
                            choices=(
                                "EXECUTIVE_STATUS",
                                "DIRECTOR_COMPENSATION_V2",
                                "TOP_COMPENSATION_V2",
                                "OFFICER_MAJOR_HOLDER_OWNERSHIP",
                            ),
                        )
                        p.add_argument("--corp-code", required=True)
                if lane == "alio-item12":
                    p.add_argument("--institution-code", action="append", dest="institution_codes")
            else:
                if lane in ("alio-safe-people", "nec-safe-people") and verb == "materialize":
                    p.add_argument("--expected-receipt-sha256", required=True, type=sha256)
                if lane == "nec-safe-people":
                    p.add_argument("--election-id", default="20260603")
                    p.add_argument("--types", type=election_types, default=(3, 4, 5, 6, 11))
                if lane in ("orggo-organizations", "gukgam-batch"):
                    p.add_argument("--manifest", type=Path, required=True)
                    if verb != "inspect":
                        p.add_argument("--expected-manifest-sha256", type=sha256, required=True)
                    if lane == "orggo-organizations":
                        p.add_argument("--proposal", type=Path, required=True)
                if lane in ("alio-item12", "gukgam-claim"):
                    p.add_argument("--organization-id", type=UUID, required=True)
                    if lane == "gukgam-claim":
                        p.add_argument("--review-key", required=True)
                    else:
                        p.add_argument("--institution-code", required=True)
                        p.add_argument("--earlier-fiscal-year", type=int, required=True)
                        p.add_argument("--later-fiscal-year", type=int, required=True)
                if lane == "assembly-distinct-person":
                    p.add_argument("--review-item-id", type=UUID, required=True)
                    p.add_argument("--resolution-note", required=True)
    return parser


def parse_command(argv: list[str] | None = None) -> argparse.Namespace:
    parser = build_parser()
    args = parser.parse_args(argv)
    permitted = args.allow_effect or CommandEffect.READ_ONLY.value
    if permitted != args.effect.value:
        parser.error(
            f"command effect is {args.effect.value}; specify --allow-effect {args.effect.value}"
        )
    if getattr(args, "resolution_note", None) is not None and not args.resolution_note.strip():
        parser.error("resolution note must not be blank")
    for flag in ("page_size", "page_no", "page_index", "max_pages", "row_count"):
        if getattr(args, flag, 1) < 1:
            parser.error(f"{flag.replace('_', '-')} must be positive")
    if args.verb == "observe" and args.lane == "assembly":
        limits = (args.max_requests, args.min_request_interval, args.fetch_deadline_seconds)
        if any(value is not None for value in limits):
            if any(value is None for value in limits):
                parser.error("Assembly request-count, interval and fetch deadline are required together")
            if args.max_requests < 1:
                parser.error("max-requests must be positive")
            if not math.isfinite(args.min_request_interval) or args.min_request_interval < 0:
                parser.error("min-request-interval must be finite and nonnegative")
            if not math.isfinite(args.fetch_deadline_seconds) or args.fetch_deadline_seconds <= 0:
                parser.error("fetch-deadline-seconds must be finite and positive")
    if args.lane == "gukgam-witness" and args.verb == "inspect":
        if args.packet and not args.artifact:
            parser.error("witness packet inspection requires its exact local artifact")
        if args.research and args.artifact:
            parser.error("research inspection does not accept an artifact for multiple sources")
        if bool(args.draft_edits) != bool(args.draft_packet):
            parser.error("draft-edits and draft-packet are required together")
        if (args.write_draft_edits or args.draft_edits) and (
            not args.packet or args.plan_packet
        ):
            parser.error("draft preparation requires a single packet without plan inputs")
    if args.lane == "mois-organization-lookup":
        if args.page_size > 100 or not args.expected_full_name.strip():
            parser.error("MOIS lookup requires an expected full name and at most 100 rows")
        if args.full_name is not None and (
            not args.full_name.strip() or args.full_name != args.expected_full_name
        ):
            parser.error("MOIS name filter must equal the expected full name")
        if args.org_code is not None and not re.fullmatch(r"[0-9A-Z]{7}", args.org_code):
            parser.error("MOIS org-code requires seven uppercase alphanumeric characters")
    if args.lane == "collection-status" and not 1 <= args.running_age_minutes <= 10080:
        parser.error("running-age-minutes must be 1 to 10080")
    if args.lane == "gwanbo" and args.from_date > args.to_date:
        parser.error("from-date must precede to-date")
    if args.lane == "gukgam-schedule-probe" and (
        not args.committee.strip() or args.page_size > 100
    ):
        parser.error("schedule probe requires a committee and page-size from 1 to 100")
    return args


def _json_default(value: object) -> object:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    if isinstance(value, (UUID, date, StrEnum)):
        return str(value)
    raise TypeError(f"unsupported receipt type: {type(value).__name__}")


def main(argv: list[str] | None = None) -> int:
    args = parse_command(argv)
    from apps.cli.adapters import dispatch

    try:
        result = dispatch(args)
        print(
            json.dumps(
                {
                    "effect": args.effect.value,
                    "command": f"{args.verb} {args.lane}",
                    "result": result,
                },
                ensure_ascii=False,
                sort_keys=True,
                default=_json_default,
            )
        )
    except Exception as exc:  # noqa: BLE001 - redact all operational connection/request errors.
        print(
            json.dumps(
                {
                    "effect": args.effect.value,
                    "command": f"{args.verb} {args.lane}",
                    "status": "UNAVAILABLE" if args.lane == "collection-status" else "FAILED",
                    "error_code": "COLLECTION_STATUS_UNAVAILABLE"
                    if args.lane == "collection-status" else "COMMAND_FAILED",
                },
                sort_keys=True,
            )
        )
        if isinstance(exc, ValueError):
            raise SystemExit(2) from None
        return 1
    return 0

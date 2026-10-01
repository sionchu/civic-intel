"""Explicit-effect operator command boundary (no legacy worker-main dispatch)."""

from __future__ import annotations

import argparse
import json
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
            "alio-item4",
            "alio-item12",
            "gukgam-plan",
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
            "alio-item4",
            "gukgam-plan",
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
            if lane not in (
                "policy-research",
                "assembly-page",
                "legislative-person",
                "nec-page",
                "dart",
            ):
                p.add_argument("--database-url")
            if lane == "claim":
                p.add_argument("--claim-id", type=UUID, required=True)
            if lane == "gukgam-plan":
                p.add_argument("--packet", type=Path, required=True)
                p.add_argument("--artifact", type=Path, required=True)
                p.add_argument("--attachment-url", required=True)
                p.add_argument(
                    "--confirm-exact-attachment-rights", action="store_true", required=True
                )
            if verb == "observe":
                if lane not in (
                    "policy-research",
                    "assembly-page",
                    "legislative-person",
                    "nec-page",
                    "dart",
                ):
                    p.add_argument("--resume", action="store_true")
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
                ):
                    p.add_argument(
                        "--page-size",
                        type=int,
                        default=10
                        if lane == "gwanbo"
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
    if args.lane == "gwanbo" and args.from_date > args.to_date:
        parser.error("from-date must precede to-date")
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
                    "status": "FAILED",
                    "error_code": "COMMAND_FAILED",
                },
                sort_keys=True,
            )
        )
        if isinstance(exc, ValueError):
            raise SystemExit(2) from None
        return 1
    return 0

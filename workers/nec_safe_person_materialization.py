from __future__ import annotations

import argparse
import json
import re

from sqlalchemy.exc import SQLAlchemyError

from packages.persistence import SqlAlchemyRepository
from packages.persistence.nec_person_materialization import DEFAULT_ELECTION_TYPES
from packages.verification.nec_person_materialization import NecPersonMaterializationError

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _types(value: str) -> tuple[int, ...]:
    try:
        parsed = tuple(sorted({int(item.strip()) for item in value.split(",") if item.strip()}))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("types must be comma-separated integers") from exc
    if not parsed:
        raise argparse.ArgumentTypeError("at least one election type is required")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Preflight or atomically materialize the deterministic private source-context "
            "subset of persisted NEC local-election candidate observations."
        )
    )
    parser.add_argument("--database-url")
    parser.add_argument("--election-id", default="20260603")
    parser.add_argument(
        "--types",
        type=_types,
        default=DEFAULT_ELECTION_TYPES,
        help="Comma-separated NEC election types; default 3,4,5,6,11.",
    )
    parser.add_argument("--commit", action="store_true")
    parser.add_argument("--expected-receipt-sha256")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.commit:
        expected = (args.expected_receipt_sha256 or "").strip().casefold()
        if not _SHA256.fullmatch(expected):
            parser.error("--commit requires --expected-receipt-sha256 with 64 hex characters")
    elif args.expected_receipt_sha256:
        parser.error("--expected-receipt-sha256 is only valid with --commit")

    repository = SqlAlchemyRepository(args.database_url)
    try:
        if args.commit:
            result = repository.commit_nec_person_materialization(
                expected_receipt_sha256=expected,
                election_id=args.election_id,
                election_types=args.types,
            )
        else:
            result = repository.prepare_nec_person_materialization(
                election_id=args.election_id,
                election_types=args.types,
            ).to_dict()
    except (NecPersonMaterializationError, RuntimeError, TypeError, ValueError) as exc:
        parser.error(str(exc))
    except SQLAlchemyError:
        parser.error("database operation failed; connection details were suppressed")

    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

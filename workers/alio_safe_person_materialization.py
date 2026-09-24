from __future__ import annotations

import argparse
import json
import re

from sqlalchemy.exc import SQLAlchemyError

from packages.persistence import SqlAlchemyRepository
from packages.verification.alio_person_materialization import AlioPersonMaterializationError

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Preflight or atomically materialize the deterministic safe subset of the "
            "persisted current ALIO item-4 executive roster. No network fetch or publication."
        )
    )
    parser.add_argument("--database-url")
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Perform the exact preflighted atomic Person/DRAFT-Claim materialization.",
    )
    parser.add_argument(
        "--expected-receipt-sha256",
        help="Required with --commit; exact SHA from the current dry-run receipt.",
    )
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
            result = repository.commit_alio_person_materialization(
                expected_receipt_sha256=expected,
            )
        else:
            result = repository.prepare_alio_person_materialization().to_dict()
    except (AlioPersonMaterializationError, RuntimeError, TypeError, ValueError) as exc:
        parser.error(str(exc))
    except SQLAlchemyError:
        parser.error("database operation failed; connection details were suppressed")

    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

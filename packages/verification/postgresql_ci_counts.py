"""Compute CI backup expectations through the canonical database and public query."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from sqlalchemy import func, select

from packages.application.queries import DirectoryView
from packages.domain.enums import PublicationStatus
from packages.persistence.database import Database
from packages.persistence.models import ClaimRow, PersonRow


def expected_counts(database_url: str) -> dict[str, int]:
    database = Database(database_url)
    database.assert_ready()
    try:
        with database.sessions() as session:
            people = int(session.scalar(select(func.count()).select_from(PersonRow)) or 0)
            organization_claims = int(
                session.scalar(
                    select(func.count())
                    .select_from(ClaimRow)
                    .where(
                        ClaimRow.organization_id.is_not(None),
                        ClaimRow.publication_status == PublicationStatus.PUBLISHED.value,
                        ClaimRow.superseded_at.is_(None),
                    )
                )
                or 0
            )
        with database(read_only=True) as uow:
            public_people = len(DirectoryView(uow).people())
    finally:
        database.close()
    return {
        "expected_people": people,
        "expected_public_people": public_people,
        "expected_organization_claims": organization_claims,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print backup/restore expectation counts.")
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args(argv)
    counts = expected_counts(args.database_url)
    print(json.dumps(counts, sort_keys=True))
    if args.github_output is not None:
        with args.github_output.open("a", encoding="utf-8") as handle:
            handle.writelines(
                f"{key.removeprefix('expected_')}={value}\n" for key, value in counts.items()
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json

from fastapi.testclient import TestClient
from sqlalchemy import func, select, text

from apps.api.main import create_app
from packages.domain.db import ClaimRow, PersonRow
from packages.domain.enums import PublicationStatus
from packages.persistence import SqlAlchemyRepository


def verify_restored_database(
    database_url: str,
    *,
    expected_people: int,
    expected_organization_claims: int,
    expected_public_people: int | None = None,
) -> dict[str, int | str]:
    repository = SqlAlchemyRepository(database_url)
    repository.assert_ready()
    with repository.sessions() as session:
        revision = session.scalar(text("SELECT version_num FROM alembic_version"))
        people = session.scalar(select(func.count()).select_from(PersonRow)) or 0
        organization_claims = (
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

    if people != expected_people:
        raise RuntimeError(f"restored Person count mismatch: {people} != {expected_people}")
    if organization_claims != expected_organization_claims:
        raise RuntimeError(
            "restored Organization Claim count mismatch: "
            f"{organization_claims} != {expected_organization_claims}"
        )

    public_people = expected_people if expected_public_people is None else expected_public_people
    with TestClient(create_app(repository)) as client:
        roster_response = client.get("/people")
        if roster_response.status_code != 200 or len(roster_response.json()) != public_people:
            raise RuntimeError(
                "restored public roster contract mismatch: "
                f"{len(roster_response.json()) if roster_response.status_code == 200 else 'HTTP_ERROR'} "
                f"!= {public_people}"
            )

    return {
        "alembic_revision": str(revision),
        "people": people,
        "public_people": public_people,
        "published_organization_claims": organization_claims,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify a restored Civic Intel PostgreSQL database.")
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--expected-people", required=True, type=int)
    parser.add_argument("--expected-organization-claims", required=True, type=int)
    parser.add_argument("--expected-public-people", type=int)
    args = parser.parse_args(argv)
    result = verify_restored_database(
        args.database_url,
        expected_people=args.expected_people,
        expected_organization_claims=args.expected_organization_claims,
        expected_public_people=args.expected_public_people,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

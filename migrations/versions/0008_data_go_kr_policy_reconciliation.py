"""Reconcile the shared apis.data.go.kr SourcePolicy for NEC and MOIS."""

from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

_POLICY_ID = "12000000-0000-0000-0000-000000000001"
_DOMAIN = "apis.data.go.kr"

_OLD_TERMS_CHECKED_AT = datetime(2026, 8, 31, tzinfo=UTC)
_OLD_RATE_LIMIT = (
    "Development account 10,000 requests; operational account requires review approval"
)
_OLD_POLICY_NOTE = (
    "Reviewed against data.go.kr datasets 15000908 and 15000864 on 2026-08-31 for "
    "the Central Election Commission candidate and winner APIs. Civic Intel discards "
    "candidate address and stores only public-interest election metadata."
)

_NEW_TERMS_CHECKED_AT = datetime(2026, 9, 22, tzinfo=UTC)
_NEW_RATE_LIMIT = (
    "Dataset/account-specific public-data-portal quotas apply. The reviewed NEC "
    "development account documents 10,000 requests; MOIS development/operation access "
    "is automatic. Source-specific workers must remain within the approved dataset scope."
)
_NEW_POLICY_NOTE = (
    "Host-level policy reviewed for exactly these Civic Intel lanes: NEC candidate "
    "dataset 15000908, NEC winner dataset 15000864, and MOIS Standard Organization "
    "Code dataset 15077870. This shared host policy does not authorize unrelated "
    "apis.data.go.kr endpoints. Source-specific connectors enforce endpoint, field, "
    "pagination and minimization contracts; credentials and raw fulltext are not persisted."
)


def _date_key(value: object) -> str | None:
    if value is None:
        return None
    return str(value)[:10]


def _policy_rows() -> list:
    return list(
        op.get_bind()
        .execute(
            sa.text(
                """
                SELECT id, domain, source_class, collection_mode,
                       can_fetch, can_store_metadata, can_store_fulltext,
                       can_send_to_ai, can_show_excerpt, can_commercialize,
                       robots_checked_at, terms_checked_at, license, rate_limit, policy_note
                FROM source_policies
                WHERE id = :policy_id OR domain = :domain
                """
            ),
            {"policy_id": _POLICY_ID, "domain": _DOMAIN},
        )
        .fetchall()
    )


def _require_expected_policy(
    *,
    terms_checked_at: datetime,
    rate_limit: str,
    policy_note: str,
) -> bool:
    rows = _policy_rows()
    if not rows:
        # Clean databases have no seeded SourcePolicy rows during schema migration.
        return False
    if len(rows) != 1:
        raise RuntimeError("apis.data.go.kr SourcePolicy identity is ambiguous")
    row = rows[0]._mapping
    expected = {
        "id": _POLICY_ID,
        "domain": _DOMAIN,
        "source_class": "official_open_api",
        "collection_mode": "API",
        "can_fetch": True,
        "can_store_metadata": True,
        "can_store_fulltext": False,
        "can_send_to_ai": False,
        "can_show_excerpt": False,
        "can_commercialize": True,
        "robots_checked_at": None,
        "license": "이용허락범위 제한 없음",
        "rate_limit": rate_limit,
        "policy_note": policy_note,
    }
    for key, value in expected.items():
        actual = bool(row[key]) if isinstance(value, bool) else row[key]
        if actual != value:
            raise RuntimeError(
                f"apis.data.go.kr SourcePolicy precondition failed for {key}"
            )
    if _date_key(row["terms_checked_at"]) != terms_checked_at.date().isoformat():
        raise RuntimeError(
            "apis.data.go.kr SourcePolicy precondition failed for terms_checked_at"
        )
    return True


def _update_policy(
    *,
    expected_terms_checked_at: datetime,
    expected_rate_limit: str,
    expected_policy_note: str,
    terms_checked_at: datetime,
    rate_limit: str,
    policy_note: str,
) -> None:
    if not _require_expected_policy(
        terms_checked_at=expected_terms_checked_at,
        rate_limit=expected_rate_limit,
        policy_note=expected_policy_note,
    ):
        return
    result = op.get_bind().execute(
        sa.text(
            """
            UPDATE source_policies
            SET terms_checked_at = :terms_checked_at,
                rate_limit = :rate_limit,
                policy_note = :policy_note
            WHERE id = :policy_id AND domain = :domain
            """
        ),
        {
            "terms_checked_at": terms_checked_at,
            "rate_limit": rate_limit,
            "policy_note": policy_note,
            "policy_id": _POLICY_ID,
            "domain": _DOMAIN,
        },
    )
    if result.rowcount != 1:
        raise RuntimeError("apis.data.go.kr SourcePolicy reconciliation updated no exact row")


def upgrade() -> None:
    _update_policy(
        expected_terms_checked_at=_OLD_TERMS_CHECKED_AT,
        expected_rate_limit=_OLD_RATE_LIMIT,
        expected_policy_note=_OLD_POLICY_NOTE,
        terms_checked_at=_NEW_TERMS_CHECKED_AT,
        rate_limit=_NEW_RATE_LIMIT,
        policy_note=_NEW_POLICY_NOTE,
    )


def downgrade() -> None:
    _update_policy(
        expected_terms_checked_at=_NEW_TERMS_CHECKED_AT,
        expected_rate_limit=_NEW_RATE_LIMIT,
        expected_policy_note=_NEW_POLICY_NOTE,
        terms_checked_at=_OLD_TERMS_CHECKED_AT,
        rate_limit=_OLD_RATE_LIMIT,
        policy_note=_OLD_POLICY_NOTE,
    )

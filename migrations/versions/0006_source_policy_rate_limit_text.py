"""Store descriptive source rate-limit policy without silent truncation."""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def _rate_limit_type() -> sa.types.TypeEngine:
    column = next(
        item
        for item in sa.inspect(op.get_bind()).get_columns("source_policies")
        if item["name"] == "rate_limit"
    )
    return column["type"]


def upgrade() -> None:
    existing_type = _rate_limit_type()
    if isinstance(existing_type, sa.Text):
        return
    with op.batch_alter_table("source_policies") as batch:
        batch.alter_column(
            "rate_limit",
            existing_type=existing_type,
            type_=sa.Text(),
            existing_nullable=True,
        )


def downgrade() -> None:
    existing_type = _rate_limit_type()
    longest = op.get_bind().execute(
        sa.text("SELECT MAX(LENGTH(rate_limit)) FROM source_policies")
    ).scalar_one()
    if longest is not None and longest > 100:
        raise RuntimeError("cannot narrow source_policies.rate_limit while values exceed 100 chars")
    with op.batch_alter_table("source_policies") as batch:
        batch.alter_column(
            "rate_limit",
            existing_type=existing_type,
            type_=sa.String(length=100),
            existing_nullable=True,
        )

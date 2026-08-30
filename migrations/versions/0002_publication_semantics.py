"""Separate publication visibility from epistemic assertion semantics."""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("claims")}
    if "publication_status" in columns:
        return
    with op.batch_alter_table("claims") as batch:
        batch.add_column(sa.Column("subject", sa.Text(), nullable=True))
        batch.add_column(sa.Column("predicate", sa.String(length=120), nullable=True))
        batch.add_column(sa.Column("object_text", sa.Text(), nullable=True))
        batch.add_column(sa.Column("qualifiers", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("publication_status", sa.String(length=32), nullable=True))
        batch.add_column(sa.Column("asserted_as_true", sa.Boolean(), nullable=True))
        batch.add_column(sa.Column("resolution_note", sa.Text(), nullable=True))
    op.execute(
        sa.text(
            "UPDATE claims SET subject = '', predicate = 'legacy', object_text = proposition, qualifiers = '{}', publication_status = CASE WHEN published = 1 THEN 'PUBLISHED' ELSE 'DRAFT' END, asserted_as_true = CASE WHEN epistemic_status = 'FACT' THEN 1 ELSE 0 END"
        )
    )
    with op.batch_alter_table("claims") as batch:
        batch.alter_column("subject", nullable=False)
        batch.alter_column("predicate", nullable=False)
        batch.alter_column("object_text", nullable=False)
        batch.alter_column("qualifiers", nullable=False)
        batch.alter_column("publication_status", nullable=False)
        batch.alter_column("asserted_as_true", nullable=False)
        batch.drop_column("published")
        batch.create_index("ix_claims_predicate", ["predicate"])
        batch.create_index("ix_claims_publication_status", ["publication_status"])


def downgrade() -> None:
    columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("claims")}
    if "published" in columns:
        return
    with op.batch_alter_table("claims") as batch:
        batch.add_column(sa.Column("published", sa.Boolean(), nullable=True))
    op.execute(
        sa.text(
            "UPDATE claims SET published = CASE WHEN publication_status = 'PUBLISHED' THEN 1 ELSE 0 END"
        )
    )
    with op.batch_alter_table("claims") as batch:
        batch.alter_column("published", nullable=False)
        batch.drop_index("ix_claims_publication_status")
        batch.drop_index("ix_claims_predicate")
        batch.drop_column("resolution_note")
        batch.drop_column("asserted_as_true")
        batch.drop_column("publication_status")
        batch.drop_column("qualifiers")
        batch.drop_column("object_text")
        batch.drop_column("predicate")
        batch.drop_column("subject")

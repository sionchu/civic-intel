"""Allow canonical Claims to target one Person or one Organization."""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


_ONE_SUBJECT = (
    "(person_id IS NOT NULL AND organization_id IS NULL) OR "
    "(person_id IS NULL AND organization_id IS NOT NULL)"
)


def _claims_table(*, organization_subject: bool = False) -> sa.Table:
    metadata = sa.MetaData()
    columns = [
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "person_id",
            sa.String(length=36),
            sa.ForeignKey("people.id"),
            nullable=organization_subject,
        ),
        sa.Column("proposition", sa.Text(), nullable=False),
        sa.Column("epistemic_status", sa.String(length=32), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("predicate", sa.String(length=120), nullable=False),
        sa.Column("object_text", sa.Text(), nullable=False),
        sa.Column("qualifiers", sa.JSON(), nullable=False),
        sa.Column("publication_status", sa.String(length=32), nullable=False),
        sa.Column("asserted_as_true", sa.Boolean(), nullable=False),
        sa.Column("resolution_note", sa.Text(), nullable=True),
    ]
    if organization_subject:
        columns.insert(
            2,
            sa.Column(
                "organization_id",
                sa.String(length=36),
                nullable=True,
            ),
        )
    table = sa.Table("claims", metadata, *columns)
    if organization_subject:
        table.append_constraint(
            sa.ForeignKeyConstraint(
                ["organization_id"],
                ["organizations.id"],
                name="fk_claims_organization_id",
            )
        )
        table.append_constraint(sa.CheckConstraint(_ONE_SUBJECT, name="ck_claims_one_subject"))
        sa.Index("ix_claims_organization_id", table.c.organization_id)
    sa.Index("ix_claims_person_id", table.c.person_id)
    sa.Index("ix_claims_predicate", table.c.predicate)
    sa.Index("ix_claims_publication_status", table.c.publication_status)
    return table


def upgrade() -> None:
    bind = op.get_bind()
    columns = {item["name"] for item in sa.inspect(bind).get_columns("claims")}
    if "organization_id" in columns:
        return
    if bind.dialect.name == "postgresql":
        op.alter_column(
            "claims",
            "person_id",
            existing_type=sa.String(length=36),
            nullable=True,
        )
        op.add_column("claims", sa.Column("organization_id", sa.String(length=36)))
        op.create_foreign_key(
            "fk_claims_organization_id",
            "claims",
            "organizations",
            ["organization_id"],
            ["id"],
        )
        op.create_index("ix_claims_organization_id", "claims", ["organization_id"])
        op.create_check_constraint("ck_claims_one_subject", "claims", _ONE_SUBJECT)
        return

    with op.batch_alter_table(
        "claims", recreate="always", copy_from=_claims_table()
    ) as batch:
        batch.alter_column(
            "person_id",
            existing_type=sa.String(length=36),
            nullable=True,
        )
        batch.add_column(sa.Column("organization_id", sa.String(length=36), nullable=True))
        batch.create_foreign_key(
            "fk_claims_organization_id",
            "organizations",
            ["organization_id"],
            ["id"],
        )
        batch.create_index("ix_claims_organization_id", ["organization_id"])
        batch.create_check_constraint("ck_claims_one_subject", _ONE_SUBJECT)


def downgrade() -> None:
    bind = op.get_bind()
    organization_claims = bind.execute(
        sa.text("SELECT COUNT(*) FROM claims WHERE organization_id IS NOT NULL")
    ).scalar_one()
    if organization_claims:
        raise RuntimeError(
            "cannot downgrade organization-scoped claims while organization claims exist"
        )

    if bind.dialect.name == "postgresql":
        op.drop_constraint("ck_claims_one_subject", "claims", type_="check")
        op.drop_index("ix_claims_organization_id", table_name="claims")
        op.drop_constraint("fk_claims_organization_id", "claims", type_="foreignkey")
        op.drop_column("claims", "organization_id")
        op.alter_column(
            "claims",
            "person_id",
            existing_type=sa.String(length=36),
            nullable=False,
        )
        return

    with op.batch_alter_table(
        "claims", recreate="always", copy_from=_claims_table(organization_subject=True)
    ) as batch:
        batch.drop_constraint("ck_claims_one_subject", type_="check")
        batch.drop_index("ix_claims_organization_id")
        batch.drop_constraint("fk_claims_organization_id", type_="foreignkey")
        batch.drop_column("organization_id")
        batch.alter_column(
            "person_id",
            existing_type=sa.String(length=36),
            nullable=False,
        )

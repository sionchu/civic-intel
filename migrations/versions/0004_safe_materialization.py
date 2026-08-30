"""Add observation identity links, review items, and claim-level row provenance."""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "identity_review_items" not in tables:
        op.create_table(
            "identity_review_items",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("observation_id", sa.String(length=36), nullable=False),
            sa.Column("candidate_person_id", sa.String(length=36), nullable=True),
            sa.Column("reason_code", sa.String(length=100), nullable=False),
            sa.Column("details_json", sa.JSON(), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("resolution_note", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(["observation_id"], ["feeder_observations.id"]),
            sa.ForeignKeyConstraint(["candidate_person_id"], ["people.id"]),
        )
        op.create_index(
            "ix_identity_review_items_candidate_person_id",
            "identity_review_items",
            ["candidate_person_id"],
        )
        op.create_index(
            "ix_identity_review_items_observation_id",
            "identity_review_items",
            ["observation_id"],
        )
        op.create_index(
            "ix_identity_review_items_reason_code",
            "identity_review_items",
            ["reason_code"],
        )
        op.create_index(
            "ix_identity_review_items_status", "identity_review_items", ["status"]
        )

    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "person_observation_links" not in tables:
        op.create_table(
            "person_observation_links",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("person_id", sa.String(length=36), nullable=False),
            sa.Column("observation_id", sa.String(length=36), nullable=False),
            sa.Column("action", sa.String(length=40), nullable=False),
            sa.Column("decision_class", sa.String(length=80), nullable=False),
            sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("review_item_id", sa.String(length=36), nullable=True),
            sa.ForeignKeyConstraint(["person_id"], ["people.id"]),
            sa.ForeignKeyConstraint(["observation_id"], ["feeder_observations.id"]),
            sa.ForeignKeyConstraint(["review_item_id"], ["identity_review_items.id"]),
            sa.UniqueConstraint(
                "person_id", "observation_id", name="uq_person_observation_links_pair"
            ),
        )
        for column in (
            "action",
            "decision_class",
            "observation_id",
            "person_id",
            "review_item_id",
        ):
            op.create_index(
                f"ix_person_observation_links_{column}",
                "person_observation_links",
                [column],
            )

    evidence_columns = {
        item["name"] for item in sa.inspect(op.get_bind()).get_columns("claim_evidence")
    }
    if "feeder_observation_id" not in evidence_columns:
        with op.batch_alter_table("claim_evidence") as batch:
            batch.add_column(sa.Column("feeder_observation_id", sa.String(length=36)))
            batch.create_foreign_key(
                "fk_claim_evidence_feeder_observation_id",
                "feeder_observations",
                ["feeder_observation_id"],
                ["id"],
            )
            batch.create_index(
                "ix_claim_evidence_feeder_observation_id", ["feeder_observation_id"]
            )


def downgrade() -> None:
    evidence_columns = {
        item["name"] for item in sa.inspect(op.get_bind()).get_columns("claim_evidence")
    }
    if "feeder_observation_id" in evidence_columns:
        with op.batch_alter_table("claim_evidence") as batch:
            batch.drop_index("ix_claim_evidence_feeder_observation_id")
            batch.drop_column("feeder_observation_id")
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "person_observation_links" in tables:
        op.drop_table("person_observation_links")
    if "identity_review_items" in tables:
        op.drop_table("identity_review_items")

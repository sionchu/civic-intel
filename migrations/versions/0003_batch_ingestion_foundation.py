"""Add persistent batch runs, checkpoints, and record observations."""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "source_runs" not in tables:
        op.create_table(
            "source_runs",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("feeder", sa.String(length=100), nullable=False),
            sa.Column("scope_key", sa.String(length=300), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("checkpoint_before", sa.Text(), nullable=True),
            sa.Column("checkpoint_after", sa.Text(), nullable=True),
            sa.Column("records_seen", sa.Integer(), nullable=False),
            sa.Column("observations_created", sa.Integer(), nullable=False),
            sa.Column("observations_unchanged", sa.Integer(), nullable=False),
            sa.Column("error_code", sa.String(length=120), nullable=True),
            sa.Column("error_summary", sa.Text(), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=False),
        )
        op.create_index("ix_source_runs_feeder", "source_runs", ["feeder"])
        op.create_index(
            "ix_source_runs_feeder_scope", "source_runs", ["feeder", "scope_key"]
        )
        op.create_index("ix_source_runs_started_at", "source_runs", ["started_at"])
        op.create_index("ix_source_runs_status", "source_runs", ["status"])

    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "source_checkpoints" not in tables:
        op.create_table(
            "source_checkpoints",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("feeder", sa.String(length=100), nullable=False),
            sa.Column("scope_key", sa.String(length=300), nullable=False),
            sa.Column("cursor", sa.Text(), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_run_id", sa.String(length=36), nullable=True),
            sa.ForeignKeyConstraint(["last_run_id"], ["source_runs.id"]),
            sa.UniqueConstraint(
                "feeder", "scope_key", name="uq_source_checkpoints_feeder_scope"
            ),
        )
        op.create_index(
            "ix_source_checkpoints_last_run_id", "source_checkpoints", ["last_run_id"]
        )

    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "feeder_observations" not in tables:
        op.create_table(
            "feeder_observations",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("feeder", sa.String(length=100), nullable=False),
            sa.Column("scope_key", sa.String(length=300), nullable=False),
            sa.Column("provider_record_key", sa.String(length=500), nullable=False),
            sa.Column("snapshot_id", sa.String(length=36), nullable=False),
            sa.Column("run_id", sa.String(length=36), nullable=False),
            sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("provider_observed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("semantic_scope", sa.String(length=120), nullable=False),
            sa.Column("identity_hints_json", sa.JSON(), nullable=False),
            sa.Column("normalized_json", sa.JSON(), nullable=False),
            sa.Column("content_hash", sa.String(length=64), nullable=False),
            sa.ForeignKeyConstraint(["snapshot_id"], ["source_snapshots.id"]),
            sa.ForeignKeyConstraint(["run_id"], ["source_runs.id"]),
            sa.UniqueConstraint(
                "feeder",
                "scope_key",
                "provider_record_key",
                "content_hash",
                name="uq_feeder_observations_version",
            ),
        )
        op.create_index(
            "ix_feeder_observations_content_hash", "feeder_observations", ["content_hash"]
        )
        op.create_index(
            "ix_feeder_observations_feeder_provider",
            "feeder_observations",
            ["feeder", "provider_record_key"],
        )
        op.create_index(
            "ix_feeder_observations_run_id", "feeder_observations", ["run_id"]
        )
        op.create_index(
            "ix_feeder_observations_semantic_scope",
            "feeder_observations",
            ["semantic_scope"],
        )
        op.create_index(
            "ix_feeder_observations_snapshot_id", "feeder_observations", ["snapshot_id"]
        )


def downgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "feeder_observations" in tables:
        op.drop_table("feeder_observations")
    if "source_checkpoints" in tables:
        op.drop_table("source_checkpoints")
    if "source_runs" in tables:
        op.drop_table("source_runs")

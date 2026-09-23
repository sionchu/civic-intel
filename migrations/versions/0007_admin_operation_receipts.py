"""Add append-only operator receipts; existing evidence tables are unchanged."""

from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "admin_operations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("actor", sa.String(100), nullable=False),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("command_hash", sa.String(64), nullable=False),
        sa.Column("state_hash", sa.String(64), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("targets", sa.JSON(), nullable=False),
        sa.Column("changes", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
    )
    for column in ("actor", "action", "created_at"):
        op.create_index(f"ix_admin_operations_{column}", "admin_operations", [column])
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute("""CREATE FUNCTION civic_admin_receipt_immutable() RETURNS trigger
            LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Admin receipts are append-only'; END $$""")
        op.execute("""CREATE TRIGGER admin_receipt_no_update_delete
            BEFORE UPDATE OR DELETE ON admin_operations FOR EACH ROW
            EXECUTE FUNCTION civic_admin_receipt_immutable()""")
    elif dialect == "sqlite":
        for action in ("UPDATE", "DELETE"):
            op.execute(f"""CREATE TRIGGER admin_receipt_no_{action.lower()} BEFORE {action}
                ON admin_operations BEGIN SELECT RAISE(ABORT, 'Admin receipts are append-only'); END""")


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TRIGGER admin_receipt_no_update_delete ON admin_operations")
        op.execute("DROP FUNCTION civic_admin_receipt_immutable()")
    op.drop_table("admin_operations")

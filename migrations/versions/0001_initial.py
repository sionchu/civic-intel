"""Initial canonical schema."""

from alembic import op

from packages.domain.db import Base

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Later audit tables are owned exclusively by their numbered migrations.
    tables = [table for table in Base.metadata.sorted_tables if table.name != "admin_operations"]
    Base.metadata.create_all(bind=op.get_bind(), tables=tables)


def downgrade() -> None:
    tables = [table for table in Base.metadata.sorted_tables if table.name != "admin_operations"]
    Base.metadata.drop_all(bind=op.get_bind(), tables=tables)

from __future__ import annotations

from typing import Any

from sqlalchemy import event

from packages.persistence.database import Database


def configure_read_only(repository: Database, *, allow_writes: bool = False) -> None:
    """Apply database-enforced read-only defaults to this dedicated engine only."""
    dialect = repository.engine.dialect.name
    if dialect not in {"sqlite", "postgresql"}:
        raise RuntimeError("Operator console supports SQLite or PostgreSQL only")

    @event.listens_for(repository.engine, "connect")
    def readonly_connection(connection: Any, _: Any) -> None:
        cursor = connection.cursor()
        try:
            if dialect == "sqlite":
                cursor.execute(
                    "PRAGMA query_only = OFF" if allow_writes else "PRAGMA query_only = ON"
                )
                cursor.execute("PRAGMA busy_timeout = 5000")
            else:
                connection.autocommit = True
                cursor.execute(
                    "SET default_transaction_read_only = off"
                    if allow_writes
                    else "SET default_transaction_read_only = on"
                )
                cursor.execute("SET statement_timeout = 15000")
                cursor.execute("SET idle_in_transaction_session_timeout = 20000")
                cursor.execute(
                    "SET default_transaction_isolation = 'read committed'"
                    if allow_writes
                    else "SET default_transaction_isolation = 'repeatable read'"
                )
                connection.autocommit = False
        finally:
            cursor.close()

    repository.engine.dispose()

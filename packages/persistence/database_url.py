from __future__ import annotations


def normalize_database_url(database_url: str) -> str:
    """Use the project's supported PostgreSQL DBAPI for provider-supplied URLs."""

    if database_url.startswith("postgresql://"):
        return f"postgresql+psycopg://{database_url.removeprefix('postgresql://')}"
    return database_url

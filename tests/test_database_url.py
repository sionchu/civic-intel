from packages.persistence.database_url import normalize_database_url
from packages.persistence.repository import SqlAlchemyRepository


def test_provider_postgresql_url_uses_project_psycopg_driver() -> None:
    database_url = "postgresql://user:password@postgres.railway.internal:5432/railway"

    assert normalize_database_url(database_url) == (
        "postgresql+psycopg://user:password@postgres.railway.internal:5432/railway"
    )
    repository = SqlAlchemyRepository(database_url)
    assert repository.engine.url.drivername == "postgresql+psycopg"


def test_database_url_normalization_preserves_explicit_driver_and_sqlite() -> None:
    assert normalize_database_url("postgresql+psycopg://user:password@host:5432/db") == (
        "postgresql+psycopg://user:password@host:5432/db"
    )
    assert normalize_database_url("sqlite:///./civic_intel.db") == "sqlite:///./civic_intel.db"

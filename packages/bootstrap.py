from __future__ import annotations

from packages.application.context import Application
from packages.persistence.database import Database
from packages.persistence.errors import DatabaseNotReady


def application(database_url: str | None = None) -> Application:
    return Application(Database(database_url))


def bootstrap_database(target: Database, mode: str | None = None) -> Database:
    selected = (mode or "runtime").strip().casefold()
    if selected == "runtime":
        target.assert_ready()
    elif selected == "golden":
        Application(target).onboarding.seed_golden()
    else:
        raise DatabaseNotReady(
            f"Unsupported CIVIC_BOOTSTRAP_MODE {selected!r}; expected 'runtime' or 'golden'"
        )
    return target

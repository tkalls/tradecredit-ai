"""Ports: what the domain needs from the outside world, written as Protocols.

The domain says *what* it needs ("give me application X", "keep this change"). Adapters in
app/adapters/ say *how* (a dict in memory for tests, Postgres in production). Services only ever
see the Protocol, so swapping the storage never touches the domain or the services.
"""

from typing import Protocol

from app.domain.application import Application


class ApplicationNotFound(Exception):
    """No application is stored under this id."""


class ApplicationAlreadyExists(Exception):
    """add() was called with an id that is already stored."""


class StaleApplication(Exception):
    """Another save landed after this copy was loaded, so saving it would overwrite that one."""


class ApplicationRepository(Protocol):
    def add(self, application: Application) -> None:
        """Store a new application. Raises ApplicationAlreadyExists if the id is taken."""
        ...

    def get(self, id: str) -> Application:
        """Load a copy of an application. Raises ApplicationNotFound."""
        ...

    def save(self, application: Application) -> None:
        """Store changes to an application that was loaded with get().

        Raises ApplicationNotFound if it was never added, and StaleApplication if its version no
        longer matches the stored one (another worker saved first). On success the version goes up
        by one, both on the stored copy and on the object passed in.
        """
        ...

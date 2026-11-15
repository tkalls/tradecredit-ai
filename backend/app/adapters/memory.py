import copy

from app.domain.application import Application
from app.domain.ports import ApplicationAlreadyExists, ApplicationNotFound, StaleApplication


class InMemoryApplicationRepository:
    def __init__(self) -> None:
        self._items: dict[str, Application] = {}

    def add(self, application: Application) -> None:
        if application.id in self._items:
            raise ApplicationAlreadyExists(application.id)
        self._items[application.id] = copy.deepcopy(application)

    def get(self, id: str) -> Application:
        if id not in self._items:
            raise ApplicationNotFound(id)
        return copy.deepcopy(self._items[id])

    def save(self, application: Application) -> None:
        stored = self._items.get(application.id)
        if stored is None:
            raise ApplicationNotFound(application.id)
        if stored.version != application.version:
            raise StaleApplication(application.id)
        application.version += 1
        self._items[application.id] = copy.deepcopy(application)

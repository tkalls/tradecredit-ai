"""Contract tests for ApplicationRepository.

They only use the Protocol's three methods, so the SQLAlchemy repository can later run the very
same tests by adding itself to the `repo` fixture's params.
"""

import pytest

from app.adapters.memory import InMemoryApplicationRepository
from app.domain.application import Application, ApplicationState
from app.domain.ports import (
    ApplicationAlreadyExists,
    ApplicationNotFound,
    ApplicationRepository,
    StaleApplication,
)

S = ApplicationState


@pytest.fixture(params=[InMemoryApplicationRepository])
def repo(request: pytest.FixtureRequest) -> ApplicationRepository:
    repository: ApplicationRepository = request.param()
    return repository


def test_get_returns_what_was_added(repo: ApplicationRepository) -> None:
    repo.add(Application(id="app-1"))

    loaded = repo.get("app-1")

    assert loaded.id == "app-1", "the loaded application keeps its id"
    assert loaded.state is S.RECEIVED, "a new application starts in RECEIVED"


def test_get_unknown_id_raises(repo: ApplicationRepository) -> None:
    with pytest.raises(ApplicationNotFound):
        repo.get("nope")


def test_add_twice_raises(repo: ApplicationRepository) -> None:
    repo.add(Application(id="app-1"))

    with pytest.raises(ApplicationAlreadyExists):
        repo.add(Application(id="app-1"))


def test_save_never_added_raises(repo: ApplicationRepository) -> None:
    with pytest.raises(ApplicationNotFound):
        repo.save(Application(id="ghost"))


def test_a_move_is_kept_only_after_save(repo: ApplicationRepository) -> None:
    repo.add(Application(id="app-1"))
    app = repo.get("app-1")

    app.move_to(S.PARSING, actor="worker-1", reason="picked up")
    assert repo.get("app-1").state is S.RECEIVED, "an unsaved move must not leak into storage"

    repo.save(app)
    reloaded = repo.get("app-1")
    assert reloaded.state is S.PARSING, "save() stores the new state"
    assert len(reloaded.history) == 1, "save() stores the audit log with it"
    assert reloaded.history[0].actor == "worker-1", "the audit entry survives the round trip"


def test_changing_the_object_passed_to_add_does_not_change_storage(
    repo: ApplicationRepository,
) -> None:
    app = Application(id="app-1")
    repo.add(app)

    app.move_to(S.PARSING, actor="worker-1", reason="picked up")

    assert repo.get("app-1").state is S.RECEIVED, "add() must store a copy, not the caller's object"


def test_each_save_bumps_the_version(repo: ApplicationRepository) -> None:
    repo.add(Application(id="app-1"))
    app = repo.get("app-1")
    start = app.version

    app.move_to(S.PARSING, actor="worker-1", reason="picked up")
    repo.save(app)
    assert app.version == start + 1, "save() bumps the version on the caller's object"

    app.move_to(S.EXTRACTING, actor="worker-1", reason="parsed")
    repo.save(app)
    assert repo.get("app-1").version == start + 2, "and on the stored copy"


def test_second_worker_saving_a_stale_copy_is_refused(repo: ApplicationRepository) -> None:
    repo.add(Application(id="app-1"))
    worker_a = repo.get("app-1")
    worker_b = repo.get("app-1")

    worker_a.move_to(S.PARSING, actor="worker-a", reason="picked up")
    repo.save(worker_a)

    worker_b.move_to(S.PARSING, actor="worker-b", reason="picked up")
    with pytest.raises(StaleApplication):
        repo.save(worker_b)

    stored = repo.get("app-1")
    assert [t.actor for t in stored.history] == ["worker-a"], "only the first save counts"

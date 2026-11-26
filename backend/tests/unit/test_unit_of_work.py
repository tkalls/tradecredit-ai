"""Contract tests for UnitOfWork: a `with` block is all or nothing.

Like the repository tests, they only use the Protocol, so the SQLAlchemy unit of work can run
the same tests later by joining the `uow` fixture's params.
"""

import pytest

from app.adapters.memory import InMemoryUnitOfWork
from app.domain.application import Application, ApplicationState
from app.domain.ports import ApplicationNotFound, UnitOfWork

S = ApplicationState


@pytest.fixture(params=[InMemoryUnitOfWork])
def uow(request: pytest.FixtureRequest) -> UnitOfWork:
    unit: UnitOfWork = request.param()
    return unit


def test_committed_work_is_kept(uow: UnitOfWork) -> None:
    with uow:
        uow.applications.add(Application(id="app-1"))
        uow.commit()

    with uow:
        assert uow.applications.get("app-1").id == "app-1", "commit() keeps the new application"


def test_work_without_commit_is_thrown_away(uow: UnitOfWork) -> None:
    with uow:
        uow.applications.add(Application(id="app-1"))

    with uow, pytest.raises(ApplicationNotFound):
        uow.applications.get("app-1")


def test_an_error_rolls_everything_back_and_still_reaches_the_caller(uow: UnitOfWork) -> None:
    with pytest.raises(RuntimeError, match="worker crashed"), uow:
        uow.applications.add(Application(id="app-1"))
        raise RuntimeError("worker crashed")

    with uow, pytest.raises(ApplicationNotFound):
        uow.applications.get("app-1")


def test_two_changes_are_all_or_nothing(uow: UnitOfWork) -> None:
    with uow:
        uow.applications.add(Application(id="app-1"))
        uow.commit()

    with pytest.raises(RuntimeError), uow:
        app = uow.applications.get("app-1")
        app.move_to(S.PARSING, actor="worker-1", reason="picked up")
        uow.applications.save(app)
        uow.applications.add(Application(id="app-2"))
        raise RuntimeError("crash before commit")

    with uow:
        assert uow.applications.get("app-1").state is S.RECEIVED, "the saved move was undone"
        with pytest.raises(ApplicationNotFound):
            uow.applications.get("app-2")


def test_commit_is_a_safe_point_inside_the_block(uow: UnitOfWork) -> None:
    with pytest.raises(RuntimeError), uow:
        uow.applications.add(Application(id="app-1"))
        uow.commit()
        uow.applications.add(Application(id="app-2"))
        raise RuntimeError("crash after the first commit")

    with uow:
        assert uow.applications.get("app-1").id == "app-1", "work before commit() survives"
        with pytest.raises(ApplicationNotFound):
            uow.applications.get("app-2")


def test_rollback_undoes_work_since_the_last_commit(uow: UnitOfWork) -> None:
    with uow:
        uow.applications.add(Application(id="app-1"))
        uow.rollback()
        with pytest.raises(ApplicationNotFound):
            uow.applications.get("app-1")

"""The application state machine, written as tests from the three design decisions (5 Nov 2026).

The table below is the spec. It is copied here on purpose instead of imported from the code,
so a wrong edit to the code's table makes these tests fail instead of quietly agreeing with it.
"""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from itertools import product

import pytest

from app.domain.application import (
    ALLOWED_TRANSITIONS,
    Application,
    ApplicationState,
    InvalidTransition,
)

S = ApplicationState

EXPECTED: dict[ApplicationState, set[ApplicationState]] = {
    S.RECEIVED: {S.PARSING, S.FAILED},
    S.PARSING: {S.EXTRACTING, S.FAILED},
    S.EXTRACTING: {S.SCORING, S.NEEDS_REVIEW_EXTRACTION, S.FAILED},
    S.NEEDS_REVIEW_EXTRACTION: {S.SCORING},
    S.SCORING: {S.DECIDING, S.FAILED},
    S.DECIDING: {S.DECIDED, S.NEEDS_REVIEW_DECISION, S.FAILED},
    S.NEEDS_REVIEW_DECISION: {S.DECIDED},
    S.DECIDED: set(),
    S.FAILED: {S.RECEIVED},
}

ALLOWED = [(start, end) for start, ends in EXPECTED.items() for end in ends]
FORBIDDEN = [(start, end) for start, end in product(S, S) if end not in EXPECTED[start]]


def application_in(state: ApplicationState) -> Application:
    """An application already sitting in `state`, as a repository would load it."""
    return Application(id="app-1", state=state)


# The whole table ------------------------------------------------------------------------------


def test_there_are_nine_states() -> None:
    assert len(S) == 9


def test_the_code_table_matches_the_spec_exactly() -> None:
    assert dict(ALLOWED_TRANSITIONS) == {state: frozenset(ends) for state, ends in EXPECTED.items()}


def test_the_table_cannot_be_changed_while_running() -> None:
    with pytest.raises(TypeError):
        ALLOWED_TRANSITIONS[S.DECIDED] = frozenset({S.SCORING})  # type: ignore[index]
    with pytest.raises(AttributeError):
        ALLOWED_TRANSITIONS[S.NEEDS_REVIEW_DECISION].add(S.SCORING)  # type: ignore[attr-defined]


def _reachable_from(start: ApplicationState) -> set[ApplicationState]:
    seen, todo = {start}, [start]
    while todo:
        for end in ALLOWED_TRANSITIONS[todo.pop()]:
            if end not in seen:
                seen.add(end)
                todo.append(end)
    return seen


def test_every_state_can_be_reached_from_received() -> None:
    assert _reachable_from(S.RECEIVED) == set(S)


@pytest.mark.parametrize("state", list(S))
def test_no_state_is_a_trap_every_one_can_still_end_in_decided(state: ApplicationState) -> None:
    assert S.DECIDED in _reachable_from(state)


def test_a_new_application_starts_in_received_with_no_history() -> None:
    application = Application(id="app-1")

    assert application.state is S.RECEIVED
    assert application.history == ()


@pytest.mark.parametrize(("start", "end"), ALLOWED)
def test_every_allowed_move_works(start: ApplicationState, end: ApplicationState) -> None:
    application = application_in(start)

    application.move_to(end, actor="test", reason="allowed move")

    assert application.state is end


@pytest.mark.parametrize(("start", "end"), FORBIDDEN)
def test_every_other_move_is_refused_and_changes_nothing(
    start: ApplicationState, end: ApplicationState
) -> None:
    application = application_in(start)

    with pytest.raises(InvalidTransition):
        application.move_to(end, actor="test", reason="forbidden move")

    assert application.state is start
    assert application.history == ()


# The three decisions, one story each -----------------------------------------------------------


def test_a_clean_application_goes_straight_through() -> None:
    application = Application(id="app-1")

    for step in (S.PARSING, S.EXTRACTING, S.SCORING, S.DECIDING, S.DECIDED):
        application.move_to(step, actor="worker", reason="step finished")

    assert [entry.to_state for entry in application.history] == [
        S.PARSING,
        S.EXTRACTING,
        S.SCORING,
        S.DECIDING,
        S.DECIDED,
    ]


@pytest.mark.parametrize("state", [S.RECEIVED, S.PARSING, S.EXTRACTING, S.SCORING, S.DECIDING])
def test_decision_1_these_states_can_give_up(state: ApplicationState) -> None:
    application = application_in(state)

    application.move_to(S.FAILED, actor="worker", reason="retries ran out")

    assert application.state is S.FAILED


@pytest.mark.parametrize("end", list(S))
def test_decision_1_decided_is_final(end: ApplicationState) -> None:
    with pytest.raises(InvalidTransition):
        application_in(S.DECIDED).move_to(end, actor="test", reason="after the decision")


@pytest.mark.parametrize("review", [S.NEEDS_REVIEW_EXTRACTION, S.NEEDS_REVIEW_DECISION])
def test_decision_1_waiting_for_a_human_is_never_a_failure(review: ApplicationState) -> None:
    with pytest.raises(InvalidTransition):
        application_in(review).move_to(S.FAILED, actor="sweeper", reason="reviewer is late")


def test_decision_2_a_refer_can_never_go_back_to_scoring() -> None:
    with pytest.raises(InvalidTransition):
        application_in(S.NEEDS_REVIEW_DECISION).move_to(
            S.SCORING, actor="reviewer", reason="should be impossible"
        )


def test_decision_2_a_fixed_field_carries_on_to_scoring() -> None:
    application = application_in(S.NEEDS_REVIEW_EXTRACTION)

    application.move_to(S.SCORING, actor="reviewer:amina", reason="corrected invoice amount")

    assert application.state is S.SCORING


def test_decision_3_a_failed_application_restarts_from_the_top_with_one_history() -> None:
    application = Application(id="app-1")
    application.move_to(S.PARSING, actor="worker", reason="picked up")
    application.move_to(S.FAILED, actor="worker", reason="invoice.pdf is corrupted")
    application.move_to(S.RECEIVED, actor="borrower", reason="re-uploaded invoice.pdf")
    application.move_to(S.PARSING, actor="worker", reason="picked up")

    assert application.state is S.PARSING
    assert [(entry.from_state, entry.to_state) for entry in application.history] == [
        (S.RECEIVED, S.PARSING),
        (S.PARSING, S.FAILED),
        (S.FAILED, S.RECEIVED),
        (S.RECEIVED, S.PARSING),
    ]


# The audit log ---------------------------------------------------------------------------------


def test_every_move_records_who_why_and_when() -> None:
    application = Application(id="app-1")

    entry = application.move_to(S.PARSING, actor="worker", reason="picked up")

    assert application.history == (entry,)
    assert entry.from_state is S.RECEIVED
    assert entry.to_state is S.PARSING
    assert entry.actor == "worker"
    assert entry.reason == "picked up"
    assert entry.at.tzinfo is not None


@pytest.mark.parametrize(("actor", "reason"), [("", "picked up"), ("worker", "  ")])
def test_a_move_without_who_or_why_is_refused(actor: str, reason: str) -> None:
    application = Application(id="app-1")

    with pytest.raises(ValueError):
        application.move_to(S.PARSING, actor=actor, reason=reason)

    assert application.state is S.RECEIVED
    assert application.history == ()


def test_the_audit_log_cannot_be_rewritten() -> None:
    application = Application(id="app-1")
    entry = application.move_to(S.PARSING, actor="worker", reason="picked up")

    with pytest.raises(FrozenInstanceError):
        entry.reason = "something nicer"  # type: ignore[misc]
    with pytest.raises(AttributeError):
        application.history.append(entry)  # type: ignore[attr-defined]


def test_state_cannot_be_set_directly() -> None:
    application = Application(id="app-1")

    with pytest.raises(AttributeError):
        application.state = S.DECIDED  # type: ignore[misc]


def test_a_given_time_is_kept_and_a_time_without_a_timezone_is_refused() -> None:
    application = Application(id="app-1")
    when = datetime(2026, 11, 5, 9, 30, tzinfo=UTC)

    assert application.move_to(S.PARSING, actor="worker", reason="picked up", at=when).at == when
    with pytest.raises(ValueError):
        application.move_to(
            S.EXTRACTING, actor="worker", reason="text saved", at=datetime(2026, 11, 5)
        )
    assert application.state is S.PARSING


def test_a_refused_move_says_what_was_asked() -> None:
    with pytest.raises(InvalidTransition) as refused:
        application_in(S.NEEDS_REVIEW_DECISION).move_to(S.SCORING, actor="x", reason="y")

    assert refused.value.from_state is S.NEEDS_REVIEW_DECISION
    assert refused.value.to_state is S.SCORING
    assert "NEEDS_REVIEW_DECISION" in str(refused.value)


# Data coming in from outside (the database, an API body) ---------------------------------------


def test_plain_strings_become_real_states() -> None:
    application = Application(id="app-1", state="EXTRACTING")  # type: ignore[arg-type]

    application.move_to("SCORING", actor="worker", reason="fields saved")  # type: ignore[arg-type]

    assert application.state is S.SCORING
    assert application.history[0].from_state is S.EXTRACTING
    assert application.history[0].to_state is S.SCORING


@pytest.mark.parametrize("bad", ["APPROVED", "received", ""])
def test_a_state_that_does_not_exist_is_refused(bad: str) -> None:
    with pytest.raises(ValueError):
        Application(id="app-1", state=bad)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        Application(id="app-1").move_to(bad, actor="x", reason="y")  # type: ignore[arg-type]


@pytest.mark.parametrize("bad_id", ["", "   "])
def test_an_application_needs_an_id(bad_id: str) -> None:
    with pytest.raises(ValueError):
        Application(id=bad_id)

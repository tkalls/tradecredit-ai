"""A loan application and the state machine that moves it through the pipeline.

An application is always in exactly one state. ALLOWED_TRANSITIONS is the whole map: a move it
doesn't list is refused. Every move that happens is appended to the application's history (the
audit log) with who made it, why, and when.

The three decisions behind the table (5 Nov 2026) are in docs/design.md section 6 and ADR-0001.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from types import MappingProxyType


class ApplicationState(StrEnum):
    """Where an application is right now."""

    RECEIVED = "RECEIVED"  # waiting: on the rail until a worker picks it up
    PARSING = "PARSING"  # working: the worker reads the files into clean text
    EXTRACTING = "EXTRACTING"  # working: Claude fills the extraction schema
    NEEDS_REVIEW_EXTRACTION = "NEEDS_REVIEW_EXTRACTION"  # waiting: a human checks a field
    SCORING = "SCORING"  # working: the scorecard runs (plain Python decides)
    DECIDING = "DECIDING"  # working: outcome plus a cited memo
    NEEDS_REVIEW_DECISION = "NEEDS_REVIEW_DECISION"  # waiting: a human makes the Refer call
    DECIDED = "DECIDED"  # finished: nothing moves after this
    FAILED = "FAILED"  # waiting: retries ran out, a human must act


_S = ApplicationState

# Read-only at runtime (MappingProxyType + frozenset), so no code can add a move while running.
ALLOWED_TRANSITIONS: Mapping[ApplicationState, frozenset[ApplicationState]] = MappingProxyType(
    {
        _S.RECEIVED: frozenset({_S.PARSING, _S.FAILED}),
        _S.PARSING: frozenset({_S.EXTRACTING, _S.FAILED}),
        _S.EXTRACTING: frozenset({_S.SCORING, _S.NEEDS_REVIEW_EXTRACTION, _S.FAILED}),
        _S.NEEDS_REVIEW_EXTRACTION: frozenset({_S.SCORING}),
        _S.SCORING: frozenset({_S.DECIDING, _S.FAILED}),
        _S.DECIDING: frozenset({_S.DECIDED, _S.NEEDS_REVIEW_DECISION, _S.FAILED}),
        _S.NEEDS_REVIEW_DECISION: frozenset({_S.DECIDED}),
        _S.DECIDED: frozenset(),
        _S.FAILED: frozenset({_S.RECEIVED}),
    }
)


class InvalidTransition(Exception):
    """Code asked for a move that ALLOWED_TRANSITIONS doesn't list."""

    def __init__(self, from_state: ApplicationState, to_state: ApplicationState) -> None:
        super().__init__(f"cannot move from {from_state} to {to_state}")
        self.from_state = from_state
        self.to_state = to_state


@dataclass(frozen=True, slots=True)
class Transition:
    """One line of the audit log. Frozen, so once it is written it can't be changed."""

    from_state: ApplicationState
    to_state: ApplicationState
    actor: str
    reason: str
    at: datetime


class Application:
    """A borrower's application. The only way to change its state is move_to()."""

    def __init__(self, id: str, state: ApplicationState = ApplicationState.RECEIVED) -> None:
        if not id.strip():
            raise ValueError("an application needs an id")
        self.id = id
        # ApplicationState(...) turns a plain string from the database into the real enum,
        # and raises ValueError for a state that doesn't exist.
        self._state = ApplicationState(state)
        self._history: list[Transition] = []

    @property
    def state(self) -> ApplicationState:
        return self._state

    @property
    def history(self) -> tuple[Transition, ...]:
        # A tuple copy: callers can read the audit log but not append to it or edit it.
        return tuple(self._history)

    def move_to(
        self,
        to_state: ApplicationState,
        *,
        actor: str,
        reason: str,
        at: datetime | None = None,
    ) -> Transition:
        """Move to `to_state` if the table allows it, and write the move to the audit log.

        Every check runs before anything changes, so a refused move leaves no trace.
        """
        to_state = ApplicationState(to_state)
        if to_state not in ALLOWED_TRANSITIONS[self._state]:
            raise InvalidTransition(self._state, to_state)
        if not actor.strip() or not reason.strip():
            raise ValueError("every move needs an actor and a reason for the audit log")
        if at is not None and at.utcoffset() is None:
            raise ValueError("audit times must carry a timezone")

        entry = Transition(
            from_state=self._state,
            to_state=to_state,
            actor=actor,
            reason=reason,
            at=at if at is not None else datetime.now(UTC),
        )
        self._history.append(entry)
        self._state = to_state
        return entry

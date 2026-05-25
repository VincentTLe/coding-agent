"""Calendar scheduler over ``events.Event`` (IMPLEMENT THIS FILE).

Each method raises ``NotImplementedError``. Implement them per the docstrings
and ``test_scheduler.py``. You must READ ``events.py``: intervals are half-open
``[start, end)`` (adjacent events do NOT conflict), times are integer minutes,
and you should reuse ``Event.overlaps`` for conflict checks rather than
re-deriving the comparison. Conflicts raise the ``Conflict`` exception defined
in ``events.py``.
"""

from __future__ import annotations

from events import Conflict, Event


class Calendar:
    """Holds non-overlapping events on a single shared timeline."""

    def __init__(self) -> None:
        self.events: list[Event] = []

    def conflicts_with(self, candidate: Event) -> list:
        """Return the list of already-booked events that overlap ``candidate``.

        Order is by start time ascending. Does not modify the calendar. An
        event that merely touches ``candidate`` end-to-end is NOT a conflict
        (half-open intervals).
        """
        raise NotImplementedError

    def add(self, event: Event) -> None:
        """Add ``event`` to the calendar.

        If it overlaps any existing event, raise ``Conflict`` and leave the
        calendar unchanged. Otherwise store it. Adjacent (touching) events are
        allowed.
        """
        raise NotImplementedError

    def busy_intervals(self) -> list:
        """Return merged busy intervals as a sorted list of ``(start, end)``.

        Overlapping OR touching booked intervals are merged into one (e.g.
        [0,30) and [30,60) merge into (0, 60)). Returns ``[]`` for an empty
        calendar. The result is sorted by start.
        """
        raise NotImplementedError

    def is_free(self, start: int, end: int) -> bool:
        """True iff the half-open interval ``[start, end)`` overlaps no event.

        ``end`` must be > ``start`` (callers pass a valid interval).
        """
        raise NotImplementedError

    def find_free_slot(self, duration: int, after: int = 0, until: int | None = None) -> int | None:
        """Earliest start minute ``s >= after`` such that ``[s, s+duration)`` is
        free and (if ``until`` is given) ``s + duration <= until``.

        ``duration`` must be positive. Returns the start minute, or ``None`` if
        no such slot exists within the bound. The slot may begin exactly when an
        earlier event ends (half-open). When ``until`` is ``None`` there is no
        upper bound, so a slot always exists at or after the last busy interval.
        """
        raise NotImplementedError

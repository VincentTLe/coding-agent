"""Calendar event model (COMPLETE — do not modify).

`scheduler.py` reasons over these events. Read this file: times are integer
minutes, intervals are HALF-OPEN ``[start, end)`` (so an event ending at 60
does NOT conflict with one starting at 60), and construction validates the
interval. ``scheduler.py`` must reuse ``Event.overlaps`` rather than redo the
comparison.
"""

from __future__ import annotations

from dataclasses import dataclass


class SchedulingError(Exception):
    """Base class for scheduling errors."""


class InvalidEvent(SchedulingError):
    """Raised when an event's interval is not strictly positive."""


class Conflict(SchedulingError):
    """Raised when an event cannot be placed because it overlaps another."""


@dataclass(frozen=True)
class Event:
    """A booked interval on a single shared calendar.

    Times are integer MINUTES from some fixed origin (e.g. minutes past
    midnight). The interval is half-open ``[start, end)``: ``end`` is exclusive,
    so two events where one ends exactly when the other begins do NOT overlap.

    Construction requires ``end > start`` (a zero- or negative-length event is
    invalid) and both bounds non-negative.
    """

    name: str
    start: int
    end: int

    def __post_init__(self) -> None:
        if self.start < 0 or self.end < 0:
            raise InvalidEvent(f"times must be non-negative: {self.start}, {self.end}")
        if self.end <= self.start:
            raise InvalidEvent(f"end ({self.end}) must be after start ({self.start})")

    @property
    def duration(self) -> int:
        return self.end - self.start

    def overlaps(self, other: "Event") -> bool:
        """True iff the two half-open intervals share at least one minute."""
        return self.start < other.end and other.start < self.end

    def contains(self, minute: int) -> bool:
        """True iff ``minute`` falls inside the half-open interval."""
        return self.start <= minute < self.end

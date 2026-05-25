"""Reference solution for scheduler.py."""

from __future__ import annotations

from events import Conflict, Event


class Calendar:
    """Holds non-overlapping events on a single shared timeline."""

    def __init__(self) -> None:
        self.events: list[Event] = []

    def conflicts_with(self, candidate: Event) -> list:
        hits = [e for e in self.events if e.overlaps(candidate)]
        hits.sort(key=lambda e: e.start)
        return hits

    def add(self, event: Event) -> None:
        if self.conflicts_with(event):
            raise Conflict(f"{event.name} overlaps an existing event")
        self.events.append(event)

    def busy_intervals(self) -> list:
        if not self.events:
            return []
        intervals = sorted((e.start, e.end) for e in self.events)
        merged: list[tuple[int, int]] = [intervals[0]]
        for start, end in intervals[1:]:
            last_start, last_end = merged[-1]
            if start <= last_end:  # overlapping OR touching -> merge
                merged[-1] = (last_start, max(last_end, end))
            else:
                merged.append((start, end))
        return merged

    def is_free(self, start: int, end: int) -> bool:
        return all(not (start < e.end and e.start < end) for e in self.events)

    def find_free_slot(self, duration: int, after: int = 0, until: int | None = None) -> int | None:
        if duration <= 0:
            raise ValueError("duration must be positive")
        candidate = max(after, 0)
        # Walk merged busy blocks; push the candidate past any that would clash.
        for bstart, bend in self.busy_intervals():
            if bend <= candidate:
                continue  # entirely before our candidate
            # block starts at/after candidate: is there room before it?
            if bstart - candidate >= duration:
                break  # the gap [candidate, bstart) is big enough
            # not enough room before this block -> jump to its end
            candidate = max(candidate, bend)
        if until is not None and candidate + duration > until:
            return None
        return candidate

# multi_file_scheduler — Conflict detection & next free slot

## Goal
Implement the `Calendar` scheduler in `scheduler.py` so all tests in
`test_scheduler.py` pass.

The event model is already written for you in `events.py` (a frozen `Event`
dataclass and the `SchedulingError`/`InvalidEvent`/`Conflict` exceptions). You
MUST read `events.py` to implement `scheduler.py` correctly — times are
integer minutes, intervals are **half-open** `[start, end)` (so an event
ending at 60 does NOT conflict with one starting at 60), and you should reuse
`Event.overlaps` for conflict checks.

Implement these `Calendar` methods (full specs are in the docstrings):

- `conflicts_with(candidate)` — list of booked events overlapping `candidate`,
  sorted by start; touching events do not count.
- `add(event)` — store the event, or raise `Conflict` (leaving the calendar
  unchanged) if it overlaps an existing one. Adjacent events are allowed.
- `busy_intervals()` — merged busy `(start, end)` tuples, sorted; overlapping
  OR touching intervals merge (e.g. `[0,30)` and `[30,60)` -> `(0,60)`).
- `is_free(start, end)` — True iff `[start, end)` overlaps no event.
- `find_free_slot(duration, after=0, until=None)` — earliest start `s >= after`
  where `[s, s+duration)` is free and (if `until` is given) `s + duration <=
  until`; return the start minute or `None`. `duration` must be positive.

Example:

```python
c = Calendar()
c.add(Event("a", 0, 60))
c.add(Event("b", 120, 180))
c.find_free_slot(60, after=0)   # 60  (the gap [60,120) fits exactly)
c.is_free(60, 120)              # True
c.busy_intervals()             # [(0, 60), (120, 180)]
```

## Category
multi_file

## Difficulty
hard

## Tests
visible

## Source/License
Authored for coding-agent eval. MIT.

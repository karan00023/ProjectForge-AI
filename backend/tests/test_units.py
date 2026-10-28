"""Pure unit tests for deterministic engines (no database)."""

import uuid
from datetime import date

import pytest

from app.services.calendar import add_working_days, working_days_between
from app.services.graph import cycle_if_added, find_path


@pytest.mark.parametrize(
    ("start", "end", "expected"),
    [
        (date(2026, 6, 15), date(2026, 6, 15), 0),  # Mon → Mon
        (date(2026, 6, 15), date(2026, 6, 16), 1),  # Mon → Tue
        (date(2026, 6, 19), date(2026, 6, 22), 1),  # Fri → Mon (weekend skipped)
        (date(2026, 6, 15), date(2026, 6, 22), 5),  # one week
        (date(2026, 6, 15), date(2026, 6, 29), 10),  # two weeks
        (date(2026, 6, 20), date(2026, 6, 21), 0),  # Sat → Sun
        (date(2026, 6, 22), date(2026, 6, 15), -5),  # negative direction
    ],
)
def test_working_days_between(start: date, end: date, expected: int) -> None:
    assert working_days_between(start, end) == expected


def test_add_working_days_round_trips() -> None:
    start = date(2026, 6, 18)  # Thursday
    for n in range(-15, 16):
        assert working_days_between(start, add_working_days(start, n)) == n


def test_find_path_and_cycle_detection() -> None:
    a, b, c, d = (uuid.uuid4() for _ in range(4))
    edges = [(a, b), (b, c)]
    assert find_path(edges, a, c) == [a, b, c]
    assert find_path(edges, c, a) is None
    # Adding c → a closes a → b → c → a.
    assert cycle_if_added(edges, c, a) == [c, a, b, c]
    # Adding a → d or d → a is safe.
    assert cycle_if_added(edges, a, d) is None
    assert cycle_if_added(edges, d, a) is None

"""Working-day arithmetic (Mon–Fri). Org calendars and holidays are backlog item CORE-12."""

from datetime import date, timedelta


def working_days_between(start: date, end: date) -> int:
    """Signed count of working days moving from `start` to `end` (end exclusive of start).

    working_days_between(Fri, next Mon) == 1; reversed arguments give the negative.
    """
    if start == end:
        return 0
    sign = 1
    if end < start:
        start, end = end, start
        sign = -1
    days = (end - start).days
    full_weeks, extra = divmod(days, 7)
    count = full_weeks * 5
    weekday = start.weekday()
    for i in range(1, extra + 1):
        if (weekday + i) % 7 < 5:
            count += 1
    return sign * count


def add_working_days(start: date, n: int) -> date:
    step = 1 if n >= 0 else -1
    current = start
    remaining = abs(n)
    while remaining:
        current += timedelta(days=step)
        if current.weekday() < 5:
            remaining -= 1
    return current

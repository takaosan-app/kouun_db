from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True, slots=True)
class DateRange:
    start: date
    end: date


def split_into_months(
    start_date: date,
    end_date: date,
) -> tuple[DateRange, ...]:
    if start_date > end_date:
        raise ValueError(
            "start_date must not be later than end_date."
        )

    ranges: list[DateRange] = []
    current = start_date

    while current <= end_date:
        last_day = monthrange(
            current.year,
            current.month,
        )[1]
        end_of_month = date(
            current.year,
            current.month,
            last_day,
        )
        range_end = min(end_of_month, end_date)

        ranges.append(
            DateRange(
                start=current,
                end=range_end,
            )
        )
        current = range_end + timedelta(days=1)

    return tuple(ranges)

from datetime import date

import pytest

from schedule import (
    format_date_range,
    format_date_with_weekday,
    get_monday_of_week,
    get_monday_to_sunday_after_next,
    get_seven_days_from,
)


@pytest.mark.parametrize(
    ("day", "expected_monday"),
    [
        pytest.param(date(2026, 10, 26), date(2026, 10, 26), id="monday"),
        pytest.param(date(2026, 11, 1), date(2026, 10, 26), id="sunday_across_month"),
        pytest.param(date(2026, 11, 5), date(2026, 11, 2), id="different_week"),
    ],
)
def test_get_monday_of_week_returns_monday_of_same_week(
    day: date, expected_monday: date
) -> None:
    assert get_monday_of_week(day) == expected_monday


def test_get_seven_days_from_returns_consecutive_days_including_start() -> None:
    assert get_seven_days_from(date(2026, 10, 26)) == [
        date(2026, 10, 26),
        date(2026, 10, 27),
        date(2026, 10, 28),
        date(2026, 10, 29),
        date(2026, 10, 30),
        date(2026, 10, 31),
        date(2026, 11, 1),
    ]


@pytest.mark.parametrize(
    "day",
    [
        pytest.param(date(2026, 10, 26), id="monday"),
        pytest.param(date(2026, 11, 1), id="sunday"),
    ],
)
def test_get_monday_to_sunday_after_next_returns_same_result_for_any_day_in_week(
    day: date,
) -> None:
    assert get_monday_to_sunday_after_next(day) == [
        date(2026, 11, 9),
        date(2026, 11, 10),
        date(2026, 11, 11),
        date(2026, 11, 12),
        date(2026, 11, 13),
        date(2026, 11, 14),
        date(2026, 11, 15),
    ]


@pytest.mark.parametrize(
    ("day", "expected_label"),
    [
        pytest.param(date(2026, 11, 23), "11/23 (月)", id="monday"),
        pytest.param(date(2027, 1, 3), "1/3 (日)", id="sunday_single_digits"),
    ],
)
def test_format_date_with_weekday_returns_unpadded_date_and_japanese_weekday(
    day: date, expected_label: str
) -> None:
    assert format_date_with_weekday(day) == expected_label


@pytest.mark.parametrize(
    ("start", "end", "expected_label"),
    [
        pytest.param(
            date(2026, 11, 23), date(2026, 11, 29), "11/23-29", id="in_same_month"
        ),
        pytest.param(
            date(2026, 11, 30), date(2026, 12, 6), "11/30-12/6", id="across_months"
        ),
    ],
)
def test_format_date_range_shows_end_month_only_when_different(
    start: date, end: date, expected_label: str
) -> None:
    assert format_date_range(start, end) == expected_label

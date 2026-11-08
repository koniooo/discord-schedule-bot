from datetime import date

import pytest

from schedule import get_monday_of_week, get_seven_days_from


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

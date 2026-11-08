from datetime import date

import pytest

from schedule import get_monday_of_week


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

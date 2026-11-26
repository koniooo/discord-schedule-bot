from datetime import date

import pytest

from schedule import (
    format_date_range,
    format_date_with_weekday,
    get_monday_of_week,
    get_nearest_monday,
    get_seven_days_from,
    get_week_after_nearest_monday,
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
    ("day", "expected_monday"),
    [
        pytest.param(date(2026, 11, 23), date(2026, 11, 23), id="monday_itself"),
        # Thursday is 3 days after Monday and 4 days before the next one.
        pytest.param(date(2026, 11, 26), date(2026, 11, 23), id="thursday"),
        pytest.param(date(2026, 11, 27), date(2026, 11, 30), id="friday"),
        pytest.param(date(2026, 11, 29), date(2026, 11, 30), id="sunday_next_monday"),
        pytest.param(date(2026, 12, 31), date(2026, 12, 28), id="thursday_across_year"),
    ],
)
def test_get_nearest_monday_picks_this_weeks_monday_until_thursday(
    day: date, expected_monday: date
) -> None:
    assert get_nearest_monday(day) == expected_monday


# The vote may be posted on Sunday, Monday or Tuesday; each gives the week
# that starts on the coming Monday 11/30.
@pytest.mark.parametrize(
    "day",
    [
        pytest.param(date(2026, 11, 22), id="sunday"),
        pytest.param(date(2026, 11, 23), id="monday"),
        pytest.param(date(2026, 11, 24), id="tuesday"),
    ],
)
def test_get_week_after_nearest_monday_starts_on_coming_monday_from_sunday_to_tuesday(
    day: date,
) -> None:
    assert get_week_after_nearest_monday(day) == [
        date(2026, 11, 30),
        date(2026, 12, 1),
        date(2026, 12, 2),
        date(2026, 12, 3),
        date(2026, 12, 4),
        date(2026, 12, 5),
        date(2026, 12, 6),
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

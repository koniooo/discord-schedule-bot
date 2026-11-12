from datetime import date

from schedule import format_date_with_weekday
from vote import NO_AVAILABLE_DAY_TEXT, build_poll_answers


def test_build_poll_answers_returns_day_answers_followed_by_no_available_day() -> None:
    monday = date(2026, 11, 23)
    tuesday = date(2026, 11, 24)

    assert build_poll_answers([monday, tuesday]) == [
        {"poll_media": {"text": format_date_with_weekday(monday)}},
        {"poll_media": {"text": format_date_with_weekday(tuesday)}},
        {"poll_media": {"text": NO_AVAILABLE_DAY_TEXT}},
    ]

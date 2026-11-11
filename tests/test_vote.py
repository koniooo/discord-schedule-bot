from datetime import date

from vote import NO_AVAILABLE_DAY_TEXT, build_poll_answers


def test_build_poll_answers_returns_day_answers_followed_by_no_available_day() -> None:
    assert build_poll_answers([date(2026, 11, 23), date(2026, 11, 24)]) == [
        {"poll_media": {"text": "11/23 (月)"}},
        {"poll_media": {"text": "11/24 (火)"}},
        {"poll_media": {"text": NO_AVAILABLE_DAY_TEXT}},
    ]

from datetime import date

from schedule import format_date_range, format_date_with_weekday
from vote import (
    COMMENT_THREAD_NAME_SUFFIX,
    NO_AVAILABLE_DAY_TEXT,
    POLL_QUESTION_TEXT,
    VOTE_ANNOUNCEMENT_TEXT,
    VOTE_DURATION_HOURS,
    build_poll_answers,
    build_vote_message,
    format_comment_thread_name,
)


def test_build_poll_answers_returns_day_answers_followed_by_no_available_day() -> None:
    monday = date(2026, 11, 23)
    tuesday = date(2026, 11, 24)

    assert build_poll_answers([monday, tuesday]) == [
        {"poll_media": {"text": format_date_with_weekday(monday)}},
        {"poll_media": {"text": format_date_with_weekday(tuesday)}},
        {"poll_media": {"text": NO_AVAILABLE_DAY_TEXT}},
    ]


def test_build_vote_message_announces_vote_to_everyone() -> None:
    vote_message = build_vote_message([date(2026, 11, 12)])

    assert VOTE_ANNOUNCEMENT_TEXT in vote_message["content"]
    assert "@everyone" in vote_message["content"]
    assert vote_message["allowed_mentions"] == {"parse": ["everyone"]}


def test_build_vote_message_builds_poll_from_candidate_days() -> None:
    candidate_days = [date(2026, 11, 12), date(2026, 11, 13)]

    assert build_vote_message(candidate_days)["poll"] == {
        "question": {"text": POLL_QUESTION_TEXT},
        "answers": build_poll_answers(candidate_days),
        "duration": VOTE_DURATION_HOURS,
        "allow_multiselect": True,
    }


def test_format_comment_thread_name_shows_date_range_and_suffix() -> None:
    first_day = date(2026, 11, 30)
    last_day = date(2026, 12, 6)
    assert (
        format_comment_thread_name(
            [
                first_day,
                date(2026, 12, 1),
                last_day,
            ]
        )
        == f"{format_date_range(first_day, last_day)} {COMMENT_THREAD_NAME_SUFFIX}"
    )

from datetime import date

from vote import (
    VOTE_ANNOUNCEMENT_TEXT,
    build_poll_answers,
    build_vote_message,
    format_comment_thread_name,
)


def test_build_poll_answers_returns_day_answers_followed_by_no_available_day() -> None:
    assert build_poll_answers([date(2026, 11, 23), date(2026, 11, 24)]) == [
        {"poll_media": {"text": "11/23 (月)"}},
        {"poll_media": {"text": "11/24 (火)"}},
        {"poll_media": {"text": "どの日も難しい"}},
    ]


def test_build_vote_message_announces_vote_to_everyone() -> None:
    vote_message = build_vote_message([date(2026, 11, 12)])

    assert VOTE_ANNOUNCEMENT_TEXT in vote_message["content"]
    assert "@everyone" in vote_message["content"]
    assert vote_message["allowed_mentions"] == {"parse": ["everyone"]}


def test_build_vote_message_builds_poll_from_candidate_days() -> None:
    candidate_days = [date(2026, 11, 12), date(2026, 11, 13)]

    assert build_vote_message(candidate_days)["poll"] == {
        "question": {"text": "参加可能日 (22:00～23:30)"},
        "answers": build_poll_answers(candidate_days),
        "duration": 168,
        "allow_multiselect": True,
    }


def test_format_comment_thread_name_shows_date_range_and_suffix() -> None:
    assert (
        format_comment_thread_name(
            [date(2026, 11, 30), date(2026, 12, 1), date(2026, 12, 6)]
        )
        == "11/30-12/6 💬コメント"
    )

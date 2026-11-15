from datetime import date

import pytest

from discord_api import AnswerId, Message, MessageId, User, UserId
from vote import (
    VOTE_ANNOUNCEMENT_TEXT,
    build_poll_answers,
    build_vote_message,
    collect_voter_ids,
    find_latest_vote_message,
    format_comment_thread_name,
)

BOT_ID = UserId("4000")
OTHER_USER_ID = UserId("4001")


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


def make_message(message_id: str, author_id: UserId, *, has_poll: bool) -> Message:
    message: Message = {
        "id": MessageId(message_id),
        "author": {"id": author_id},
    }
    if has_poll:
        message["poll"] = {
            "answers": [
                {"poll_media": {"text": "11/16 (月)"}, "answer_id": AnswerId(1)},
                {"poll_media": {"text": "11/17 (火)"}, "answer_id": AnswerId(2)},
            ]
        }
    return message


def test_find_latest_vote_message_returns_vote_message_in_typical_channel() -> None:
    vote_message = make_message("3002", BOT_ID, has_poll=True)
    messages = [
        make_message("3003", OTHER_USER_ID, has_poll=False),
        vote_message,
        make_message("3001", BOT_ID, has_poll=True),
    ]

    assert find_latest_vote_message(messages, BOT_ID) == vote_message


def test_find_latest_vote_message_ignores_bot_message_without_poll() -> None:
    vote_message = make_message("3002", BOT_ID, has_poll=True)
    messages = [
        make_message("3003", BOT_ID, has_poll=False),
        vote_message,
        make_message("3001", BOT_ID, has_poll=True),
    ]

    assert find_latest_vote_message(messages, BOT_ID) == vote_message


def test_find_latest_vote_message_ignores_poll_posted_by_other_user() -> None:
    vote_message = make_message("3002", BOT_ID, has_poll=True)
    messages = [
        make_message("3003", OTHER_USER_ID, has_poll=True),
        vote_message,
        make_message("3001", BOT_ID, has_poll=True),
    ]

    assert find_latest_vote_message(messages, BOT_ID) == vote_message


def test_find_latest_vote_message_ignores_order() -> None:
    vote_message = make_message("3003", BOT_ID, has_poll=True)
    messages = [
        make_message("3002", BOT_ID, has_poll=True),
        vote_message,
        make_message("3001", BOT_ID, has_poll=True),
    ]

    assert find_latest_vote_message(messages, BOT_ID) == vote_message


def test_find_latest_vote_message_compares_message_ids_as_numbers() -> None:
    vote_message = make_message("30000", BOT_ID, has_poll=True)
    messages = [
        vote_message,
        make_message("3999", BOT_ID, has_poll=True),
    ]

    assert find_latest_vote_message(messages, BOT_ID) == vote_message


def test_find_latest_vote_message_returns_none_without_vote_message() -> None:
    messages = [
        make_message("3003", BOT_ID, has_poll=False),
        make_message("3002", OTHER_USER_ID, has_poll=True),
        make_message("3001", BOT_ID, has_poll=False),
    ]

    assert find_latest_vote_message(messages, BOT_ID) is None


@pytest.mark.parametrize(
    ("voters_per_answer", "expected"),
    [
        pytest.param(
            [
                [{"id": "4001"}],
                [],
                [{"id": "4002"}],
            ],
            {"4001", "4002"},
            id="users_in_different_answers",
        ),
        pytest.param(
            [
                [{"id": "4001"}, {"id": "4002"}],
                [{"id": "4002"}],
            ],
            {"4001", "4002"},
            id="same_user_in_multiple_answers",
        ),
        pytest.param([list[User](), list[User]()], set[UserId](), id="no_voters"),
    ],
)
def test_collect_voter_ids_returns_ids_of_all_voters(
    voters_per_answer: list[list[User]], expected: set[UserId]
) -> None:
    assert collect_voter_ids(voters_per_answer) == expected

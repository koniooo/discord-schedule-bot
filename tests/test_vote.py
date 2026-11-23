from datetime import UTC, date, datetime

import pytest

from discord_api import (
    AnswerId,
    ChannelId,
    GuildId,
    GuildMember,
    Message,
    MessageId,
    PollResponse,
    Reaction,
    User,
    UserId,
)
from vote import (
    VOTE_ANNOUNCEMENT_TEXT,
    build_all_voted_report_message,
    build_dm_reminder_message,
    build_poll_answers,
    build_vote_channel_reminder_message,
    build_vote_message,
    collect_human_non_voters,
    collect_voter_ids,
    find_latest_vote_message,
    format_comment_thread_name,
    get_display_name,
    get_poll_expires_at,
    has_own_reaction,
    is_human,
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


def test_build_vote_message_builds_poll_from_candidate_days() -> None:
    candidate_days = [date(2026, 11, 12), date(2026, 11, 13)]

    assert build_vote_message(candidate_days).get("poll") == {
        "question": {"text": "参加可能日 (22:00～23:30)"},
        "answers": build_poll_answers(candidate_days),
        "duration": 48,
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
            ],
            "expiry": "2026-11-18T03:00:00+00:00",
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


@pytest.mark.parametrize(
    ("members", "voter_ids", "expected"),
    [
        pytest.param(
            [
                {"user": {"id": "4000", "bot": True}},
                {"user": {"id": "4001"}},
                {"user": {"id": "4002"}},
                {"user": {"id": "4003"}},
            ],
            {"4002"},
            [
                {"user": {"id": "4001"}},
                {"user": {"id": "4003"}},
            ],
            id="ignores_bot",
        ),
        pytest.param(
            [
                {"user": {"id": "4000", "bot": True}},
                {"user": {"id": "4001"}},
                {"user": {"id": "4002"}},
                {"user": {"id": "4003"}},
            ],
            {"4001", "4002", "4003"},
            [],
            id="every_member_voted",
        ),
        pytest.param(
            [
                {"user": {"id": "4003"}},
                {"user": {"id": "4000", "bot": True}},
                {"user": {"id": "4001"}},
                {"user": {"id": "4002"}},
            ],
            {"4002"},
            [
                {"user": {"id": "4003"}},
                {"user": {"id": "4001"}},
            ],
            id="keeps_member_order",
        ),
    ],
)
def test_collect_human_non_voters_excludes_bots_and_voters(
    members: list[GuildMember], voter_ids: set[UserId], expected: list[GuildMember]
) -> None:
    assert collect_human_non_voters(members, voter_ids) == expected


@pytest.mark.parametrize(
    ("reactions", "expected"),
    [
        pytest.param(
            [Reaction(me=True, emoji={"name": "✅"})], True, id="own_matching_emoji"
        ),
        pytest.param(
            [Reaction(me=True, emoji={"name": "👍"})], False, id="own_other_emoji"
        ),
        pytest.param(
            [Reaction(me=False, emoji={"name": "✅"})],
            False,
            id="others_matching_emoji",
        ),
        pytest.param(
            [
                Reaction(me=False, emoji={"name": "👍"}),
                Reaction(me=True, emoji={"name": "✅"}),
            ],
            True,
            id="own_matching_emoji_after_others",
        ),
    ],
)
def test_has_own_reaction_returns_whether_bot_reacted_with_emoji(
    reactions: list[Reaction], expected: bool
) -> None:
    message = Message(
        id=MessageId("3000"),
        author={"id": BOT_ID},
        reactions=reactions,
    )
    assert has_own_reaction(message, "✅") == expected


def test_has_own_reaction_returns_false_without_reactions() -> None:
    message = Message(id=MessageId("3000"), author={"id": BOT_ID})
    assert has_own_reaction(message, "✅") is False


def test_build_all_voted_report_message_shows_count_link_and_jst_deadline() -> None:
    assert build_all_voted_report_message(
        8,
        GuildId("1001"),
        ChannelId("3000"),
        datetime(2026, 11, 24, 3, 0, tzinfo=UTC),
    ) == {
        "content": (
            "8人全員が投票したクポ～\n"
            "https://discord.com/channels/1001/3000\n"
            "\n"
            "ただ11/24 (火)の12時までは投票し直せるから気をつけてクポ～"
        )
    }


def test_get_poll_expires_at_returns_expiry_as_aware_datetime() -> None:
    poll = PollResponse(answers=[], expiry="2026-11-24T03:00:00.123000+00:00")
    assert get_poll_expires_at(poll) == datetime(
        2026, 11, 24, 3, 0, 0, 123000, tzinfo=UTC
    )


def test_get_poll_expires_at_raises_when_poll_has_no_expiry() -> None:
    poll = PollResponse(answers=[], expiry=None)
    with pytest.raises(ValueError, match="expiry"):
        get_poll_expires_at(poll)


@pytest.mark.parametrize(
    ("guild_member", "expected"),
    [
        pytest.param(
            GuildMember(user=User(id=UserId("4001"))), True, id="bot_key_missing"
        ),
        pytest.param(
            GuildMember(user=User(id=UserId("4001"), bot=False)), True, id="bot_false"
        ),
        pytest.param(
            GuildMember(user=User(id=UserId("4000"), bot=True)), False, id="bot_true"
        ),
    ],
)
def test_is_human_returns_whether_member_is_human(
    guild_member: GuildMember, expected: bool
) -> None:
    assert is_human(guild_member) == expected


def test_build_dm_reminder_message_shows_jst_deadline_and_vote_link() -> None:
    assert build_dm_reminder_message(
        GuildId("1001"),
        ChannelId("2000"),
        MessageId("3000"),
        datetime(2026, 11, 24, 3, 0, tzinfo=UTC),
    ) == {
        "content": (
            "11/24 (火)の12時に投票を締め切るクポ～\n"
            "それまでにご投票お願いしますクポ。\n"
            "https://discord.com/channels/1001/2000/3000"
        )
    }


def test_build_vote_channel_reminder_message_replies_to_vote_message() -> None:
    assert build_vote_channel_reminder_message(
        MessageId("3000"),
        datetime(2026, 11, 24, 3, 0, tzinfo=UTC),
    ) == {
        "content": (
            "11/24 (火)の12時に投票を締め切るクポ～\nそれまでにご投票お願いしますクポ。"
        ),
        "message_reference": {"message_id": "3000"},
    }


@pytest.mark.parametrize(
    ("guild_member", "expected"),
    [
        pytest.param(
            GuildMember(
                nick="こにー",
                user=User(id=UserId("4001"), global_name="こにお", username="cony"),
            ),
            "こにー",
            id="nickname",
        ),
        pytest.param(
            GuildMember(
                nick=None,
                user=User(id=UserId("4001"), global_name="こにお", username="cony"),
            ),
            "こにお",
            id="global_name",
        ),
        pytest.param(
            GuildMember(
                nick=None,
                user=User(id=UserId("4001"), global_name=None, username="cony"),
            ),
            "cony",
            id="username",
        ),
        # Discord leaves out "nick" for members without one, so missing keys
        # must be skipped like None values.
        pytest.param(
            GuildMember(user=User(id=UserId("4001"), username="cony")),
            "cony",
            id="username_when_nick_and_global_name_are_missing",
        ),
        pytest.param(
            GuildMember(nick=None, user=User(id=UserId("4001"), global_name=None)),
            "4001",
            id="user_id",
        ),
    ],
)
def test_get_display_name_prefers_nick_then_global_name_then_username(
    guild_member: GuildMember, expected: str
) -> None:
    assert get_display_name(guild_member) == expected

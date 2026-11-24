import logging
from datetime import UTC, date, datetime, timedelta
from typing import TypedDict

import pytest

import jobs
from discord_api import (
    AnswerId,
    AutoArchiveDuration,
    Channel,
    ChannelId,
    DiscordApiError,
    GuildId,
    GuildMember,
    Message,
    MessageCreateRequest,
    MessageId,
    Reaction,
    User,
    UserId,
)
from jobs import report_if_all_voted, send_reminders, start_vote
from schedule import get_monday_to_sunday_after_next
from vote import build_vote_message


def test_start_vote_posts_vote_message_and_starts_comment_thread(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    class PostMessageCall(TypedDict):
        channel_id: ChannelId
        body: MessageCreateRequest

    class StartThreadFromMessageCall(TypedDict):
        channel_id: ChannelId
        message_id: MessageId
        name: str
        auto_archive_duration: AutoArchiveDuration

    post_message_calls: list[PostMessageCall] = []
    start_thread_from_message_calls: list[StartThreadFromMessageCall] = []
    vote_message_id = MessageId("3000")
    vote_channel_id = ChannelId("2000")
    today = date(2026, 11, 16)

    def fake_post_message(
        _token: str, channel_id: ChannelId, body: MessageCreateRequest
    ) -> Message:
        post_message_calls.append({"channel_id": channel_id, "body": body})
        return {"id": vote_message_id, "author": {"id": UserId("")}}

    def fake_start_thread_from_message(
        _token: str,
        channel_id: ChannelId,
        message_id: MessageId,
        name: str,
        auto_archive_duration: AutoArchiveDuration,
    ) -> Channel:
        start_thread_from_message_calls.append(
            {
                "channel_id": channel_id,
                "message_id": message_id,
                "name": name,
                "auto_archive_duration": auto_archive_duration,
            }
        )
        return {"id": ChannelId("")}

    monkeypatch.setattr(jobs, "post_message", fake_post_message)
    monkeypatch.setattr(
        jobs, "start_thread_from_message", fake_start_thread_from_message
    )
    caplog.set_level(logging.INFO, logger="jobs")

    start_vote("dummy-token", vote_channel_id, today)

    candidate_days = get_monday_to_sunday_after_next(today)
    assert len(post_message_calls) == 1
    post_message_call = post_message_calls[0]
    assert post_message_call["channel_id"] == vote_channel_id
    assert post_message_call["body"] == build_vote_message(candidate_days)

    assert len(start_thread_from_message_calls) == 1
    start_thread_from_message_call = start_thread_from_message_calls[0]
    assert start_thread_from_message_call["channel_id"] == vote_channel_id
    assert start_thread_from_message_call["message_id"] == vote_message_id
    assert start_thread_from_message_call["name"] == "11/30-12/6 💬コメント"
    assert start_thread_from_message_call["auto_archive_duration"] == 10080

    assert caplog.messages == [
        "Vote 3000 (11/30-12/6): posted",
        "Vote 3000 (11/30-12/6): started thread '11/30-12/6 💬コメント'",
    ]


type Call = tuple[object, ...]

# Tue 11/24 12:00 JST. Every vote message from make_vote_message closes at this time.
POLL_EXPIRES_AT = datetime(2026, 11, 24, 3, 0, tzinfo=UTC)


def make_discord_api_error(
    status: int, reason: str, discord_code: int | None, message: str | None
) -> DiscordApiError:
    return DiscordApiError(
        method="POST",
        path="/api/v10/x",
        status=status,
        reason=reason,
        discord_code=discord_code,
        message=message,
        body=b"",
    )


def make_vote_message(
    *, reactions: list[Reaction] | None = None, has_thread: bool = True
) -> Message:
    vote_message: Message = {
        "id": MessageId("3000"),
        "author": {"id": UserId("4000"), "bot": True},
        "poll": {
            "answers": [
                {"answer_id": AnswerId(1), "poll_media": {"text": "11/30 (月)"}},
                {"answer_id": AnswerId(2), "poll_media": {"text": "どの日も難しい"}},
            ],
            "expiry": POLL_EXPIRES_AT.isoformat(),
        },
    }
    if reactions is not None:
        vote_message["reactions"] = reactions
    if has_thread:
        vote_message["thread"] = {
            "name": "11/30-12/6 💬コメント",
            "thread_metadata": {"archived": False, "locked": False},
        }
    return vote_message


class FakeDiscord:
    """Replaces the Discord API functions used by jobs and records every call."""

    def __init__(self) -> None:
        self.calls: list[Call] = []
        self.posted_messages: list[tuple[ChannelId, MessageCreateRequest]] = []
        self.messages: list[Message] = [make_vote_message()]
        self.voters_by_answer_id: dict[AnswerId, list[User]] = {}
        self.members: list[GuildMember] = [
            {"user": {"id": UserId("4000"), "bot": True}},
            # Names let the tests check that logs show display names, not ids.
            # 4001's nick differs from the username, so the logs must use the nick.
            {"nick": "Alice", "user": {"id": UserId("4001"), "username": "alice"}},
            {"user": {"id": UserId("4002"), "username": "bob"}},
        ]
        # One DM channel per user, so a test can make the DM to one user fail.
        self.dm_channel_ids: dict[UserId, ChannelId] = {
            UserId("4001"): ChannelId("2101"),
            UserId("4002"): ChannelId("2102"),
            UserId("4003"): ChannelId("2001"),
        }
        self.post_message_errors: dict[ChannelId, Exception] = {}

    def get_channel_messages(self, _token: str, channel_id: ChannelId) -> list[Message]:
        self.calls.append(("get_channel_messages", channel_id))
        return self.messages

    def get_current_user(self, _token: str) -> User:
        self.calls.append(("get_current_user",))
        return {"id": UserId("4000"), "bot": True}

    def get_answer_voters(
        self,
        _token: str,
        channel_id: ChannelId,
        message_id: MessageId,
        answer_id: AnswerId,
    ) -> list[User]:
        self.calls.append(("get_answer_voters", channel_id, message_id, answer_id))
        return self.voters_by_answer_id.get(answer_id, [])

    def list_guild_members(self, _token: str, guild_id: GuildId) -> list[GuildMember]:
        self.calls.append(("list_guild_members", guild_id))
        return self.members

    def create_dm_channel(self, _token: str, recipient_id: UserId) -> Channel:
        self.calls.append(("create_dm_channel", recipient_id))
        return {"id": self.dm_channel_ids[recipient_id]}

    def post_message(
        self, _token: str, channel_id: ChannelId, body: MessageCreateRequest
    ) -> Message:
        self.calls.append(("post_message", channel_id))
        if channel_id in self.post_message_errors:
            raise self.post_message_errors[channel_id]
        self.posted_messages.append((channel_id, body))
        return {"id": MessageId("3001"), "author": {"id": UserId("4000")}}

    def add_reaction(
        self, _token: str, channel_id: ChannelId, message_id: MessageId, emoji: str
    ) -> None:
        self.calls.append(("add_reaction", channel_id, message_id, emoji))

    def call_names(self) -> list[object]:
        return [call[0] for call in self.calls]


@pytest.fixture
def fake_discord(monkeypatch: pytest.MonkeyPatch) -> FakeDiscord:
    fake = FakeDiscord()
    monkeypatch.setattr(jobs, "get_channel_messages", fake.get_channel_messages)
    monkeypatch.setattr(jobs, "get_current_user", fake.get_current_user)
    monkeypatch.setattr(jobs, "get_answer_voters", fake.get_answer_voters)
    monkeypatch.setattr(jobs, "list_guild_members", fake.list_guild_members)
    monkeypatch.setattr(jobs, "create_dm_channel", fake.create_dm_channel)
    monkeypatch.setattr(jobs, "post_message", fake.post_message)
    monkeypatch.setattr(jobs, "add_reaction", fake.add_reaction)
    return fake


def run_report_if_all_voted(now: datetime) -> None:
    report_if_all_voted(
        "dummy-token", GuildId("1001"), ChannelId("2000"), UserId("4003"), now
    )


def test_report_if_all_voted_dms_master_then_marks_vote_when_everyone_voted(
    fake_discord: FakeDiscord, caplog: pytest.LogCaptureFixture
) -> None:
    fake_discord.voters_by_answer_id = {
        AnswerId(1): [{"id": UserId("4001")}],
        AnswerId(2): [{"id": UserId("4002")}],
    }
    caplog.set_level(logging.INFO, logger="jobs")

    run_report_if_all_voted(POLL_EXPIRES_AT - timedelta(days=1))

    assert fake_discord.calls == [
        ("get_channel_messages", "2000"),
        ("get_current_user",),
        ("get_answer_voters", "2000", "3000", 1),
        ("get_answer_voters", "2000", "3000", 2),
        ("list_guild_members", "1001"),
        ("create_dm_channel", "4003"),
        ("post_message", "2001"),
        ("add_reaction", "2000", "3000", "✅"),
    ]
    assert len(fake_discord.posted_messages) == 1
    report_content = fake_discord.posted_messages[0][1]["content"]
    # Two humans: the bot member must not be counted.
    assert report_content.startswith("2人全員が投票した")
    assert "https://discord.com/channels/1001/3000" in report_content
    assert caplog.messages == [
        "Vote 3000 (11/30-12/6): 2/2 members have voted",
        "Vote 3000 (11/30-12/6): sent the all-voted report to the master",
    ]


def test_report_if_all_voted_does_not_report_while_someone_has_not_voted(
    fake_discord: FakeDiscord,
) -> None:
    fake_discord.voters_by_answer_id = {AnswerId(1): [{"id": UserId("4001")}]}

    run_report_if_all_voted(POLL_EXPIRES_AT - timedelta(days=1))

    assert fake_discord.call_names() == [
        "get_channel_messages",
        "get_current_user",
        "get_answer_voters",
        "get_answer_voters",
        "list_guild_members",
    ]


def test_report_if_all_voted_logs_how_many_human_members_have_voted(
    fake_discord: FakeDiscord, caplog: pytest.LogCaptureFixture
) -> None:
    fake_discord.voters_by_answer_id = {AnswerId(1): [{"id": UserId("4001")}]}
    caplog.set_level(logging.INFO, logger="jobs")

    run_report_if_all_voted(POLL_EXPIRES_AT - timedelta(days=1))

    assert "Vote 3000 (11/30-12/6): 1/2 members have voted" in caplog.messages


def test_report_if_all_voted_still_reports_without_thread(
    fake_discord: FakeDiscord, caplog: pytest.LogCaptureFixture
) -> None:
    fake_discord.messages = [make_vote_message(has_thread=False)]
    fake_discord.voters_by_answer_id = {
        AnswerId(1): [{"id": UserId("4001")}, {"id": UserId("4002")}]
    }
    caplog.set_level(logging.INFO, logger="jobs")

    run_report_if_all_voted(POLL_EXPIRES_AT - timedelta(days=1))

    assert "Vote 3000 (no thread): 2/2 members have voted" in caplog.messages
    assert fake_discord.call_names()[-3:] == [
        "create_dm_channel",
        "post_message",
        "add_reaction",
    ]


def test_report_if_all_voted_does_nothing_when_already_reported(
    fake_discord: FakeDiscord, caplog: pytest.LogCaptureFixture
) -> None:
    fake_discord.messages = [
        make_vote_message(reactions=[{"me": True, "emoji": {"name": "✅"}}])
    ]
    fake_discord.voters_by_answer_id = {
        AnswerId(1): [{"id": UserId("4001")}, {"id": UserId("4002")}]
    }
    caplog.set_level(logging.DEBUG, logger="jobs")

    run_report_if_all_voted(POLL_EXPIRES_AT - timedelta(days=1))

    assert fake_discord.call_names() == ["get_channel_messages", "get_current_user"]
    assert caplog.messages == ["Vote 3000 (11/30-12/6): already reported"]


def test_report_if_all_voted_does_nothing_at_poll_expiry(
    fake_discord: FakeDiscord, caplog: pytest.LogCaptureFixture
) -> None:
    fake_discord.voters_by_answer_id = {
        AnswerId(1): [{"id": UserId("4001")}, {"id": UserId("4002")}]
    }
    caplog.set_level(logging.DEBUG, logger="jobs")

    run_report_if_all_voted(POLL_EXPIRES_AT)

    assert fake_discord.call_names() == ["get_channel_messages", "get_current_user"]
    assert caplog.messages == ["Vote 3000 (11/30-12/6): already closed"]


def test_report_if_all_voted_reports_one_second_before_poll_expiry(
    fake_discord: FakeDiscord,
) -> None:
    fake_discord.voters_by_answer_id = {
        AnswerId(1): [{"id": UserId("4001")}, {"id": UserId("4002")}]
    }

    run_report_if_all_voted(POLL_EXPIRES_AT - timedelta(seconds=1))

    assert fake_discord.call_names()[-3:] == [
        "create_dm_channel",
        "post_message",
        "add_reaction",
    ]


def test_report_if_all_voted_warns_without_vote_message(
    fake_discord: FakeDiscord, caplog: pytest.LogCaptureFixture
) -> None:
    fake_discord.messages = []

    run_report_if_all_voted(POLL_EXPIRES_AT - timedelta(days=1))

    assert fake_discord.call_names() == ["get_channel_messages", "get_current_user"]
    assert "No vote message found in channel 2000" in caplog.messages


def test_report_if_all_voted_does_not_mark_vote_when_dm_fails(
    fake_discord: FakeDiscord,
) -> None:
    fake_discord.voters_by_answer_id = {
        AnswerId(1): [{"id": UserId("4001")}, {"id": UserId("4002")}]
    }
    fake_discord.post_message_errors = {
        ChannelId("2001"): make_discord_api_error(
            500, "Internal Server Error", None, None
        )
    }

    with pytest.raises(DiscordApiError):
        run_report_if_all_voted(POLL_EXPIRES_AT - timedelta(days=1))

    assert "add_reaction" not in fake_discord.call_names()


def run_send_reminders(now: datetime) -> None:
    send_reminders("dummy-token", GuildId("1001"), ChannelId("2000"), now)


def test_send_reminders_dms_each_human_non_voter(
    fake_discord: FakeDiscord, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger="jobs")

    run_send_reminders(POLL_EXPIRES_AT - timedelta(days=1))

    assert fake_discord.calls == [
        ("get_channel_messages", "2000"),
        ("get_current_user",),
        ("get_answer_voters", "2000", "3000", 1),
        ("get_answer_voters", "2000", "3000", 2),
        ("list_guild_members", "1001"),
        ("create_dm_channel", "4001"),
        ("post_message", "2101"),
        ("create_dm_channel", "4002"),
        ("post_message", "2102"),
    ]
    assert [channel_id for channel_id, _ in fake_discord.posted_messages] == [
        "2101",
        "2102",
    ]
    for _, reminder_message in fake_discord.posted_messages:
        assert (
            "https://discord.com/channels/1001/2000/3000" in reminder_message["content"]
        )
    # Nobody failed, so the "not sent to" part is left out.
    assert (
        "Vote 3000 (11/30-12/6): sent 2/2 reminder DMs; sent to: Alice, bob"
        in caplog.messages
    )
    # Every DM worked, so there is no reply in the vote channel to log.
    assert (
        "Vote 3000 (11/30-12/6): posted a reminder in the vote channel"
        not in caplog.messages
    )


def test_send_reminders_does_nothing_when_everyone_voted(
    fake_discord: FakeDiscord, caplog: pytest.LogCaptureFixture
) -> None:
    fake_discord.voters_by_answer_id = {
        AnswerId(1): [{"id": UserId("4001")}, {"id": UserId("4002")}]
    }
    caplog.set_level(logging.INFO, logger="jobs")

    run_send_reminders(POLL_EXPIRES_AT - timedelta(days=1))

    assert "create_dm_channel" not in fake_discord.call_names()
    assert "post_message" not in fake_discord.call_names()
    assert (
        "Vote 3000 (11/30-12/6): everyone has voted; no reminders needed"
        in caplog.messages
    )


def test_send_reminders_warns_when_poll_is_closed(
    fake_discord: FakeDiscord, caplog: pytest.LogCaptureFixture
) -> None:
    run_send_reminders(POLL_EXPIRES_AT)

    assert fake_discord.call_names() == ["get_channel_messages", "get_current_user"]
    assert (
        "Vote 3000 (11/30-12/6): already closed; no reminders sent" in caplog.messages
    )


@pytest.mark.parametrize(
    ("discord_code", "expected_summary"),
    [
        # Seen on the real server when a member blocked the bot.
        pytest.param(
            50007,
            "Vote 3000 (11/30-12/6): sent 1/2 reminder DMs; sent to: bob; "
            "not sent to: Alice (403 Forbidden / Discord code 50007)",
            id="cannot_send_messages_to_user",
        ),
        # Seen on the real server when a member turned off DMs for the server.
        pytest.param(
            50278,
            "Vote 3000 (11/30-12/6): sent 1/2 reminder DMs; sent to: bob; "
            "not sent to: Alice (403 Forbidden / Discord code 50278)",
            id="no_mutual_guilds",
        ),
    ],
)
def test_send_reminders_replies_in_vote_channel_when_a_dm_is_closed(
    discord_code: int,
    expected_summary: str,
    fake_discord: FakeDiscord,
    caplog: pytest.LogCaptureFixture,
) -> None:
    # The first member's DMs are closed, so the second member proves the loop goes on.
    fake_discord.post_message_errors = {
        ChannelId("2101"): make_discord_api_error(403, "Forbidden", discord_code, None)
    }
    caplog.set_level(logging.INFO, logger="jobs")

    run_send_reminders(POLL_EXPIRES_AT - timedelta(days=1))

    assert [channel_id for channel_id, _ in fake_discord.posted_messages] == [
        "2102",
        "2000",
    ]
    vote_channel_reminder_message = fake_discord.posted_messages[1][1]
    assert vote_channel_reminder_message.get("message_reference") == {
        "message_id": "3000"
    }
    # Closed DMs are not errors: no failure line, only the summary and then the reply.
    assert caplog.messages == [
        expected_summary,
        "Vote 3000 (11/30-12/6): posted a reminder in the vote channel",
    ]


def test_send_reminders_logs_the_channel_reply_only_after_posting_it(
    fake_discord: FakeDiscord, caplog: pytest.LogCaptureFixture
) -> None:
    fake_discord.post_message_errors = {
        ChannelId("2101"): make_discord_api_error(403, "Forbidden", 50007, None),
        ChannelId("2000"): make_discord_api_error(
            500, "Internal Server Error", None, None
        ),
    }
    caplog.set_level(logging.INFO, logger="jobs")

    with pytest.raises(DiscordApiError):
        run_send_reminders(POLL_EXPIRES_AT - timedelta(days=1))

    # The summary is logged before the reply, so it survives the failed post.
    assert caplog.messages == [
        "Vote 3000 (11/30-12/6): sent 1/2 reminder DMs; sent to: bob; "
        "not sent to: Alice (403 Forbidden / Discord code 50007)"
    ]


def test_send_reminders_replies_once_when_several_dms_fail(
    fake_discord: FakeDiscord, caplog: pytest.LogCaptureFixture
) -> None:
    # One closed DM and one other error: both kinds lead to the same single reply.
    fake_discord.post_message_errors = {
        ChannelId("2101"): make_discord_api_error(
            403, "Forbidden", 50007, "Cannot send messages to this user"
        ),
        ChannelId("2102"): make_discord_api_error(
            500, "Internal Server Error", None, None
        ),
    }
    caplog.set_level(logging.INFO, logger="jobs")

    run_send_reminders(POLL_EXPIRES_AT - timedelta(days=1))

    # One reply for all failed DMs, not one per member.
    assert [channel_id for channel_id, _ in fake_discord.posted_messages] == ["2000"]
    # Nobody got a DM, so the "sent to" part is left out.
    assert (
        "Vote 3000 (11/30-12/6): sent 0/2 reminder DMs; not sent to: "
        "Alice (403 Forbidden / Discord code 50007: Cannot send messages to this user), "
        "bob (500 Internal Server Error / no Discord code)" in caplog.messages
    )


def test_send_reminders_continues_after_other_dm_errors(
    fake_discord: FakeDiscord, caplog: pytest.LogCaptureFixture
) -> None:
    fake_discord.post_message_errors = {
        ChannelId("2101"): make_discord_api_error(
            500, "Internal Server Error", None, None
        )
    }
    caplog.set_level(logging.INFO, logger="jobs")

    run_send_reminders(POLL_EXPIRES_AT - timedelta(days=1))

    # The failed DM is covered by one reply in the vote channel.
    assert [channel_id for channel_id, _ in fake_discord.posted_messages] == [
        "2102",
        "2000",
    ]
    [failure_record] = [
        record
        for record in caplog.records
        if record.getMessage()
        == "Vote 3000 (11/30-12/6): failed to send a reminder DM to Alice"
    ]
    # logger.exception keeps the traceback, so the cause can be found in the logs.
    assert failure_record.exc_info is not None
    assert (
        "Vote 3000 (11/30-12/6): sent 1/2 reminder DMs; sent to: bob; "
        "not sent to: Alice (500 Internal Server Error / no Discord code)"
        in caplog.messages
    )
    assert (
        "Vote 3000 (11/30-12/6): posted a reminder in the vote channel"
        in caplog.messages
    )

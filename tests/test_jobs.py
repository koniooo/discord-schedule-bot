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
    GuildId,
    GuildMember,
    Message,
    MessageCreateRequest,
    MessageId,
    Reaction,
    User,
    UserId,
)
from jobs import report_if_all_voted, start_vote
from schedule import get_monday_to_sunday_after_next
from vote import build_vote_message


def test_start_vote_posts_vote_message_and_starts_comment_thread(
    monkeypatch: pytest.MonkeyPatch,
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


type Call = tuple[object, ...]

# Tue 11/24 12:00 JST. Every vote message from make_vote_message closes at this time.
POLL_EXPIRES_AT = datetime(2026, 11, 24, 3, 0, tzinfo=UTC)


class FakeDiscordError(Exception):
    pass


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
        vote_message["thread"] = {"name": "11/30-12/6 💬コメント"}
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
            {"user": {"id": UserId("4001")}},
            {"user": {"id": UserId("4002")}},
        ]
        self.post_message_error: Exception | None = None

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
        return {"id": ChannelId("2001")}

    def post_message(
        self, _token: str, channel_id: ChannelId, body: MessageCreateRequest
    ) -> Message:
        self.calls.append(("post_message", channel_id))
        if self.post_message_error is not None:
            raise self.post_message_error
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
    fake_discord: FakeDiscord,
) -> None:
    fake_discord.voters_by_answer_id = {
        AnswerId(1): [{"id": UserId("4001")}],
        AnswerId(2): [{"id": UserId("4002")}],
    }

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

    assert "Vote 11/30-12/6 (3000): 1/2 members have voted" in caplog.messages


def test_report_if_all_voted_still_reports_without_thread(
    fake_discord: FakeDiscord, caplog: pytest.LogCaptureFixture
) -> None:
    fake_discord.messages = [make_vote_message(has_thread=False)]
    fake_discord.voters_by_answer_id = {
        AnswerId(1): [{"id": UserId("4001")}, {"id": UserId("4002")}]
    }
    caplog.set_level(logging.INFO, logger="jobs")

    run_report_if_all_voted(POLL_EXPIRES_AT - timedelta(days=1))

    assert "Vote (no thread) (3000): 2/2 members have voted" in caplog.messages
    assert fake_discord.call_names()[-3:] == [
        "create_dm_channel",
        "post_message",
        "add_reaction",
    ]


def test_report_if_all_voted_does_nothing_when_already_reported(
    fake_discord: FakeDiscord,
) -> None:
    fake_discord.messages = [
        make_vote_message(reactions=[{"me": True, "emoji": {"name": "✅"}}])
    ]
    fake_discord.voters_by_answer_id = {
        AnswerId(1): [{"id": UserId("4001")}, {"id": UserId("4002")}]
    }

    run_report_if_all_voted(POLL_EXPIRES_AT - timedelta(days=1))

    assert fake_discord.call_names() == ["get_channel_messages", "get_current_user"]


def test_report_if_all_voted_does_nothing_at_poll_expiry(
    fake_discord: FakeDiscord,
) -> None:
    fake_discord.voters_by_answer_id = {
        AnswerId(1): [{"id": UserId("4001")}, {"id": UserId("4002")}]
    }

    run_report_if_all_voted(POLL_EXPIRES_AT)

    assert fake_discord.call_names() == ["get_channel_messages", "get_current_user"]


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
    fake_discord.post_message_error = FakeDiscordError()

    with pytest.raises(FakeDiscordError):
        run_report_if_all_voted(POLL_EXPIRES_AT - timedelta(days=1))

    assert "add_reaction" not in fake_discord.call_names()

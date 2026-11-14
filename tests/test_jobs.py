from datetime import date
from typing import TypedDict

import pytest

import jobs
from discord_api import (
    Channel,
    ChannelId,
    Message,
    MessageCreateRequest,
    MessageId,
    UserId,
)
from jobs import start_vote
from schedule import get_monday_to_sunday_after_next
from vote import build_vote_message, format_comment_thread_name


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

    post_message_calls: list[PostMessageCall] = []
    start_thread_from_message_calls: list[StartThreadFromMessageCall] = []
    vote_message_id = MessageId("123456")
    vote_channel_id = ChannelId("2394893274")
    today = date(2026, 11, 13)

    def fake_post_message(
        _token: str, channel_id: ChannelId, body: MessageCreateRequest
    ) -> Message:
        post_message_calls.append({"channel_id": channel_id, "body": body})
        return {"id": vote_message_id, "author": {"id": UserId("")}}

    def fake_start_thread_from_message(
        _token: str, channel_id: ChannelId, message_id: MessageId, name: str
    ) -> Channel:
        start_thread_from_message_calls.append(
            {"channel_id": channel_id, "message_id": message_id, "name": name}
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
    assert start_thread_from_message_call["name"] == format_comment_thread_name(
        candidate_days
    )

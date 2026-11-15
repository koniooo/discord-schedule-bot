from io import BytesIO
from typing import Literal
from urllib.request import Request

import pytest

import discord_api
from discord_api import (
    AnswerId,
    ChannelId,
    GuildId,
    MessageId,
    add_reaction,
    build_request,
    get_answer_voters,
    get_channel_messages,
    get_current_user,
    list_guild_members,
    post_message,
    start_thread_from_message,
)


class FakeUrlopen:
    def __init__(self) -> None:
        self.requests: list[Request] = []
        self.response = b"{}"

    def __call__(self, request: Request) -> BytesIO:
        self.requests.append(request)
        return BytesIO(self.response)


@pytest.fixture
def fake_urlopen(monkeypatch: pytest.MonkeyPatch) -> FakeUrlopen:
    fake = FakeUrlopen()
    monkeypatch.setattr(discord_api, "urlopen", fake)
    return fake


def test_build_request_sets_full_url() -> None:
    assert (
        build_request("GET", "/users/@me", "dummy-token").full_url
        == "https://discord.com/api/v10/users/@me"
    )


def test_build_request_sets_bot_authorization_header() -> None:
    assert (
        build_request("GET", "/users/@me", "dummy-token").get_header("Authorization")
        == "Bot dummy-token"
    )


def test_build_request_sets_user_agent_header() -> None:
    assert (
        build_request("GET", "/users/@me", "dummy-token").get_header("User-agent")
        == "DiscordBot (https://github.com/koniooo/discord-schedule-bot, 0.1.0)"
    )


def test_build_request_sets_json_content_type_when_body_is_given() -> None:
    assert (
        build_request("POST", "/x", "dummy-token", body={}).get_header("Content-type")
        == "application/json"
    )


def test_build_request_does_not_set_content_type_without_body() -> None:
    assert build_request("GET", "/x", "dummy-token").get_header("Content-type") is None


@pytest.mark.parametrize("method", ["GET", "PUT"])
def test_build_request_uses_given_method_without_body(
    method: Literal["GET", "PUT"],
) -> None:
    assert build_request(method, "/x", "dummy-token").get_method() == method


def test_build_request_uses_post_method_with_body() -> None:
    assert build_request("POST", "/x", "dummy-token", {}).get_method() == "POST"


def test_build_request_sets_json_body() -> None:
    assert (
        build_request("POST", "/x", "dummy-token", body={"content": "hello"}).data
        == b'{"content": "hello"}'
    )


def test_build_request_has_no_body_when_body_is_not_given() -> None:
    assert build_request("GET", "/x", "dummy-token").data is None


def test_build_request_rejects_path_without_leading_slash() -> None:
    with pytest.raises(ValueError, match="users/@me"):
        build_request("GET", "users/@me", "dummy-token")


def test_build_request_rejects_post_without_body() -> None:
    with pytest.raises(ValueError, match="body"):
        # Intentionally call POST without body to test the runtime check.
        build_request("POST", "/x", "dummy-token")  # pyright: ignore[reportArgumentType]


def test_get_current_user_builds_request(fake_urlopen: FakeUrlopen) -> None:
    get_current_user("dummy-token")

    assert len(fake_urlopen.requests) == 1
    request = fake_urlopen.requests[0]
    assert request.method == "GET"
    assert request.full_url == "https://discord.com/api/v10/users/@me"
    assert request.get_header("Authorization") == "Bot dummy-token"


def test_get_current_user_returns_user(fake_urlopen: FakeUrlopen) -> None:
    fake_urlopen.response = b'{"id": "4000", "username": "sample-bot"}'

    assert get_current_user("dummy-token") == {"id": "4000", "username": "sample-bot"}


def test_post_message_builds_request(fake_urlopen: FakeUrlopen) -> None:
    post_message("dummy-token", ChannelId("2000"), body={"content": "hello"})

    assert len(fake_urlopen.requests) == 1
    request = fake_urlopen.requests[0]
    assert request.method == "POST"
    assert request.full_url == "https://discord.com/api/v10/channels/2000/messages"
    assert request.get_header("Authorization") == "Bot dummy-token"
    assert request.data == b'{"content": "hello"}'


def test_post_message_returns_created_message(fake_urlopen: FakeUrlopen) -> None:
    fake_urlopen.response = b'{"id": "3000", "content": "hello"}'

    assert post_message("dummy-token", ChannelId("2000"), {"content": "hello"}) == {
        "id": "3000",
        "content": "hello",
    }


def test_start_thread_from_message_builds_request(fake_urlopen: FakeUrlopen) -> None:
    start_thread_from_message(
        "dummy-token", ChannelId("2000"), MessageId("3000"), "thread_name"
    )

    assert len(fake_urlopen.requests) == 1
    request = fake_urlopen.requests[0]
    assert request.method == "POST"
    assert (
        request.full_url
        == "https://discord.com/api/v10/channels/2000/messages/3000/threads"
    )
    assert request.get_header("Authorization") == "Bot dummy-token"
    assert request.data == b'{"name": "thread_name", "auto_archive_duration": 10080}'


def test_start_thread_from_message_returns_created_thread(
    fake_urlopen: FakeUrlopen,
) -> None:
    fake_urlopen.response = b'{"id": "2001", "name": "name_from_response"}'

    assert start_thread_from_message(
        "dummy-token", ChannelId("2000"), MessageId("3000"), "thread_name"
    ) == {"id": "2001", "name": "name_from_response"}


def test_add_reaction_builds_request(fake_urlopen: FakeUrlopen) -> None:
    add_reaction("dummy-token", ChannelId("2000"), MessageId("3000"), "👍🏻")

    assert len(fake_urlopen.requests) == 1
    request = fake_urlopen.requests[0]
    assert request.method == "PUT"
    assert (
        request.full_url
        == "https://discord.com/api/v10/channels/2000/messages/3000/reactions/%F0%9F%91%8D%F0%9F%8F%BB/@me"
    )
    assert request.get_header("Authorization") == "Bot dummy-token"


def test_list_guild_members_builds_request(fake_urlopen: FakeUrlopen) -> None:
    list_guild_members("dummy-token", GuildId("1001"))

    assert len(fake_urlopen.requests) == 1
    request = fake_urlopen.requests[0]
    assert request.method == "GET"
    assert (
        request.full_url == "https://discord.com/api/v10/guilds/1001/members?limit=1000"
    )
    assert request.get_header("Authorization") == "Bot dummy-token"


def test_list_guild_members_returns_members(fake_urlopen: FakeUrlopen) -> None:
    fake_urlopen.response = (
        b'[{"user": {"id": "4000", "bot": true}}, {"user": {"id": "4001"}}]'
    )

    members = list_guild_members("dummy-token", GuildId("1001"))
    assert members == [
        {"user": {"id": "4000", "bot": True}},
        {"user": {"id": "4001"}},
    ]


def test_get_channel_messages_builds_request(fake_urlopen: FakeUrlopen) -> None:
    get_channel_messages("dummy-token", ChannelId("2000"))

    assert len(fake_urlopen.requests) == 1
    request = fake_urlopen.requests[0]
    assert request.method == "GET"
    assert (
        request.full_url
        == "https://discord.com/api/v10/channels/2000/messages?limit=100"
    )
    assert request.get_header("Authorization") == "Bot dummy-token"


def test_get_channel_messages_returns_messages(fake_urlopen: FakeUrlopen) -> None:
    fake_urlopen.response = (
        '[{"id": "3002", "author": {"id": "4000", "bot": true}, '
        '"poll": {"answers": ['
        '{"answer_id": 1, "poll_media": {"text": "11/23 (月)"}}, '
        '{"answer_id": 2, "poll_media": {"text": "どの日も難しい"}}]}}, '
        '{"id": "3001", "author": {"id": "4001"}}]'.encode()
    )

    assert get_channel_messages("dummy-token", ChannelId("2000")) == [
        {
            "id": "3002",
            "author": {"id": "4000", "bot": True},
            "poll": {
                "answers": [
                    {"answer_id": 1, "poll_media": {"text": "11/23 (月)"}},
                    {"answer_id": 2, "poll_media": {"text": "どの日も難しい"}},
                ]
            },
        },
        {"id": "3001", "author": {"id": "4001"}},
    ]


def test_get_answer_voters_builds_request(fake_urlopen: FakeUrlopen) -> None:
    # get_answer_voters reads the "users" key, so the default "{}" is not enough.
    fake_urlopen.response = b'{"users": []}'

    get_answer_voters("dummy-token", ChannelId("2000"), MessageId("3000"), AnswerId(1))

    assert len(fake_urlopen.requests) == 1
    request = fake_urlopen.requests[0]
    assert request.method == "GET"
    assert (
        request.full_url
        == "https://discord.com/api/v10/channels/2000/polls/3000/answers/1?limit=100"
    )
    assert request.get_header("Authorization") == "Bot dummy-token"


def test_get_answer_voters_returns_voters(fake_urlopen: FakeUrlopen) -> None:
    fake_urlopen.response = b'{"users": [{"id": "4001"}, {"id": "4002"}]}'

    assert get_answer_voters(
        "dummy-token", ChannelId("2000"), MessageId("3000"), AnswerId(1)
    ) == [{"id": "4001"}, {"id": "4002"}]

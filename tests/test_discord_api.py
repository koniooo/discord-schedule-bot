import email.message
import json
from io import BytesIO
from typing import Literal
from urllib.error import HTTPError
from urllib.request import Request

import pytest

import discord_api
from discord_api import (
    AnswerId,
    ChannelId,
    DiscordApiError,
    DiscordErrorBody,
    GuildId,
    Message,
    MessageId,
    UserId,
    add_reaction,
    build_request,
    create_dm_channel,
    get_answer_voters,
    get_channel_messages,
    get_current_user,
    get_thread_id_started_from,
    list_guild_members,
    parse_error_body,
    post_message,
    start_thread_from_message,
)


class FakeUrlopen:
    def __init__(self) -> None:
        self.requests: list[Request] = []
        self.response = b"{}"
        self.error: HTTPError | None = None

    def __call__(self, request: Request) -> BytesIO:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return BytesIO(self.response)


@pytest.fixture
def fake_urlopen(monkeypatch: pytest.MonkeyPatch) -> FakeUrlopen:
    fake = FakeUrlopen()
    monkeypatch.setattr(discord_api, "urlopen", fake)
    return fake


def make_http_error(status: int, reason: str, body: bytes) -> HTTPError:
    return HTTPError(
        "https://discord.com/api/v10",
        status,
        reason,
        email.message.Message(),
        BytesIO(body),
    )


def test_get_thread_id_started_from_returns_message_id() -> None:
    assert get_thread_id_started_from(MessageId("3000")) == "3000"


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


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        pytest.param(
            b'{"message": "Cannot send messages to this user", "code": 50007}',
            DiscordErrorBody(
                discord_code=50007, message="Cannot send messages to this user"
            ),
            id="discord_error",
        ),
        pytest.param(
            b'{"message": "401: Unauthorized", "code": 0}',
            DiscordErrorBody(discord_code=0, message="401: Unauthorized"),
            id="general_error_code_zero",
        ),
        pytest.param(
            b'{"message": "You are being rate limited.", "retry_after": 1.5}',
            DiscordErrorBody(discord_code=None, message="You are being rate limited."),
            id="no_code",
        ),
        pytest.param(
            b'{"code": 50007}',
            DiscordErrorBody(discord_code=50007, message=None),
            id="no_message",
        ),
        pytest.param(
            b'{"message": "Cannot send messages to this user", "code": "50007"}',
            DiscordErrorBody(
                discord_code=None, message="Cannot send messages to this user"
            ),
            id="code_wrong_type",
        ),
        pytest.param(
            b'{"message": 123, "code": 50007}',
            DiscordErrorBody(discord_code=50007, message=None),
            id="message_wrong_type",
        ),
        pytest.param(
            b'["code"]',
            DiscordErrorBody(discord_code=None, message=None),
            id="json_not_object",
        ),
        pytest.param(
            b"<html>502 Bad Gateway</html>",
            DiscordErrorBody(discord_code=None, message=None),
            id="not_json",
        ),
        pytest.param(
            b"", DiscordErrorBody(discord_code=None, message=None), id="empty"
        ),
    ],
)
def test_parse_error_body_returns_code_and_message(
    body: bytes, expected: DiscordErrorBody
) -> None:
    assert parse_error_body(body) == expected


@pytest.mark.parametrize(
    ("status", "reason", "body", "expected"),
    [
        pytest.param(
            403,
            "Forbidden",
            b'{"message": "Cannot send messages to this user", "code": 50007}',
            "POST /api/v10/channels/2000/messages returned 403 Forbidden: Cannot send messages to this user (Discord code 50007)",
            id="code_and_message",
        ),
        pytest.param(
            429,
            "Too Many Requests",
            b'{"message": "You are being rate limited.", "retry_after": 1.5}',
            "POST /api/v10/channels/2000/messages returned 429 Too Many Requests: You are being rate limited.",
            id="message_only",
        ),
        pytest.param(
            400,
            "Bad Request",
            b'{"code": 50035}',
            'POST /api/v10/channels/2000/messages returned 400 Bad Request: {"code": 50035} (Discord code 50035)',
            id="code_only",
        ),
        pytest.param(
            502,
            "Bad Gateway",
            b"<html>\n<body>502 Bad Gateway</body>\n</html>",
            "POST /api/v10/channels/2000/messages returned 502 Bad Gateway: <html> <body>502 Bad Gateway</body> </html>",
            id="not_json",
        ),
        pytest.param(
            500,
            "Internal Server Error",
            b"",
            "POST /api/v10/channels/2000/messages returned 500 Internal Server Error",
            id="empty",
        ),
    ],
)
def test_post_message_raises_discord_api_error_with_summary(
    status: int, reason: str, body: bytes, expected: str, fake_urlopen: FakeUrlopen
) -> None:
    fake_urlopen.error = make_http_error(status, reason, body)

    with pytest.raises(DiscordApiError) as caught:
        post_message("dummy-token", ChannelId("2000"), {"content": ""})

    assert str(caught.value) == expected  # str(error) is the summary line shown in logs


def test_post_message_raises_discord_api_error_with_details(
    fake_urlopen: FakeUrlopen,
) -> None:
    body = b'{"message": "Cannot send messages to this user", "code": 50007}'
    fake_urlopen.error = make_http_error(403, "Forbidden", body)

    with pytest.raises(DiscordApiError) as caught:
        post_message("dummy-token", ChannelId("2000"), {"content": ""})

    error = caught.value
    assert error.status == 403
    assert error.reason == "Forbidden"
    assert error.discord_code == 50007
    assert error.message == "Cannot send messages to this user"
    assert error.body == body


def test_post_message_keeps_http_error_as_cause(fake_urlopen: FakeUrlopen) -> None:
    http_error = make_http_error(403, "Forbidden", b"")
    fake_urlopen.error = http_error

    with pytest.raises(DiscordApiError) as caught:
        post_message("dummy-token", ChannelId("2000"), {"content": ""})

    assert caught.value.__cause__ is http_error


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


def test_create_dm_channel_builds_request(fake_urlopen: FakeUrlopen) -> None:
    create_dm_channel("dummy-token", UserId("4001"))

    assert len(fake_urlopen.requests) == 1
    request = fake_urlopen.requests[0]
    assert request.method == "POST"
    assert request.full_url == "https://discord.com/api/v10/users/@me/channels"
    assert request.get_header("Authorization") == "Bot dummy-token"
    assert request.data == b'{"recipient_id": "4001"}'


def test_create_dm_channel_returns_dm_channel(fake_urlopen: FakeUrlopen) -> None:
    fake_urlopen.response = b'{"id": "2000", "type": 1}'

    assert create_dm_channel("dummy-token", UserId("4001")) == {"id": "2000", "type": 1}


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
    messages: list[Message] = [
        {
            "id": MessageId("3002"),
            "author": {"id": UserId("4000"), "bot": True},
            "poll": {
                "answers": [
                    {"answer_id": AnswerId(1), "poll_media": {"text": "11/23 (月)"}},
                    {
                        "answer_id": AnswerId(2),
                        "poll_media": {"text": "どの日も難しい"},
                    },
                ],
                "expiry": "2026-11-24T03:00:00+00:00",
            },
        },
        {"id": MessageId("3001"), "author": {"id": UserId("4001")}},
    ]
    fake_urlopen.response = json.dumps(messages).encode()

    assert get_channel_messages("dummy-token", ChannelId("2000")) == messages


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


def test_start_thread_from_message_builds_request(fake_urlopen: FakeUrlopen) -> None:
    start_thread_from_message(
        "dummy-token", ChannelId("2000"), MessageId("3000"), "thread_name", 1440
    )

    assert len(fake_urlopen.requests) == 1
    request = fake_urlopen.requests[0]
    assert request.method == "POST"
    assert (
        request.full_url
        == "https://discord.com/api/v10/channels/2000/messages/3000/threads"
    )
    assert request.get_header("Authorization") == "Bot dummy-token"
    assert request.data == b'{"name": "thread_name", "auto_archive_duration": 1440}'


def test_start_thread_from_message_returns_created_thread(
    fake_urlopen: FakeUrlopen,
) -> None:
    fake_urlopen.response = b'{"id": "2001", "name": "name_from_response"}'

    assert start_thread_from_message(
        "dummy-token", ChannelId("2000"), MessageId("3000"), "thread_name", 1440
    ) == {"id": "2001", "name": "name_from_response"}


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

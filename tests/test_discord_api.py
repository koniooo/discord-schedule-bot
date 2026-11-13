from io import BytesIO
from typing import Literal
from urllib.request import Request

import pytest

import discord_api
from discord_api import (
    ChannelId,
    MessageId,
    add_reaction,
    build_request,
    get_current_user,
    post_message,
    start_thread_from_message,
)


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


def test_get_current_user_builds_request(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[Request] = []

    def fake_urlopen(request: Request) -> BytesIO:
        calls.append(request)
        return BytesIO(b'{"id": "123", "username": "sample-bot"}')

    monkeypatch.setattr(discord_api, "urlopen", fake_urlopen)
    get_current_user("dummy-token")

    assert len(calls) == 1
    request = calls[0]
    assert request.method == "GET"
    assert request.full_url == "https://discord.com/api/v10/users/@me"
    assert request.get_header("Authorization") == "Bot dummy-token"


def test_get_current_user_returns_user(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(_request: Request) -> BytesIO:
        return BytesIO(b'{"id": "123", "username": "sample-bot"}')

    monkeypatch.setattr(discord_api, "urlopen", fake_urlopen)

    assert get_current_user("dummy-token") == {"id": "123", "username": "sample-bot"}


def test_post_message_builds_request(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[Request] = []

    def fake_urlopen(request: Request) -> BytesIO:
        calls.append(request)
        return BytesIO(b'{"id": "123", "content": "hello"}')

    monkeypatch.setattr(discord_api, "urlopen", fake_urlopen)
    post_message("dummy-token", ChannelId("456"), body={"content": "hello"})

    assert len(calls) == 1
    request = calls[0]
    assert request.method == "POST"
    assert request.full_url == "https://discord.com/api/v10/channels/456/messages"
    assert request.get_header("Authorization") == "Bot dummy-token"
    assert request.data == b'{"content": "hello"}'


def test_post_message_returns_created_message(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(_request: Request) -> BytesIO:
        return BytesIO(b'{"id": "123", "content": "hello"}')

    monkeypatch.setattr(discord_api, "urlopen", fake_urlopen)

    assert post_message("dummy-token", ChannelId("456"), {"content": "hello"}) == {
        "id": "123",
        "content": "hello",
    }


def test_start_thread_from_message_builds_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[Request] = []

    def fake_urlopen(request: Request) -> BytesIO:
        calls.append(request)
        return BytesIO(b'{"id": "789", "name": "thread_name"}')

    monkeypatch.setattr(discord_api, "urlopen", fake_urlopen)
    start_thread_from_message(
        "dummy-token", ChannelId("123456"), MessageId("345678"), "thread_name"
    )

    assert len(calls) == 1
    request = calls[0]
    assert request.method == "POST"
    assert (
        request.full_url
        == "https://discord.com/api/v10/channels/123456/messages/345678/threads"
    )
    assert request.get_header("Authorization") == "Bot dummy-token"
    assert request.data == b'{"name": "thread_name", "auto_archive_duration": 10080}'


def test_start_thread_from_message_returns_created_thread(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(_request: Request) -> BytesIO:
        return BytesIO(b'{"id": "789", "name": "name_from_response"}')

    monkeypatch.setattr(discord_api, "urlopen", fake_urlopen)

    assert start_thread_from_message(
        "dummy-token", ChannelId("456789"), MessageId("123456"), "thread_name"
    ) == {"id": "789", "name": "name_from_response"}


def test_add_reaction_builds_request(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[Request] = []

    def fake_urlopen(request: Request) -> BytesIO:
        calls.append(request)
        return BytesIO(b"")

    monkeypatch.setattr(discord_api, "urlopen", fake_urlopen)
    add_reaction("dummy-token", ChannelId("456"), MessageId("123456"), "👍🏻")

    assert len(calls) == 1
    request = calls[0]
    assert request.method == "PUT"
    assert (
        request.full_url
        == "https://discord.com/api/v10/channels/456/messages/123456/reactions/%F0%9F%91%8D%F0%9F%8F%BB/@me"
    )
    assert request.get_header("Authorization") == "Bot dummy-token"

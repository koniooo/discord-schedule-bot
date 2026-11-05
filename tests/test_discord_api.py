from io import BytesIO
from urllib.request import Request

import pytest

import discord_api
from discord_api import HttpMethod, build_request, get_current_user


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


@pytest.mark.parametrize("expected_method", ["GET", "POST", "PUT"])
def test_build_request_uses_given_method(expected_method: HttpMethod) -> None:
    assert (
        build_request(expected_method, "/x", "dummy-token").get_method()
        == expected_method
    )


def test_build_request_sets_json_body() -> None:
    assert (
        build_request("POST", "/x", "dummy-token", body={"content": "hello"}).data
        == b'{"content": "hello"}'
    )


def test_build_request_has_no_body_when_body_is_not_given() -> None:
    assert build_request("GET", "/x", "dummy-token").data is None


def test_build_request_rejects_path_without_leading_slash() -> None:
    with pytest.raises(ValueError):
        build_request("GET", "users/@me", "dummy-token")


def test_get_current_user(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(_request: Request) -> BytesIO:
        return BytesIO(b'{"id": "123", "username": "sample-bot"}')

    monkeypatch.setattr(discord_api, "urlopen", fake_urlopen)

    assert get_current_user("dummy-token") == {"id": "123", "username": "sample-bot"}

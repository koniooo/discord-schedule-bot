from io import BytesIO
from urllib.request import Request

import pytest

import discord_api
from discord_api import build_request, get_current_user


def test_build_request_sets_full_url() -> None:
    assert (
        build_request("/users/@me", "dummy-token").full_url
        == "https://discord.com/api/v10/users/@me"
    )


def test_build_request_sets_bot_authorization_header() -> None:
    assert (
        build_request("/users/@me", "dummy-token").get_header("Authorization")
        == "Bot dummy-token"
    )


def test_build_request_sets_user_agent_header() -> None:
    assert (
        build_request("/users/@me", "dummy-token").get_header("User-agent")
        == "DiscordBot (https://github.com/koniooo/discord-schedule-bot, 0.1.0)"
    )


def test_get_current_user(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(_request: Request) -> BytesIO:
        return BytesIO(b'{"id": "123", "username": "sample-bot"}')

    monkeypatch.setattr(discord_api, "urlopen", fake_urlopen)

    assert get_current_user("dummy-token") == {"id": "123", "username": "sample-bot"}

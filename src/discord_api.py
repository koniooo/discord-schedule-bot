import json
from typing import Any
from urllib.request import Request, urlopen

DISCORD_API_BASE_URL = "https://discord.com/api/v10"
USER_AGENT = "DiscordBot (https://github.com/koniooo/discord-schedule-bot, 0.1.0)"


def build_request(path: str, token: str) -> Request:
    return Request(
        url=f"{DISCORD_API_BASE_URL}{path}",
        headers={
            "Authorization": f"Bot {token}",
            "User-Agent": USER_AGENT,
        },
    )


def get_current_user(token: str) -> dict[str, Any]:
    """GET https://discord.com/api/v10/users/@me"""
    built_request = build_request("/users/@me", token)
    with urlopen(built_request) as response:
        return json.load(response)

import json
from typing import Any, Literal
from urllib.request import Request, urlopen

DISCORD_API_BASE_URL = "https://discord.com/api/v10"
USER_AGENT = "DiscordBot (https://github.com/koniooo/discord-schedule-bot, 0.1.0)"

type HttpMethod = Literal["GET", "POST", "PUT"]


def build_request(
    method: HttpMethod, path: str, token: str, body: dict[str, Any] | None = None
) -> Request:
    if not path.startswith("/"):
        raise ValueError(f"path must start with '/': {path}")

    return Request(
        method=method,
        url=f"{DISCORD_API_BASE_URL}{path}",
        headers={
            "Authorization": f"Bot {token}",
            "User-Agent": USER_AGENT,
        },
        data=None if body is None else json.dumps(body).encode(),
    )


def get_current_user(token: str) -> dict[str, Any]:
    """GET https://discord.com/api/v10/users/@me"""
    built_request = build_request("GET", "/users/@me", token)
    with urlopen(built_request) as response:
        return json.load(response)

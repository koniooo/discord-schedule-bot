import json
from typing import Any, Literal
from urllib.parse import quote
from urllib.request import Request, urlopen

DISCORD_API_BASE_URL = "https://discord.com/api/v10"
USER_AGENT = "DiscordBot (https://github.com/koniooo/discord-schedule-bot, 0.1.0)"

type HttpMethod = Literal["GET", "POST", "PUT"]


def build_request(
    method: HttpMethod, path: str, token: str, body: dict[str, Any] | None = None
) -> Request:
    if not path.startswith("/"):
        raise ValueError(f"path must start with '/': {path}")

    if method == "POST" and body is None:
        raise ValueError("POST requires a body")

    headers = {
        "Authorization": f"Bot {token}",
        "User-Agent": USER_AGENT,
    }

    if body is not None:
        headers["Content-Type"] = "application/json"

    return Request(
        method=method,
        url=f"{DISCORD_API_BASE_URL}{path}",
        headers=headers,
        data=None if body is None else json.dumps(body).encode(),
    )


def get_current_user(token: str) -> dict[str, Any]:
    """GET https://discord.com/api/v10/users/@me"""
    request = build_request("GET", "/users/@me", token)
    with urlopen(request) as response:
        return json.load(response)


def post_message(token: str, channel_id: str, body: dict[str, Any]) -> dict[str, Any]:
    """POST https://discord.com/api/v10/channels/{channel_id}/messages"""
    request = build_request("POST", f"/channels/{channel_id}/messages", token, body)
    with urlopen(request) as response:
        return json.load(response)


def add_reaction(token: str, channel_id: str, message_id: str, emoji: str) -> None:
    """PUT https://discord.com/api/v10/channels/{channel_id}/messages/{message_id}/reactions/{emoji}/@me"""
    encoded_emoji = quote(emoji, safe="")
    request = build_request(
        "PUT",
        f"/channels/{channel_id}/messages/{message_id}/reactions/{encoded_emoji}/@me",
        token,
    )
    with urlopen(request):
        pass

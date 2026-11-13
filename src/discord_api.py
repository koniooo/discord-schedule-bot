import json
from collections.abc import Mapping
from typing import Any, Literal, NewType, TypedDict, overload
from urllib.parse import quote
from urllib.request import Request, urlopen

DISCORD_API_BASE_URL = "https://discord.com/api/v10"
USER_AGENT = "DiscordBot (https://github.com/koniooo/discord-schedule-bot, 0.1.0)"
SUPPRESS_NOTIFICATIONS = 1 << 12

ChannelId = NewType("ChannelId", str)
MessageId = NewType("MessageId", str)

type HttpMethod = Literal["GET", "POST", "PUT"]
type AllowedMentionType = Literal["roles", "users", "everyone"]


class PollMedia(TypedDict):
    text: str


class PollAnswer(TypedDict):
    poll_media: PollMedia


class AllowedMentions(TypedDict):
    parse: list[AllowedMentionType]


class PollCreateRequest(TypedDict):
    question: PollMedia
    answers: list[PollAnswer]
    duration: int
    allow_multiselect: bool


class Message(TypedDict):
    id: MessageId


class Channel(TypedDict):
    id: ChannelId


@overload
def build_request(
    method: Literal["GET", "PUT"], path: str, token: str, body: None = None
) -> Request: ...
@overload
def build_request(
    method: Literal["POST"], path: str, token: str, body: Mapping[str, Any]
) -> Request: ...
def build_request(
    method: HttpMethod, path: str, token: str, body: Mapping[str, Any] | None = None
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


def post_message(token: str, channel_id: ChannelId, body: Mapping[str, Any]) -> Message:
    """POST https://discord.com/api/v10/channels/{channel_id}/messages"""
    request = build_request("POST", f"/channels/{channel_id}/messages", token, body)
    with urlopen(request) as response:
        return json.load(response)


def start_thread_from_message(
    token: str, channel_id: ChannelId, message_id: MessageId, name: str
) -> Channel:
    """POST https://discord.com/api/v10/channels/{channel_id}/messages/{message_id}/threads"""
    body = {"name": name, "auto_archive_duration": 60 * 24 * 7}
    request = build_request(
        "POST",
        f"/channels/{channel_id}/messages/{message_id}/threads",
        token,
        body=body,
    )
    with urlopen(request) as response:
        return json.load(response)


def add_reaction(
    token: str, channel_id: ChannelId, message_id: MessageId, emoji: str
) -> None:
    """PUT https://discord.com/api/v10/channels/{channel_id}/messages/{message_id}/reactions/{emoji}/@me"""
    encoded_emoji = quote(emoji, safe="")
    request = build_request(
        "PUT",
        f"/channels/{channel_id}/messages/{message_id}/reactions/{encoded_emoji}/@me",
        token,
    )
    with urlopen(request):
        pass

import json
from collections.abc import Mapping
from typing import Any, Literal, NewType, NotRequired, ReadOnly, TypedDict, overload
from urllib.parse import quote
from urllib.request import Request, urlopen

DISCORD_API_BASE_URL = "https://discord.com/api/v10"
USER_AGENT = "DiscordBot (https://github.com/koniooo/discord-schedule-bot, 0.1.0)"

type HttpMethod = Literal["GET", "POST", "PUT"]

UserId = NewType("UserId", str)
ChannelId = NewType("ChannelId", str)
MessageId = NewType("MessageId", str)
AnswerId = NewType("AnswerId", int)
GuildId = NewType("GuildId", str)


class User(TypedDict):
    id: UserId
    bot: NotRequired[bool]


class Channel(TypedDict):
    id: ChannelId


class Thread(TypedDict):
    name: str


class PollMedia(TypedDict):
    text: str


class PollAnswer(TypedDict):
    poll_media: PollMedia


class PollCreateRequest(TypedDict):
    question: PollMedia
    answers: list[PollAnswer]
    duration: int
    allow_multiselect: bool


class PollAnswerResponse(PollAnswer):
    answer_id: AnswerId


class PollResponse(TypedDict):
    answers: list[PollAnswerResponse]
    expiry: str | None


class Emoji(TypedDict):
    name: str | None


class Reaction(TypedDict):
    me: bool
    emoji: Emoji


class Message(TypedDict):
    id: MessageId
    author: User
    poll: NotRequired[PollResponse]
    reactions: NotRequired[list[Reaction]]
    thread: NotRequired[Thread]


class MessageReference(TypedDict):
    message_id: MessageId


class MessageCreateRequest(TypedDict):
    content: ReadOnly[str]
    message_reference: ReadOnly[NotRequired[MessageReference]]
    poll: ReadOnly[NotRequired[PollCreateRequest]]


# Minutes of inactivity before Discord archives a thread: 1 hour, 1 day, 3 days, 7 days.
type AutoArchiveDuration = Literal[60, 1440, 4320, 10080]


class GuildMember(TypedDict):
    user: User


def get_thread_id_started_from(message_id: MessageId) -> ChannelId:
    """A thread started from a message has the same id as the message."""
    return ChannelId(message_id)


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


def get_current_user(token: str) -> User:
    """GET https://discord.com/api/v10/users/@me"""
    request = build_request("GET", "/users/@me", token)
    with urlopen(request) as response:
        return json.load(response)


def post_message(
    token: str, channel_id: ChannelId, body: MessageCreateRequest
) -> Message:
    """POST https://discord.com/api/v10/channels/{channel_id}/messages"""
    request = build_request("POST", f"/channels/{channel_id}/messages", token, body)
    with urlopen(request) as response:
        return json.load(response)


def start_thread_from_message(
    token: str,
    channel_id: ChannelId,
    message_id: MessageId,
    name: str,
    auto_archive_duration: AutoArchiveDuration,
) -> Channel:
    """POST https://discord.com/api/v10/channels/{channel_id}/messages/{message_id}/threads"""
    body = {"name": name, "auto_archive_duration": auto_archive_duration}
    request = build_request(
        "POST",
        f"/channels/{channel_id}/messages/{message_id}/threads",
        token,
        body,
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


def list_guild_members(token: str, guild_id: GuildId) -> list[GuildMember]:
    """GET https://discord.com/api/v10/guilds/{guild_id}/members?limit=1000"""
    request = build_request("GET", f"/guilds/{guild_id}/members?limit=1000", token)
    with urlopen(request) as response:
        return json.load(response)


def get_channel_messages(token: str, channel_id: ChannelId) -> list[Message]:
    """GET https://discord.com/api/v10/channels/{channel_id}/messages?limit=100"""
    request = build_request("GET", f"/channels/{channel_id}/messages?limit=100", token)
    with urlopen(request) as response:
        return json.load(response)


def get_answer_voters(
    token: str, channel_id: ChannelId, message_id: MessageId, answer_id: AnswerId
) -> list[User]:
    """GET https://discord.com/api/v10/channels/{channel_id}/polls/{message_id}/answers/{answer_id}?limit=100"""
    request = build_request(
        "GET",
        f"/channels/{channel_id}/polls/{message_id}/answers/{answer_id}?limit=100",
        token,
    )
    with urlopen(request) as response:
        return json.load(response)["users"]


def create_dm_channel(token: str, recipient_id: UserId) -> Channel:
    """POST https://discord.com/api/v10/users/@me/channels"""
    body = {"recipient_id": recipient_id}
    request = build_request("POST", "/users/@me/channels", token, body)
    with urlopen(request) as response:
        return json.load(response)

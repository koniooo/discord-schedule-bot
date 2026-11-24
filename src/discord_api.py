import json
from collections.abc import Mapping
from typing import (
    Any,
    Literal,
    NamedTuple,
    NewType,
    NotRequired,
    ReadOnly,
    TypedDict,
    overload,
)
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

DISCORD_API_BASE_URL = "https://discord.com/api/v10"
USER_AGENT = "DiscordBot (https://github.com/koniooo/discord-schedule-bot, 0.1.0)"
# Discord's JSON error codes when a user can't receive DMs from the bot.
CANNOT_SEND_MESSAGES_TO_USER = 50007
CANNOT_SEND_MESSAGES_TO_USER_NO_MUTUAL_GUILDS = 50278

type HttpMethod = Literal["GET", "POST", "PUT", "PATCH"]

UserId = NewType("UserId", str)
ChannelId = NewType("ChannelId", str)
MessageId = NewType("MessageId", str)
AnswerId = NewType("AnswerId", int)
GuildId = NewType("GuildId", str)


class User(TypedDict):
    id: UserId
    bot: NotRequired[bool]
    # Discord always sends these two; NotRequired keeps hand-built test users short.
    username: NotRequired[str]
    global_name: NotRequired[str | None]


class GuildMember(TypedDict):
    user: User
    nick: NotRequired[str | None]


class Channel(TypedDict):
    id: ChannelId


class ThreadMetadata(TypedDict):
    archived: bool
    locked: bool


class Thread(TypedDict):
    name: str
    thread_metadata: ThreadMetadata


# Minutes of inactivity before Discord archives a thread: 1 hour, 1 day, 3 days, 7 days.
type AutoArchiveDuration = Literal[60, 1440, 4320, 10080]


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


def get_thread_id_started_from(message_id: MessageId) -> ChannelId:
    """A thread started from a message has the same id as the message."""
    return ChannelId(message_id)


@overload
def build_request(
    method: Literal["GET", "PUT"], path: str, token: str, body: None = None
) -> Request: ...
@overload
def build_request(
    method: Literal["POST", "PATCH"], path: str, token: str, body: Mapping[str, Any]
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


class DiscordErrorBody(NamedTuple):
    discord_code: int | None
    message: str | None


def parse_error_body(body: bytes) -> DiscordErrorBody:
    """Parse Discord's JSON error body. Missing or invalid parts become None."""
    try:
        data = json.loads(body)
    except ValueError:
        return DiscordErrorBody(discord_code=None, message=None)
    if not isinstance(data, dict):
        return DiscordErrorBody(discord_code=None, message=None)

    if "code" in data and isinstance(data["code"], int):
        discord_code = data["code"]
    else:
        discord_code = None

    if "message" in data and isinstance(data["message"], str):
        message = data["message"]
    else:
        message = None
    return DiscordErrorBody(discord_code=discord_code, message=message)


class DiscordApiError(Exception):
    """A request to the Discord API failed.

    Attributes:
        status: The HTTP status code, e.g. 403.
        reason: The HTTP reason phrase, e.g. "Forbidden".
        discord_code: Discord's JSON error code, e.g. 50007, or None.
        message: Discord's error message, or None.
        body: The raw response body.
    """

    def __init__(
        self,
        *,
        method: str,
        path: str,
        status: int,
        reason: str,
        discord_code: int | None,
        message: str | None,
        body: bytes,
    ) -> None:
        summary = f"{method} {path} returned {status} {reason}"
        if message is not None:
            summary += f": {message}"
        elif body:
            # Keep it on one line and short, even for a long HTML error page.
            snippet = " ".join(body.decode(errors="replace").split())[:500]
            summary += f": {snippet}"
        if discord_code is not None:
            summary += f" (Discord code {discord_code})"

        super().__init__(summary)
        self.status = status
        self.reason = reason
        self.discord_code = discord_code
        self.message = message
        self.body = body


def format_error_details(error: DiscordApiError) -> str:
    """Return the status and Discord's error details on one line.

    e.g. "403 Forbidden / Discord code 50007: Cannot send messages to this user"
    """
    status_line = f"{error.status} {error.reason}".rstrip()
    if error.discord_code is not None:
        code = f"Discord code {error.discord_code}"
    else:
        code = "no Discord code"
    message_part = f": {error.message}" if error.message is not None else ""
    return f"{status_line} / {code}{message_part}"


def _send(request: Request) -> bytes:
    """Send the request to Discord and return the raw response body.

    Raises DiscordApiError when Discord answers with an HTTP error status.
    """
    try:
        with urlopen(request) as response:
            return response.read()
    except HTTPError as error:
        body = error.read()
        error_body = parse_error_body(body)
        raise DiscordApiError(
            method=request.get_method(),
            path=request.selector,
            status=error.code,
            reason=error.reason,
            discord_code=error_body.discord_code,
            message=error_body.message,
            body=body,
        ) from error


def get_current_user(token: str) -> User:
    """GET https://discord.com/api/v10/users/@me"""
    request = build_request("GET", "/users/@me", token)
    return json.loads(_send(request))


def create_dm_channel(token: str, recipient_id: UserId) -> Channel:
    """POST https://discord.com/api/v10/users/@me/channels"""
    body = {"recipient_id": recipient_id}
    request = build_request("POST", "/users/@me/channels", token, body)
    return json.loads(_send(request))


def list_guild_members(token: str, guild_id: GuildId) -> list[GuildMember]:
    """GET https://discord.com/api/v10/guilds/{guild_id}/members?limit=1000

    Returns every member of the server, including bots.
    """
    request = build_request("GET", f"/guilds/{guild_id}/members?limit=1000", token)
    return json.loads(_send(request))


def get_channel_messages(token: str, channel_id: ChannelId) -> list[Message]:
    """GET https://discord.com/api/v10/channels/{channel_id}/messages?limit=100"""
    request = build_request("GET", f"/channels/{channel_id}/messages?limit=100", token)
    return json.loads(_send(request))


def post_message(
    token: str, channel_id: ChannelId, body: MessageCreateRequest
) -> Message:
    """POST https://discord.com/api/v10/channels/{channel_id}/messages"""
    request = build_request("POST", f"/channels/{channel_id}/messages", token, body)
    return json.loads(_send(request))


def modify_thread(
    token: str, thread_id: ChannelId, *, locked: bool, archived: bool
) -> Channel:
    """PATCH https://discord.com/api/v10/channels/{thread_id}"""
    request = build_request(
        "PATCH",
        f"/channels/{thread_id}",
        token,
        {"locked": locked, "archived": archived},
    )
    return json.loads(_send(request))


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
    _send(request)


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
    return json.loads(_send(request))


def get_answer_voters(
    token: str, channel_id: ChannelId, message_id: MessageId, answer_id: AnswerId
) -> list[User]:
    """GET https://discord.com/api/v10/channels/{channel_id}/polls/{message_id}/answers/{answer_id}?limit=100"""
    request = build_request(
        "GET",
        f"/channels/{channel_id}/polls/{message_id}/answers/{answer_id}?limit=100",
        token,
    )
    return json.loads(_send(request))["users"]

from collections.abc import Sequence
from datetime import date, datetime, timedelta

from discord_api import (
    AutoArchiveDuration,
    ChannelId,
    GuildId,
    GuildMember,
    Message,
    MessageCreateRequest,
    MessageId,
    PollAnswer,
    PollResponse,
    User,
    UserId,
)
from schedule import JST, format_date_range, format_date_with_weekday
from vote_timing import VOTE_DURATION

NO_AVAILABLE_DAY_TEXT = "どの日も難しい"

VOTE_ANNOUNCEMENT_TEXT = (
    "再来週のスケジュールを決めるクポ～。ご投票お願いしますクポ。\n\n"
    "「この日は遅れるかも・まだわからない」といったコメントは、このメッセージにぶら下がってるスレッドへどうぞクポ。"
)

POLL_QUESTION_TEXT = "参加可能日 (22:00～23:30)"

COMMENT_THREAD_NAME_SUFFIX = "💬コメント"

COMMENT_THREAD_AUTO_ARCHIVE_MINUTES: AutoArchiveDuration = 60 * 24 * 7

ALL_VOTED_REPORTED_EMOJI = "✅"


def build_poll_answers(candidate_days: list[date]) -> list[PollAnswer]:
    answers: list[PollAnswer] = [
        {"poll_media": {"text": format_date_with_weekday(day)}}
        for day in candidate_days
    ]
    return [*answers, {"poll_media": {"text": NO_AVAILABLE_DAY_TEXT}}]


def build_vote_message(candidate_days: list[date]) -> MessageCreateRequest:
    return {
        "content": f"{VOTE_ANNOUNCEMENT_TEXT} @everyone",
        "poll": {
            "question": {"text": POLL_QUESTION_TEXT},
            "answers": build_poll_answers(candidate_days),
            "duration": VOTE_DURATION // timedelta(hours=1),
            "allow_multiselect": True,
        },
    }


def format_comment_thread_name(candidate_days: list[date]) -> str:
    date_range = format_date_range(candidate_days[0], candidate_days[-1])
    return f"{date_range} {COMMENT_THREAD_NAME_SUFFIX}"


def find_latest_vote_message(
    messages: Sequence[Message], bot_id: UserId
) -> Message | None:
    def is_vote_message(message: Message) -> bool:
        return "poll" in message and message["author"]["id"] == bot_id

    vote_messages = [message for message in messages if is_vote_message(message)]
    return max(vote_messages, key=lambda message: int(message["id"]), default=None)


def collect_voter_ids(voters_per_answer: list[list[User]]) -> set[UserId]:
    voter_ids: set[UserId] = set()
    for voters in voters_per_answer:
        for voter in voters:
            voter_ids.add(voter["id"])
    return voter_ids


def is_human(user: User) -> bool:
    return not user.get("bot", False)


def collect_human_non_voter_ids(
    guild_members: list[GuildMember], voter_ids: set[UserId]
) -> list[UserId]:
    """Return the ids of human members who have not voted, in member order."""

    def is_human_non_voter(user: User) -> bool:
        return is_human(user) and user["id"] not in voter_ids

    users = [guild_member["user"] for guild_member in guild_members]

    return [user["id"] for user in users if is_human_non_voter(user)]


def has_own_reaction(message: Message, emoji: str) -> bool:
    if "reactions" not in message:
        return False
    return any(
        reaction["me"] and reaction["emoji"]["name"] == emoji
        for reaction in message["reactions"]
    )


def get_poll_expires_at(poll: PollResponse) -> datetime:
    expiry = poll["expiry"]
    if expiry is None:
        raise ValueError("Poll has no expiry")
    return datetime.fromisoformat(expiry)


def build_all_voted_report_message(
    human_member_count: int,
    guild_id: GuildId,
    thread_id: ChannelId,
    poll_expires_at: datetime,
) -> MessageCreateRequest:
    expires_at_in_jst = poll_expires_at.astimezone(JST)
    content = (
        f"{human_member_count}人全員が投票したクポ～\n"
        f"https://discord.com/channels/{guild_id}/{thread_id}\n"
        "\n"
        f"ただ{format_date_with_weekday(expires_at_in_jst.date())}の"
        f"{expires_at_in_jst.hour}時までは投票し直せるから気をつけてクポ～"
    )
    return MessageCreateRequest(content=content)


def _format_reminder_text(poll_expires_at: datetime) -> str:
    expires_at_in_jst = poll_expires_at.astimezone(JST)
    return (
        f"{format_date_with_weekday(expires_at_in_jst.date())}の"
        f"{expires_at_in_jst.hour}時に投票を締め切るクポ～"
        "\n"
        "それまでにご投票お願いしますクポ。"
    )


def build_dm_reminder_message(
    guild_id: GuildId,
    channel_id: ChannelId,
    vote_message_id: MessageId,
    poll_expires_at: datetime,
) -> MessageCreateRequest:
    content = (
        f"{_format_reminder_text(poll_expires_at)}"
        "\n"
        f"https://discord.com/channels/{guild_id}/{channel_id}/{vote_message_id}"
    )
    return MessageCreateRequest(content=content)


def build_vote_channel_reminder_message(
    vote_message_id: MessageId, poll_expires_at: datetime
) -> MessageCreateRequest:
    content = _format_reminder_text(poll_expires_at)
    return MessageCreateRequest(
        content=content,
        message_reference={"message_id": vote_message_id},
    )


def get_display_name(guild_member: GuildMember) -> str:
    """Return the name shown in the server.

    Tries nick, then global name, then username, and falls back to the id.
    """
    user = guild_member["user"]
    if "nick" in guild_member and guild_member["nick"] is not None:
        return guild_member["nick"]
    if "global_name" in user and user["global_name"] is not None:
        return user["global_name"]
    if "username" in user:
        return user["username"]
    return user["id"]

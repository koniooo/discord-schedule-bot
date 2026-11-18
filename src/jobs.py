import logging
from datetime import date, datetime

from discord_api import (
    ChannelId,
    GuildId,
    Message,
    MessageCreateRequest,
    MessageId,
    PollResponse,
    UserId,
    add_reaction,
    create_dm_channel,
    get_answer_voters,
    get_channel_messages,
    get_current_user,
    get_thread_id_started_from,
    list_guild_members,
    post_message,
    start_thread_from_message,
)
from schedule import get_monday_to_sunday_after_next
from vote import (
    ALL_VOTED_REPORTED_EMOJI,
    COMMENT_THREAD_AUTO_ARCHIVE_MINUTES,
    COMMENT_THREAD_NAME_SUFFIX,
    build_all_voted_report_message,
    build_vote_message,
    collect_non_voter_ids,
    collect_voter_ids,
    find_latest_vote_message,
    format_comment_thread_name,
    get_poll_expires_at,
    has_own_reaction,
    is_human,
)

logger = logging.getLogger(__name__)


def start_vote(token: str, channel_id: ChannelId, today: date) -> None:
    candidate_days = get_monday_to_sunday_after_next(today)
    vote_message = post_message(token, channel_id, build_vote_message(candidate_days))

    thread_name = format_comment_thread_name(candidate_days)
    start_thread_from_message(
        token,
        channel_id,
        vote_message["id"],
        thread_name,
        COMMENT_THREAD_AUTO_ARCHIVE_MINUTES,
    )


def _find_vote_message(
    token: str, channel_id: ChannelId
) -> tuple[Message, PollResponse] | None:
    channel_messages = get_channel_messages(token, channel_id)
    bot_id = get_current_user(token)["id"]
    vote_message = find_latest_vote_message(channel_messages, bot_id)

    if vote_message is None:
        logger.warning("No vote message found in channel %s", channel_id)
        return None
    if "poll" not in vote_message:
        logger.warning("Vote message %s has no poll", vote_message["id"])
        return None
    return vote_message, vote_message["poll"]


def _fetch_voter_ids(
    token: str, channel_id: ChannelId, vote_message_id: MessageId, poll: PollResponse
) -> set[UserId]:
    poll_answer_ids = [answer["answer_id"] for answer in poll["answers"]]
    voters_per_answer = [
        get_answer_voters(token, channel_id, vote_message_id, poll_answer_id)
        for poll_answer_id in poll_answer_ids
    ]
    return collect_voter_ids(voters_per_answer)


def _format_vote_label(vote_message: Message) -> str:
    thread = vote_message.get("thread")
    thread_name = thread["name"] if thread is not None else "(no thread)"
    return thread_name.removesuffix(COMMENT_THREAD_NAME_SUFFIX).rstrip()


def _send_dm(token: str, recipient_id: UserId, body: MessageCreateRequest) -> None:
    dm_channel = create_dm_channel(token, recipient_id)
    post_message(token, dm_channel["id"], body)


def report_if_all_voted(
    token: str,
    channel_id: ChannelId,
    guild_id: GuildId,
    master_user_id: UserId,
    now: datetime,
) -> None:
    """DM the master once when every human member has voted on the open vote.

    Marks the vote message with ALL_VOTED_REPORTED_EMOJI after the DM is sent.
    `now` must be timezone-aware.
    """
    found = _find_vote_message(token, channel_id)
    if found is None:
        return
    vote_message, poll = found
    vote_message_id = vote_message["id"]

    poll_expires_at = get_poll_expires_at(poll)
    if now >= poll_expires_at:
        return
    if has_own_reaction(vote_message, ALL_VOTED_REPORTED_EMOJI):
        return

    voter_ids = _fetch_voter_ids(token, channel_id, vote_message_id, poll)
    guild_members = list_guild_members(token, guild_id)
    non_voter_ids = collect_non_voter_ids(guild_members, voter_ids)

    human_members = [
        guild_member for guild_member in guild_members if is_human(guild_member["user"])
    ]
    human_member_count = len(human_members)
    voted_count = human_member_count - len(non_voter_ids)

    logger.info(
        "Vote %s (%s): %d/%d members have voted",
        _format_vote_label(vote_message),
        vote_message_id,
        voted_count,
        human_member_count,
    )

    if non_voter_ids:
        return

    all_voted_report_message = build_all_voted_report_message(
        human_member_count,
        guild_id,
        get_thread_id_started_from(vote_message_id),
        poll_expires_at,
    )
    _send_dm(token, master_user_id, all_voted_report_message)
    add_reaction(token, channel_id, vote_message_id, ALL_VOTED_REPORTED_EMOJI)

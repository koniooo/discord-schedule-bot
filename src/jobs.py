import logging
from datetime import date, datetime

from discord_api import (
    CANNOT_SEND_MESSAGES_TO_USER,
    CANNOT_SEND_MESSAGES_TO_USER_NO_MUTUAL_GUILDS,
    ChannelId,
    DiscordApiError,
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
from schedule import format_date_range, get_monday_to_sunday_after_next
from vote import (
    ALL_VOTED_REPORTED_EMOJI,
    COMMENT_THREAD_AUTO_ARCHIVE_MINUTES,
    COMMENT_THREAD_NAME_SUFFIX,
    build_all_voted_report_message,
    build_dm_reminder_message,
    build_vote_channel_reminder_message,
    build_vote_message,
    collect_human_non_voter_ids,
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
    vote_message_id = vote_message["id"]
    date_range = format_date_range(candidate_days[0], candidate_days[-1])
    logger.info("Vote %s (%s): posted", vote_message_id, date_range)

    thread_name = format_comment_thread_name(candidate_days)
    start_thread_from_message(
        token,
        channel_id,
        vote_message_id,
        thread_name,
        COMMENT_THREAD_AUTO_ARCHIVE_MINUTES,
    )
    logger.info(
        "Vote %s (%s): started thread '%s'", vote_message_id, date_range, thread_name
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
        logger.warning(
            "Vote %s (%s): the message has no poll",
            vote_message["id"],
            _format_vote_label(vote_message),
        )
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
    thread_name = thread["name"] if thread is not None else "no thread"
    return thread_name.removesuffix(COMMENT_THREAD_NAME_SUFFIX).rstrip()


def _send_dm(token: str, recipient_id: UserId, body: MessageCreateRequest) -> None:
    dm_channel = create_dm_channel(token, recipient_id)
    post_message(token, dm_channel["id"], body)


def report_if_all_voted(
    token: str,
    guild_id: GuildId,
    channel_id: ChannelId,
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
    vote_label = _format_vote_label(vote_message)

    poll_expires_at = get_poll_expires_at(poll)
    if now >= poll_expires_at:
        return
    if has_own_reaction(vote_message, ALL_VOTED_REPORTED_EMOJI):
        return

    voter_ids = _fetch_voter_ids(token, channel_id, vote_message_id, poll)
    guild_members = list_guild_members(token, guild_id)
    human_non_voter_ids = collect_human_non_voter_ids(guild_members, voter_ids)

    human_members = [
        guild_member for guild_member in guild_members if is_human(guild_member["user"])
    ]
    human_member_count = len(human_members)
    voted_count = human_member_count - len(human_non_voter_ids)

    logger.info(
        "Vote %s (%s): %d/%d members have voted",
        vote_message_id,
        vote_label,
        voted_count,
        human_member_count,
    )

    if human_non_voter_ids:
        return

    all_voted_report_message = build_all_voted_report_message(
        human_member_count,
        guild_id,
        get_thread_id_started_from(vote_message_id),
        poll_expires_at,
    )
    _send_dm(token, master_user_id, all_voted_report_message)
    logger.info(
        "Vote %s (%s): sent the all-voted report to the master",
        vote_message_id,
        vote_label,
    )
    add_reaction(token, channel_id, vote_message_id, ALL_VOTED_REPORTED_EMOJI)


def send_reminders(
    token: str,
    guild_id: GuildId,
    channel_id: ChannelId,
    now: datetime,
) -> None:
    """DM a reminder to every human member who hasn't voted.

    If any reminder DM can't be delivered (DMs closed or another error),
    post one reminder in the vote channel as well.
    `now` must be timezone-aware.
    """
    found = _find_vote_message(token, channel_id)
    if found is None:
        return
    vote_message, poll = found
    vote_message_id = vote_message["id"]
    vote_label = _format_vote_label(vote_message)
    poll_expires_at = get_poll_expires_at(poll)
    if now >= poll_expires_at:
        logger.warning(
            "Vote %s (%s): already closed; no reminders sent",
            vote_message_id,
            vote_label,
        )
        return

    voter_ids = _fetch_voter_ids(token, channel_id, vote_message_id, poll)
    guild_members = list_guild_members(token, guild_id)
    human_non_voter_ids = collect_human_non_voter_ids(guild_members, voter_ids)
    if not human_non_voter_ids:
        logger.info(
            "Vote %s (%s): everyone has voted; no reminders needed",
            vote_message_id,
            vote_label,
        )
        return

    dm_sent_ids: list[UserId] = []
    dm_cannot_send_ids: list[UserId] = []
    dm_no_mutual_guild_ids: list[UserId] = []
    dm_failed_ids: list[UserId] = []
    dm_reminder_message = build_dm_reminder_message(
        guild_id, channel_id, vote_message_id, poll_expires_at
    )
    for human_non_voter_id in human_non_voter_ids:
        try:
            _send_dm(token, human_non_voter_id, dm_reminder_message)
        except DiscordApiError as error:
            if error.discord_code == CANNOT_SEND_MESSAGES_TO_USER:
                dm_cannot_send_ids.append(human_non_voter_id)
            elif error.discord_code == CANNOT_SEND_MESSAGES_TO_USER_NO_MUTUAL_GUILDS:
                dm_no_mutual_guild_ids.append(human_non_voter_id)
            else:
                logger.exception(
                    "Vote %s (%s): failed to send a reminder DM to %s",
                    vote_message_id,
                    vote_label,
                    human_non_voter_id,
                )
                dm_failed_ids.append(human_non_voter_id)
        else:
            dm_sent_ids.append(human_non_voter_id)

    logger.info(
        "Vote %s (%s): sent %d/%d reminder DMs; sent to: %s; cannot send to: %s; "
        "no mutual guilds with: %s; failed for: %s",
        vote_message_id,
        vote_label,
        len(dm_sent_ids),
        len(human_non_voter_ids),
        dm_sent_ids,
        dm_cannot_send_ids,
        dm_no_mutual_guild_ids,
        dm_failed_ids,
    )

    if dm_cannot_send_ids or dm_no_mutual_guild_ids or dm_failed_ids:
        vote_channel_reminder_message = build_vote_channel_reminder_message(
            vote_message_id, poll_expires_at
        )
        post_message(token, channel_id, vote_channel_reminder_message)

import logging
from datetime import date, datetime

from discord_api import (
    CANNOT_SEND_MESSAGES_TO_USER,
    CANNOT_SEND_MESSAGES_TO_USER_NO_MUTUAL_GUILDS,
    ChannelId,
    DiscordApiError,
    GuildId,
    GuildMember,
    Message,
    MessageCreateRequest,
    MessageId,
    PollResponse,
    UserId,
    add_reaction,
    create_dm_channel,
    format_error_details,
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
    collect_human_non_voters,
    collect_voter_ids,
    find_latest_vote_message,
    format_comment_thread_name,
    format_message_url,
    format_thread_url,
    get_display_name,
    get_poll_expires_at,
    has_own_reaction,
    is_human,
)

logger = logging.getLogger(__name__)


def _format_vote_log_prefix(vote_message_id: MessageId, vote_label: str) -> str:
    return f"Vote {vote_message_id} ({vote_label}):"


def start_vote(token: str, channel_id: ChannelId, today: date) -> None:
    candidate_days = get_monday_to_sunday_after_next(today)
    vote_message = post_message(token, channel_id, build_vote_message(candidate_days))
    vote_message_id = vote_message["id"]
    date_range = format_date_range(candidate_days[0], candidate_days[-1])
    log_prefix = _format_vote_log_prefix(vote_message_id, date_range)
    logger.info("%s posted", log_prefix)

    thread_name = format_comment_thread_name(candidate_days)
    start_thread_from_message(
        token,
        channel_id,
        vote_message_id,
        thread_name,
        COMMENT_THREAD_AUTO_ARCHIVE_MINUTES,
    )
    logger.info("%s started thread '%s'", log_prefix, thread_name)


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
        log_prefix = _format_vote_log_prefix(
            vote_message["id"], _format_vote_label(vote_message)
        )
        logger.warning("%s the message has no poll", log_prefix)
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


def _choose_report_url(
    guild_id: GuildId, channel_id: ChannelId, vote_message: Message, log_prefix: str
) -> str:
    if "thread" in vote_message:
        return format_thread_url(
            guild_id, get_thread_id_started_from(vote_message["id"])
        )
    logger.warning("%s linking to the vote message instead of the thread", log_prefix)
    return format_message_url(guild_id, channel_id, vote_message["id"])


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
    log_prefix = _format_vote_log_prefix(
        vote_message_id, _format_vote_label(vote_message)
    )

    poll_expires_at = get_poll_expires_at(poll)
    if now >= poll_expires_at:
        logger.debug("%s already closed", log_prefix)
        return
    if has_own_reaction(vote_message, ALL_VOTED_REPORTED_EMOJI):
        logger.debug("%s already reported", log_prefix)
        return

    voter_ids = _fetch_voter_ids(token, channel_id, vote_message_id, poll)
    guild_members = list_guild_members(token, guild_id)

    human_non_voters = collect_human_non_voters(guild_members, voter_ids)
    human_members = [
        guild_member for guild_member in guild_members if is_human(guild_member)
    ]
    human_member_count = len(human_members)
    voted_count = human_member_count - len(human_non_voters)

    logger.info(
        "%s %d/%d members have voted",
        log_prefix,
        voted_count,
        human_member_count,
    )

    if human_non_voters:
        return

    url = _choose_report_url(guild_id, channel_id, vote_message, log_prefix)
    all_voted_report_message = build_all_voted_report_message(
        human_member_count,
        url,
        poll_expires_at,
    )
    _send_dm(token, master_user_id, all_voted_report_message)
    logger.info("%s sent the all-voted report to the master", log_prefix)
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
    log_prefix = _format_vote_log_prefix(
        vote_message_id, _format_vote_label(vote_message)
    )
    poll_expires_at = get_poll_expires_at(poll)
    if now >= poll_expires_at:
        logger.warning("%s already closed; no reminders sent", log_prefix)
        return

    voter_ids = _fetch_voter_ids(token, channel_id, vote_message_id, poll)
    guild_members = list_guild_members(token, guild_id)

    human_non_voters = collect_human_non_voters(guild_members, voter_ids)
    if not human_non_voters:
        logger.info("%s everyone has voted; no reminders needed", log_prefix)
        return

    dm_sent_members: list[GuildMember] = []
    dm_failures: list[tuple[GuildMember, DiscordApiError]] = []
    dm_reminder_message = build_dm_reminder_message(
        format_message_url(guild_id, channel_id, vote_message_id), poll_expires_at
    )

    for human_non_voter in human_non_voters:
        try:
            _send_dm(token, human_non_voter["user"]["id"], dm_reminder_message)
        except DiscordApiError as error:
            dm_failures.append((human_non_voter, error))
            # Closed DMs are the member's choice; any other error is a problem.
            if error.discord_code not in (
                CANNOT_SEND_MESSAGES_TO_USER,
                CANNOT_SEND_MESSAGES_TO_USER_NO_MUTUAL_GUILDS,
            ):
                logger.exception(
                    "%s failed to send a reminder DM to %s",
                    log_prefix,
                    get_display_name(human_non_voter),
                )
        else:
            dm_sent_members.append(human_non_voter)

    member_parts: list[str] = []
    if dm_sent_members:
        sent_names = ", ".join(get_display_name(member) for member in dm_sent_members)
        member_parts.append(f"sent to: {sent_names}")
    if dm_failures:
        failures = ", ".join(
            f"{get_display_name(member)} ({format_error_details(error)})"
            for member, error in dm_failures
        )
        member_parts.append(f"not sent to: {failures}")
    logger.info(
        "%s sent %d/%d reminder DMs; %s",
        log_prefix,
        len(dm_sent_members),
        len(human_non_voters),
        "; ".join(member_parts),
    )

    if dm_failures:
        vote_channel_reminder_message = build_vote_channel_reminder_message(
            vote_message_id, poll_expires_at
        )
        post_message(token, channel_id, vote_channel_reminder_message)
        logger.info("%s posted a reminder in the vote channel", log_prefix)

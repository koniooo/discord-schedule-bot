import logging
from datetime import UTC, datetime
from typing import TypedDict

from config import get_log_level, get_required_env
from discord_api import ChannelId, GuildId, UserId
from jobs import close_vote, report_if_all_voted, send_reminders, start_vote
from schedule import JST

logger = logging.getLogger(__name__)


class ScheduledJobEvent(TypedDict):
    """The input that each EventBridge Scheduler schedule sends."""

    job: str
    scheduled_time: str


def lambda_handler(event: ScheduledJobEvent, _context: object) -> None:
    """Run the job named in the EventBridge Scheduler event.

    start_vote uses the scheduled time's JST date, so a retry after midnight
    still picks the same candidate week. The other jobs check the poll's
    current state, so they get the real current time.
    """

    # Lambda already gives the root logger a handler, so basicConfig would do nothing;
    # set the level directly.
    logging.getLogger().setLevel(get_log_level())
    job = event["job"]
    scheduled_time = event["scheduled_time"]
    logger.info("job: %s (scheduled at %s)", job, scheduled_time)

    token = get_required_env("DISCORD_BOT_TOKEN")
    guild_id = GuildId(get_required_env("DISCORD_GUILD_ID"))
    channel_id = ChannelId(get_required_env("DISCORD_CHANNEL_ID"))
    master_user_id = UserId(get_required_env("DISCORD_MASTER_USER_ID"))

    match job:
        case "start_vote":
            scheduled_at = datetime.fromisoformat(scheduled_time)
            today = scheduled_at.astimezone(JST).date()
            start_vote(token, channel_id, today)
        case "report_if_all_voted":
            report_if_all_voted(
                token, guild_id, channel_id, master_user_id, datetime.now(UTC)
            )
        case "send_reminders":
            send_reminders(token, guild_id, channel_id, datetime.now(UTC))
        case "close_vote":
            close_vote(token, guild_id, channel_id, master_user_id, datetime.now(UTC))
        case _:
            raise ValueError(f"Unknown job: {job!r}")

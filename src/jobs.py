from datetime import date

from discord_api import ChannelId, post_message, start_thread_from_message
from schedule import get_monday_to_sunday_after_next
from vote import build_vote_message, format_comment_thread_name


def start_vote(token: str, channel_id: ChannelId, today: date) -> None:
    candidate_days = get_monday_to_sunday_after_next(today)
    message = post_message(token, channel_id, build_vote_message(candidate_days))

    thread_name = format_comment_thread_name(candidate_days)
    start_thread_from_message(token, channel_id, message["id"], thread_name)

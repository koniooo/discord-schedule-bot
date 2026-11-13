from datetime import date
from pprint import pprint
from urllib.error import HTTPError

from dotenv import load_dotenv

from config import get_required_env
from discord_api import ChannelId, MessageId, post_message, start_thread_from_message
from schedule import (
    format_date_range,
    get_monday_to_sunday_after_next,
)
from vote import build_vote_message


def main() -> None:
    load_dotenv()
    token = get_required_env("DISCORD_BOT_TOKEN")
    channel_id = ChannelId(get_required_env("DISCORD_CHANNEL_ID"))
    candidate_days = get_monday_to_sunday_after_next(date.today())

    message = post_message(token, channel_id, build_vote_message(candidate_days))

    thread_name = (
        f"{format_date_range(candidate_days[0], candidate_days[-1])} 💬コメント"
    )
    start_thread_from_message(token, channel_id, MessageId(message["id"]), thread_name)


if __name__ == "__main__":
    try:
        main()
    except HTTPError as error:
        pprint(error.read().decode())
        raise

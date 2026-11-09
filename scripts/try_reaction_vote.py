from datetime import date
from pprint import pprint
from urllib.error import HTTPError

from dotenv import load_dotenv

from config import get_required_env
from discord_api import SUPPRESS_NOTIFICATIONS, add_reaction, post_message
from schedule import WEEKDAY_NAMES, get_monday_to_sunday_after_next
from vote import VOTE_CHOICES


def main() -> None:
    load_dotenv()
    token = get_required_env("DISCORD_BOT_TOKEN")
    channel_id = get_required_env("DISCORD_CHANNEL_ID")
    post_message(
        token,
        channel_id,
        {
            "content": "再来週のスケジュールを決めるクポ～。ご投票お願いしますクポ。 @everyone",
            "allowed_mentions": {"parse": ["everyone"]},
        },
    )
    for day in get_monday_to_sunday_after_next(date.today()):
        message = post_message(
            token,
            channel_id,
            {
                "content": f"{day.month}/{day.day}({WEEKDAY_NAMES[day.weekday()]})",
                "flags": SUPPRESS_NOTIFICATIONS,
            },
        )
        for emoji, _label in VOTE_CHOICES:
            add_reaction(token, channel_id, message["id"], emoji)


if __name__ == "__main__":
    try:
        main()
    except HTTPError as error:
        pprint(error.read().decode())
        raise

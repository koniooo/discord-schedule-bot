from datetime import date
from pprint import pprint
from urllib.error import HTTPError

from dotenv import load_dotenv

from config import get_required_env
from discord_api import SUPPRESS_NOTIFICATIONS, post_message
from schedule import get_monday_to_sunday_after_next

IS_COMPONENTS_V2 = 1 << 15


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
    for _day in get_monday_to_sunday_after_next(date.today()):
        post_message(
            token,
            channel_id,
            {
                "flags": IS_COMPONENTS_V2 | SUPPRESS_NOTIFICATIONS,
                "components": [
                    {"type": 10, "content": "11/23(月)"},
                    {
                        "type": 1,
                        "components": [
                            {
                                "type": 2,
                                "style": 3,
                                "emoji": {"name": "👍"},
                                "custom_id": "vote: 2026-11-23:yes",
                            },
                            {
                                "type": 2,
                                "style": 2,
                                "emoji": {"name": "❓"},
                                "custom_id": "vote: 2026-11-23:undetermined",
                            },
                            {
                                "type": 2,
                                "style": 4,
                                "emoji": {"name": "👎"},
                                "custom_id": "vote: 2026-11-23:no",
                            },
                        ],
                    },
                ],
            },
        )


if __name__ == "__main__":
    try:
        main()
    except HTTPError as error:
        pprint(error.read().decode())
        raise

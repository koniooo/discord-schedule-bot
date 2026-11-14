from datetime import date
from pprint import pprint
from urllib.error import HTTPError

from dotenv import load_dotenv

from config import get_required_env
from discord_api import ChannelId
from jobs import start_vote


def main() -> None:
    load_dotenv()
    token = get_required_env("DISCORD_BOT_TOKEN")
    channel_id = ChannelId(get_required_env("DISCORD_CHANNEL_ID"))

    start_vote(token, channel_id, date.today())


if __name__ == "__main__":
    try:
        main()
    except HTTPError as error:
        pprint(error.read().decode())
        raise

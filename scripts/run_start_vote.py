import logging
from datetime import datetime

from dotenv import load_dotenv

from config import get_required_env
from discord_api import ChannelId
from jobs import start_vote
from schedule import JST


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    load_dotenv()
    token = get_required_env("DISCORD_BOT_TOKEN")
    channel_id = ChannelId(get_required_env("DISCORD_CHANNEL_ID"))

    start_vote(token, channel_id, datetime.now(JST).date())


if __name__ == "__main__":
    main()

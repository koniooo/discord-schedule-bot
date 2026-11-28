import logging
from datetime import UTC, datetime

from dotenv import load_dotenv

from config import get_log_level, get_required_env
from discord_api import ChannelId, GuildId
from jobs import send_reminders


def main() -> None:
    load_dotenv()
    logging.basicConfig(level=get_log_level())
    token = get_required_env("DISCORD_BOT_TOKEN")
    guild_id = GuildId(get_required_env("DISCORD_GUILD_ID"))
    channel_id = ChannelId(get_required_env("DISCORD_CHANNEL_ID"))

    send_reminders(token, guild_id, channel_id, datetime.now(UTC))


if __name__ == "__main__":
    main()

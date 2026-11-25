import logging
from datetime import UTC, datetime

from dotenv import load_dotenv

from config import get_required_env
from discord_api import ChannelId, GuildId, UserId
from jobs import close_vote


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    load_dotenv()
    token = get_required_env("DISCORD_BOT_TOKEN")
    channel_id = ChannelId(get_required_env("DISCORD_CHANNEL_ID"))
    guild_id = GuildId(get_required_env("DISCORD_GUILD_ID"))
    master_user_id = UserId(get_required_env("DISCORD_MASTER_USER_ID"))
    close_vote(token, guild_id, channel_id, master_user_id, datetime.now(UTC))


if __name__ == "__main__":
    main()

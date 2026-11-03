import os

from dotenv import load_dotenv


def get_bot_token() -> str:
    load_dotenv()
    return os.environ["DISCORD_BOT_TOKEN"]

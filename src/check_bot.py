from pprint import pprint

from dotenv import load_dotenv

from config import get_bot_token, get_required_env
from discord_api import get_current_user, post_message


def main() -> None:
    load_dotenv()
    token = get_bot_token()
    channel_id = get_required_env("DISCORD_CHANNEL_ID")
    current_user = get_current_user(token)
    pprint(current_user)
    posted_message = post_message(token, channel_id, {"content": "hello"})
    pprint(posted_message)


if __name__ == "__main__":
    main()

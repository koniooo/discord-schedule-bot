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
    post_response = post_message(token, channel_id, {"content": "Fuck u"})
    pprint(post_response)


if __name__ == "__main__":
    main()

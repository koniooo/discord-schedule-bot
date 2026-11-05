from dotenv import load_dotenv

from config import get_bot_token
from discord_api import get_current_user


def main() -> None:
    load_dotenv()
    token = get_bot_token()
    current_user = get_current_user(token)
    print(current_user["username"])


if __name__ == "__main__":
    main()

import os


def get_required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:  # Reject both unset (None) and empty-string values
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def get_bot_token() -> str:
    return get_required_env("DISCORD_BOT_TOKEN")

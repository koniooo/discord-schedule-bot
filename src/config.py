import os
from typing import Literal

type EnvVarName = Literal["DISCORD_BOT_TOKEN", "DISCORD_CHANNEL_ID"]


def get_required_env(name: EnvVarName) -> str:
    value = os.environ.get(name)
    if not value:  # Reject both unset (None) and empty-string values
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value

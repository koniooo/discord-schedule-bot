import logging
import os
from typing import Literal

from discord_api import UserId

type EnvVarName = Literal[
    "DISCORD_BOT_TOKEN",
    "DISCORD_GUILD_ID",
    "DISCORD_CHANNEL_ID",
    "DISCORD_MASTER_USER_ID",
    "DISCORD_DEEP_DUNGEON_MEMBER_IDS",
    "LOG_LEVEL",
]

logger = logging.getLogger(__name__)


def get_required_env(name: EnvVarName) -> str:
    value = os.environ.get(name)
    if not value:  # Reject both unset (None) and empty-string values
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def get_deep_dungeon_member_ids() -> list[UserId]:
    """Return the 4 Deep Dungeon members' ids from the env var, in the given order."""
    name: EnvVarName = "DISCORD_DEEP_DUNGEON_MEMBER_IDS"
    raw_value = get_required_env(name)
    member_ids = [value.strip() for value in raw_value.split(",")]
    if len(member_ids) != 4:
        raise RuntimeError(f"{name} must have exactly 4 ids, got {len(member_ids)}")
    for member_id in member_ids:
        if member_id == "":
            raise RuntimeError(f"{name} has an empty id")
    for member_id in member_ids:
        if not (member_id.isascii() and member_id.isdigit()):
            raise RuntimeError(f"{name} ids must be digits only, got {member_id!r}")
    seen: set[str] = set()
    for member_id in member_ids:
        if member_id in seen:
            raise RuntimeError(f"{name} has a duplicate id: {member_id!r}")
        seen.add(member_id)
    return [UserId(member_id) for member_id in member_ids]


def get_log_level() -> str:
    """Return LOG_LEVEL upper-cased; warn and return "INFO" if missing or invalid."""
    name: EnvVarName = "LOG_LEVEL"
    value = os.environ.get(name)
    if not value:
        logger.warning("%s is not set; using INFO", name)
        return "INFO"
    level = value.upper()
    if level not in logging.getLevelNamesMapping():
        logger.warning("%s %r is not a valid level; using INFO", name, value)
        return "INFO"
    return level

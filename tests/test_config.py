import pytest

from config import get_deep_dungeon_member_ids, get_required_env
from discord_api import UserId


def test_get_required_env_returns_value_when_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "dummy-token")
    assert get_required_env("DISCORD_BOT_TOKEN") == "dummy-token"


def test_get_required_env_raises_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DISCORD_BOT_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="DISCORD_BOT_TOKEN"):
        get_required_env("DISCORD_BOT_TOKEN")


def test_get_required_env_raises_when_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "")
    with pytest.raises(RuntimeError, match="DISCORD_BOT_TOKEN"):
        get_required_env("DISCORD_BOT_TOKEN")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(
            "4003,4001,4004,4002", ["4003", "4001", "4004", "4002"], id="unsorted_ids"
        ),
        pytest.param(
            " 4001 ,4002, 4003 , 4004 ",
            ["4001", "4002", "4003", "4004"],
            id="spaces_around_ids",
        ),
    ],
)
def test_get_deep_dungeon_member_ids_returns_ids_in_order(
    value: str, expected: list[UserId], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DISCORD_DEEP_DUNGEON_MEMBER_IDS", value)
    assert get_deep_dungeon_member_ids() == expected


@pytest.mark.parametrize(
    ("value", "match"),
    [
        pytest.param("4001,4002,4003", "exactly 4", id="too_few"),
        pytest.param("4001,4002,4003,4004,4005", "exactly 4", id="too_many"),
        pytest.param("4001,,4003,4004", "empty", id="empty_id"),
        pytest.param("4001,abc,4003,4004", "digits", id="not_a_number"),
        # Full-width digits pass str.isdigit(), but aren't valid Discord ids.
        pytest.param(
            "４００１,4002,4003,4004",  # noqa: RUF001
            "digits",
            id="full_width_digits",
        ),
        pytest.param("4001,4001,4003,4004", "duplicate", id="duplicate_id"),
    ],
)
def test_get_deep_dungeon_member_ids_raises_when_value_is_invalid(
    value: str,
    match: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DISCORD_DEEP_DUNGEON_MEMBER_IDS", value)
    with pytest.raises(RuntimeError, match=match):
        get_deep_dungeon_member_ids()


def test_get_deep_dungeon_member_ids_raises_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DISCORD_DEEP_DUNGEON_MEMBER_IDS", raising=False)
    with pytest.raises(RuntimeError, match="DISCORD_DEEP_DUNGEON_MEMBER_IDS"):
        get_deep_dungeon_member_ids()

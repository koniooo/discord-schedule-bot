import logging

import pytest

from config import get_deep_dungeon_member_ids, get_log_level, get_required_env
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


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param("WARNING", "WARNING", id="upper_case"),
        pytest.param("debug", "DEBUG", id="lower_case"),
    ],
)
def test_get_log_level_returns_value_in_upper_case(
    value: str,
    expected: str,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setenv("LOG_LEVEL", value)
    caplog.set_level(logging.DEBUG, logger="config")

    assert get_log_level() == expected
    assert caplog.record_tuples == []


@pytest.mark.parametrize(
    ("value", "log_text"),
    [
        pytest.param(
            "INVALID",
            "LOG_LEVEL 'INVALID' is not a valid level; using INFO",
            id="invalid",
        ),
        pytest.param("", "LOG_LEVEL is not set; using INFO", id="empty"),
    ],
)
def test_get_log_level_returns_info_and_warns_when_empty_or_invalid(
    value: str,
    log_text: str,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setenv("LOG_LEVEL", value)
    caplog.set_level(logging.WARNING, logger="config")

    assert get_log_level() == "INFO"
    assert caplog.record_tuples == [("config", logging.WARNING, log_text)]


def test_get_log_level_returns_info_and_warns_when_unset(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    caplog.set_level(logging.WARNING, logger="config")

    assert get_log_level() == "INFO"
    assert caplog.record_tuples == [
        ("config", logging.WARNING, "LOG_LEVEL is not set; using INFO")
    ]

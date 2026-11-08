import pytest

from config import get_required_env


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

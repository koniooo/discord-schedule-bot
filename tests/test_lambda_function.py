import logging
from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import cast

import pytest

import lambda_function
from lambda_function import ScheduledJobEvent, lambda_handler

type JobCall = tuple[str, tuple[object, ...]]


class FakeJobs:
    """Replaces the four jobs and records which one ran with which arguments."""

    def __init__(self) -> None:
        self.calls: list[JobCall] = []

    def make(self, job: str) -> Callable[..., None]:
        def fake_job(*args: object) -> None:
            self.calls.append((job, args))

        return fake_job


@pytest.fixture
def fake_jobs(monkeypatch: pytest.MonkeyPatch) -> FakeJobs:
    fake = FakeJobs()
    for job in ("start_vote", "report_if_all_voted", "send_reminders", "close_vote"):
        monkeypatch.setattr(lambda_function, job, fake.make(job))
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "dummy-token")
    monkeypatch.setenv("DISCORD_GUILD_ID", "1001")
    monkeypatch.setenv("DISCORD_CHANNEL_ID", "2000")
    monkeypatch.setenv("DISCORD_MASTER_USER_ID", "4003")
    return fake


@pytest.mark.parametrize(
    ("scheduled_time", "expected_today"),
    [
        # Sun 12:00 JST, the posting time.
        pytest.param("2026-11-29T03:00:00Z", date(2026, 11, 29), id="sunday_noon"),
        # 11/28 in UTC is already 11/29 00:30 in JST.
        pytest.param(
            "2026-11-28T15:30:00Z", date(2026, 11, 29), id="previous_day_in_utc"
        ),
    ],
)
def test_lambda_handler_runs_start_vote_with_scheduled_jst_date(
    scheduled_time: str, expected_today: date, fake_jobs: FakeJobs
) -> None:
    lambda_handler({"job": "start_vote", "scheduled_time": scheduled_time}, None)

    assert fake_jobs.calls == [
        ("start_vote", ("dummy-token", "2000", expected_today)),
    ]


@pytest.mark.parametrize(
    ("job", "expected_settings"),
    [
        pytest.param(
            "report_if_all_voted",
            ("dummy-token", "1001", "2000", "4003"),
            id="report_if_all_voted",
        ),
        pytest.param(
            "send_reminders", ("dummy-token", "1001", "2000"), id="send_reminders"
        ),
        pytest.param(
            "close_vote", ("dummy-token", "1001", "2000", "4003"), id="close_vote"
        ),
    ],
)
def test_lambda_handler_runs_other_jobs_with_settings_and_real_current_time(
    job: str, expected_settings: tuple[str, ...], fake_jobs: FakeJobs
) -> None:
    before = datetime.now(UTC)

    # Scheduled long ago, so a scheduled time passed as "now" would show.
    lambda_handler({"job": job, "scheduled_time": "2026-01-01T00:00:00Z"}, None)

    after = datetime.now(UTC)
    [(called_job, args)] = fake_jobs.calls
    assert called_job == job
    assert args[:-1] == expected_settings
    now = args[-1]
    assert isinstance(now, datetime)
    assert now.tzinfo is not None
    assert before <= now <= after


def test_lambda_handler_raises_for_unknown_job(fake_jobs: FakeJobs) -> None:
    with pytest.raises(ValueError, match="Unknown job: 'oops'"):
        lambda_handler({"job": "oops", "scheduled_time": "2026-11-29T03:00:00Z"}, None)

    assert fake_jobs.calls == []


def test_lambda_handler_raises_without_scheduled_time(fake_jobs: FakeJobs) -> None:
    event = cast("ScheduledJobEvent", {"job": "start_vote"})

    with pytest.raises(KeyError, match="scheduled_time"):
        lambda_handler(event, None)

    assert fake_jobs.calls == []


def test_lambda_handler_raises_for_scheduled_time_not_in_iso_format(
    fake_jobs: FakeJobs,
) -> None:
    with pytest.raises(ValueError, match="Invalid isoformat string"):
        lambda_handler({"job": "start_vote", "scheduled_time": "Sunday noon"}, None)

    assert fake_jobs.calls == []


def test_lambda_handler_logs_job_and_scheduled_time_first(
    fake_jobs: FakeJobs, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger="lambda_function")

    lambda_handler(
        {"job": "start_vote", "scheduled_time": "2026-11-29T03:00:00Z"}, None
    )

    assert caplog.messages[0] == "job: start_vote (scheduled at 2026-11-29T03:00:00Z)"
    assert [job for job, _ in fake_jobs.calls] == ["start_vote"]

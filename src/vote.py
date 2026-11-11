from datetime import date
from typing import TypedDict

from schedule import format_date_with_weekday

NO_AVAILABLE_DAY_TEXT = "どの日も難しい"


class PollMedia(TypedDict):
    text: str


class PollAnswer(TypedDict):
    poll_media: PollMedia


def build_poll_answers(days: list[date]) -> list[PollAnswer]:
    answers: list[PollAnswer] = [
        {"poll_media": {"text": format_date_with_weekday(day)}} for day in days
    ]
    return answers + [{"poll_media": {"text": NO_AVAILABLE_DAY_TEXT}}]

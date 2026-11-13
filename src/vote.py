from datetime import date
from typing import TypedDict

from discord_api import AllowedMentions, PollAnswer, PollCreateRequest
from schedule import format_date_with_weekday

NO_AVAILABLE_DAY_TEXT = "どの日も難しい"

VOTE_ANNOUNCEMENT_TEXT = (
    "再来週のスケジュールを決めるクポ～。ご投票お願いしますクポ。\n\n"
    "「この日は遅れるかも・まだわからない」といったコメントは、このメッセージにぶら下がってるスレッドへどうぞクポ。"
)

POLL_QUESTION_TEXT = "参加可能日 (22:00～23:30)"

VOTE_DURATION_HOURS = 24 * 7


class VoteMessage(TypedDict):
    content: str
    allowed_mentions: AllowedMentions
    poll: PollCreateRequest


def build_poll_answers(candidate_days: list[date]) -> list[PollAnswer]:
    answers: list[PollAnswer] = [
        {"poll_media": {"text": format_date_with_weekday(day)}}
        for day in candidate_days
    ]
    return answers + [{"poll_media": {"text": NO_AVAILABLE_DAY_TEXT}}]


def build_vote_message(candidate_days: list[date]) -> VoteMessage:
    return {
        "content": f"{VOTE_ANNOUNCEMENT_TEXT} @everyone",
        "allowed_mentions": {"parse": ["everyone"]},
        "poll": {
            "question": {"text": POLL_QUESTION_TEXT},
            "answers": build_poll_answers(candidate_days),
            "duration": VOTE_DURATION_HOURS,
            "allow_multiselect": True,
        },
    }

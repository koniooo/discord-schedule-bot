from datetime import date
from pprint import pprint
from urllib.error import HTTPError

from dotenv import load_dotenv

from config import get_required_env
from discord_api import post_message, start_thread_from_message
from schedule import WEEKDAY_NAMES, format_date_range, get_monday_to_sunday_after_next


def main() -> None:
    load_dotenv()
    token = get_required_env("DISCORD_BOT_TOKEN")
    channel_id = get_required_env("DISCORD_CHANNEL_ID")
    candidate_days = get_monday_to_sunday_after_next(date.today())
    answers = [
        {
            "poll_media": {
                "text": f"{day.month}/{day.day} ({WEEKDAY_NAMES[day.weekday()]})",
            }
        }
        for day in candidate_days
    ] + [{"poll_media": {"text": "どの日も難しい"}}]

    message = post_message(
        token,
        channel_id,
        {
            "content": (
                "再来週のスケジュールを決めるクポ～。ご投票お願いしますクポ。\n\n"
                "「この日は遅れるかも・まだわからない」といったコメントは、このメッセージにぶら下がってるスレッドへどうぞクポ。 @everyone"
            ),
            "allowed_mentions": {"parse": ["everyone"]},
            "poll": {
                "question": {"text": "参加可能日 (22:00～23:30)"},
                "answers": answers,
                "duration": 24 * 7,
                "allow_multiselect": True,
            },
        },
    )

    thread_name = (
        f"{format_date_range(candidate_days[0], candidate_days[-1])} 💬コメント"
    )
    start_thread_from_message(token, channel_id, message["id"], thread_name)


if __name__ == "__main__":
    try:
        main()
    except HTTPError as error:
        pprint(error.read().decode())
        raise

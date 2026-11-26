"""Date and time helpers for the vote schedule. Weeks start on Monday (ISO 8601)."""

from datetime import date, timedelta
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")

_WEEKDAY_NAMES = ("月", "火", "水", "木", "金", "土", "日")


def get_monday_of_week(day: date) -> date:
    return day - timedelta(days=day.weekday())


def get_nearest_monday(day: date) -> date:
    """Return the Monday closest to the day.

    That's this week's Monday from Monday to Thursday (at most 3 days back),
    and next week's Monday from Friday to Sunday (at most 3 days ahead).
    """
    monday = get_monday_of_week(day)
    if day.weekday() <= 3:
        return monday
    return monday + timedelta(weeks=1)


def get_seven_days_from(start: date) -> list[date]:
    return [start + timedelta(days=offset) for offset in range(7)]


def get_week_after_nearest_monday(day: date) -> list[date]:
    """Return Monday to Sunday of the week after the Monday closest to the day.

    From Sunday, Monday or Tuesday, that's the week that starts on the coming
    Monday, e.g. Sun 11/22, Mon 11/23 and Tue 11/24 all give Mon 11/30 to Sun 12/6.
    """
    monday_after_nearest = get_nearest_monday(day) + timedelta(weeks=1)
    return get_seven_days_from(monday_after_nearest)


def format_date_with_weekday(day: date) -> str:
    return f"{day.month}/{day.day} ({_WEEKDAY_NAMES[day.weekday()]})"


def format_date_range(start: date, end: date) -> str:
    start_label = f"{start.month}/{start.day}"
    end_label = f"{end.month}/{end.day}" if start.month != end.month else f"{end.day}"
    return f"{start_label}-{end_label}"

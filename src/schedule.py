"""Date helpers for vote candidates. Weeks start on Monday (ISO 8601)."""

from datetime import date, timedelta


def get_monday_of_week(day: date) -> date:
    return day - timedelta(days=day.weekday())


def get_seven_days_from(start: date) -> list[date]:
    return [start + timedelta(days=i) for i in range(7)]


def get_monday_to_sunday_after_next(day: date) -> list[date]:
    monday_after_next = get_monday_of_week(day) + timedelta(weeks=2)
    return get_seven_days_from(monday_after_next)

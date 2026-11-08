from datetime import date, timedelta


def get_monday_of_week(day: date) -> date:
    return day - timedelta(days=day.weekday())

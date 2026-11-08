from datetime import date, timedelta


def get_monday_of_week(day: date) -> date:
    return day - timedelta(days=day.weekday())


def get_seven_days_from(start: date) -> list[date]:
    return [start + timedelta(days=i) for i in range(7)]

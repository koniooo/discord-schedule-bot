from vote import search_most_voted_day


def test_returns_day_with_most_votes() -> None:
    assert search_most_voted_day({"Mon": 1, "Tue": 5, "Wed": 3}) == ("Tue", 5)


def test_returns_first_day_when_votes_are_tied() -> None:
    assert search_most_voted_day({"Mon": 4, "Tue": 2, "Wed": 4}) == ("Mon", 4)


def test_returns_none_when_no_votes() -> None:
    assert search_most_voted_day({}) is None

def find_most_voted_day(vote_counts: dict[str, int]) -> tuple[str, int] | None:
    if not vote_counts:
        return None
    return max(vote_counts.items(), key=lambda pair: pair[1])

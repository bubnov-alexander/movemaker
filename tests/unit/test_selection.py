from movie_shorts.models import Candidate, ScoreBreakdown
from movie_shorts.services.candidates import select_candidates


def scored(identifier: int, start: float, end: float, total: float) -> Candidate:
    return Candidate(identifier, start, end, (), "", ScoreBreakdown(0, 0, 0, 0, total))


def test_selection_keeps_highest_scored_non_overlapping_candidates() -> None:
    selected = select_candidates(
        [scored(1, 0, 50, 90), scored(2, 40, 80, 99), scored(3, 81, 110, 80)],
        2,
    )

    assert [item.id for item in selected] == [2, 3]

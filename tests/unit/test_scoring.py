from movie_shorts.models import Candidate
from movie_shorts.services.scoring import duration_score, keyword_score, prefilter_candidates, score_candidates


def test_text_score_is_case_insensitive_for_russian_keywords() -> None:
    assert keyword_score("Беги! Там монстр.", {"беги": 18, "монстр": 25}) == 43


def test_duration_score_prefers_35_to_75_seconds() -> None:
    assert duration_score(50) > duration_score(20)
    assert duration_score(50) > duration_score(115)


def test_score_breakdown_has_weighted_total(tmp_path) -> None:
    candidate = Candidate(1, 0, 50, (1,), "беги")

    scored = score_candidates([candidate], tmp_path / "x.mp4", has_audio=False)

    assert scored[0].score is not None
    assert 0 <= scored[0].score.total <= 100


def test_prefilter_limits_candidates_by_text_and_duration() -> None:
    candidates = [
        Candidate(1, 0, 50, (), "беги монстр"),
        Candidate(2, 60, 110, (), ""),
    ]

    assert [item.id for item in prefilter_candidates(candidates, limit=1)] == [1]


def test_prefilter_distributes_equal_score_candidates_across_video() -> None:
    candidates = [
        Candidate(1, 0, 40, (1,), ""),
        Candidate(2, 50, 90, (2,), ""),
        Candidate(3, 100, 140, (3,), ""),
        Candidate(4, 150, 190, (4,), ""),
    ]

    selected = prefilter_candidates(candidates, limit=2)

    assert [item.id for item in selected] == [2, 3]


def test_precise_scoring_reports_each_candidate_progress(tmp_path) -> None:
    messages: list[tuple[int, int]] = []
    candidates = [Candidate(1, 0, 50, (), ""), Candidate(2, 60, 110, (), "")]

    score_candidates(candidates, tmp_path / "x.mp4", has_audio=False, progress=lambda current, total: messages.append((current, total)))

    assert messages == [(1, 2), (2, 2)]

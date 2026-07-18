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

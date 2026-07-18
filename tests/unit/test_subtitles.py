from movie_shorts.models import WordTiming
from movie_shorts.services.subtitles import build_ass


def test_ass_contains_russian_style_and_relative_timestamps() -> None:
    ass = build_ass((WordTiming(10.0, 10.5, "Привет"),), video_start=10.0)

    assert "PlayResY: 1920" in ass
    assert "0:00:00.00" in ass
    assert "Привет" in ass

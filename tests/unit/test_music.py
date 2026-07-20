from pathlib import Path

from movie_shorts.config import BackgroundMusicConfig
from movie_shorts.models import Candidate, ScoreBreakdown
from movie_shorts.services.music import select_background_music


def music_config(epic_threshold: float = 60.0) -> BackgroundMusicConfig:
    return BackgroundMusicConfig(
        epic_path=Path("music/yaya.mp3"),
        calm_path=Path("music/altyn.mp3"),
        epic_threshold=epic_threshold,
    )


def test_selects_epic_track_when_all_signals_are_high() -> None:
    candidate = Candidate(1, 0, 30, (), "беги монстр", ScoreBreakdown(90, 80, 70, 100, 85))

    selection = select_background_music(candidate, music_config())

    assert selection.track == "epic"
    assert selection.path == Path("music/yaya.mp3")


def test_selects_calm_track_for_low_energy_dialogue() -> None:
    candidate = Candidate(1, 0, 30, (), "давай поговорим", ScoreBreakdown(5, 10, 10, 100, 25))

    selection = select_background_music(candidate, music_config())

    assert selection.track == "calm"
    assert selection.path == Path("music/altyn.mp3")

import pytest

from pathlib import Path

from movie_shorts.config import BackgroundMusicConfig, load_run_config
from movie_shorts.errors import UserFacingError


def test_cli_options_override_yaml_values(tmp_path) -> None:
    config_path = tmp_path / "settings.yaml"
    config_path.write_text("count: 3\nmin_duration: 30\n", encoding="utf-8")

    config = load_run_config("film.mp4", tmp_path / "out", config_path, count=5)

    assert config.count == 5
    assert config.min_duration == 30


def test_rejects_non_positive_analysis_limit(tmp_path) -> None:
    config_path = tmp_path / "settings.yaml"
    config_path.write_text("analysis_limit: 0\n", encoding="utf-8")

    with pytest.raises(UserFacingError, match="Лимит анализа должен быть больше нуля"):
        load_run_config("film.mp4", tmp_path / "out", config_path)


def test_reads_skip_intro_from_yaml(tmp_path) -> None:
    config_path = tmp_path / "settings.yaml"
    config_path.write_text("skip_intro: 120\n", encoding="utf-8")

    config = load_run_config("film.mp4", tmp_path / "out", config_path)

    assert config.skip_intro == 120


def test_reads_background_music_from_yaml(tmp_path) -> None:
    config_path = tmp_path / "settings.yaml"
    config_path.write_text(
        "background_music:\n  epic_path: music/yaya.mp3\n  calm_path: music/altyn.mp3\n"
        "  max_volume: 0.1\n  quiet_volume: 0.16\n  epic_threshold: 55\n",
        encoding="utf-8",
    )

    config = load_run_config("film.mp4", tmp_path / "out", config_path)

    assert config.background_music == BackgroundMusicConfig(
        Path("music/yaya.mp3"),
        Path("music/altyn.mp3"),
        0.1,
        0.16,
        55,
    )


def test_skip_outro_defaults_to_sixty_seconds(tmp_path) -> None:
    config = load_run_config("film.mp4", tmp_path / "out")

    assert config.skip_outro == 60


def test_reads_skip_outro_from_yaml(tmp_path) -> None:
    config_path = tmp_path / "settings.yaml"
    config_path.write_text("skip_outro: 45\n", encoding="utf-8")

    config = load_run_config("film.mp4", tmp_path / "out", config_path)

    assert config.skip_outro == 45

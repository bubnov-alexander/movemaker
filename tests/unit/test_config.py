import pytest

from movie_shorts.config import load_run_config
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

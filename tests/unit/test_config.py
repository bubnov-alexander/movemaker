from movie_shorts.config import load_run_config


def test_cli_options_override_yaml_values(tmp_path) -> None:
    config_path = tmp_path / "settings.yaml"
    config_path.write_text("count: 3\nmin_duration: 30\n", encoding="utf-8")

    config = load_run_config("film.mp4", tmp_path / "out", config_path, count=5)

    assert config.count == 5
    assert config.min_duration == 30

from typer.testing import CliRunner

from movie_shorts.cli import app
from movie_shorts.pipeline import RunReport
from movie_shorts.errors import UserFacingError


def test_help_is_in_russian() -> None:
    result = CliRunner().invoke(app, ["create", "--help"])

    assert result.exit_code == 0
    assert "Создать Shorts" in result.output


def test_rejects_non_positive_count(tmp_path) -> None:
    result = CliRunner().invoke(
        app,
        ["create", "video.mp4", "--output", str(tmp_path), "--count", "0"],
    )

    assert result.exit_code == 2
    assert "Количество роликов должно быть" in result.output


def test_create_runs_pipeline_and_reports_result(monkeypatch, tmp_path) -> None:
    source = tmp_path / "film.mp4"
    source.touch()
    output = tmp_path / "output"

    monkeypatch.setattr(
        "movie_shorts.cli.Pipeline.run",
        lambda self, config, **kwargs: RunReport((), ("Создано 0 из 5 роликов",)),
    )

    result = CliRunner().invoke(app, ["create", str(source), "--output", str(output)])

    assert result.exit_code == 1
    assert "Создано 0 из 5 роликов" in result.output


def test_create_reads_count_from_yaml_config(monkeypatch, tmp_path) -> None:
    source = tmp_path / "film.mp4"
    source.touch()
    config_file = tmp_path / "config.yaml"
    config_file.write_text("count: 3\n", encoding="utf-8")
    captured = {}

    def fake_run(self, config, **kwargs):
        captured["count"] = config.count
        return RunReport((), ())

    monkeypatch.setattr("movie_shorts.cli.Pipeline.run", fake_run)

    result = CliRunner().invoke(app, ["create", str(source), "--output", str(tmp_path / "out"), "--config", str(config_file)])

    assert result.exit_code == 1
    assert captured["count"] == 3


def test_cli_prints_user_error_without_traceback(monkeypatch, tmp_path) -> None:
    def raise_user_error(*args, **kwargs):
        raise UserFacingError("Файл не найден.")

    monkeypatch.setattr("movie_shorts.cli.Pipeline.run", raise_user_error)

    result = CliRunner().invoke(app, ["create", "missing.mp4", "--output", str(tmp_path)])

    assert result.exit_code == 1
    assert result.output == "Файл не найден.\n"

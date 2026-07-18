from typer.testing import CliRunner

from movie_shorts.cli import app


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

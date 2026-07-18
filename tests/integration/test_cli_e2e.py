from typer.testing import CliRunner

from movie_shorts.cli import app
from movie_shorts.pipeline import RunReport


def test_cli_reports_completed_mocked_run(monkeypatch, tmp_path) -> None:
    source = tmp_path / "film.mp4"
    source.touch()
    output = tmp_path / "run"

    def fake_run(self, config):
        for name in ("scenes.json", "transcript.json", "candidates.json"):
            (config.output_dir).mkdir(parents=True, exist_ok=True)
            (config.output_dir / name).write_text("[]", encoding="utf-8")
        (config.output_dir / "subtitles").mkdir(exist_ok=True)
        (config.output_dir / "subtitles" / "short-01.ass").write_text("[Events]", encoding="utf-8")
        (config.output_dir / "shorts").mkdir(exist_ok=True)
        video = config.output_dir / "shorts" / "short-01.mp4"
        video.write_bytes(b"mock")
        return RunReport((video,), ())

    monkeypatch.setattr("movie_shorts.cli.Pipeline.run", fake_run)

    result = CliRunner().invoke(app, ["create", str(source), "--output", str(output)])

    assert result.exit_code == 0
    assert "Готово: создано роликов — 1." in result.output
    assert (output / "candidates.json").exists()
    assert (output / "subtitles" / "short-01.ass").exists()
    assert (output / "shorts" / "short-01.mp4").exists()
